"""Project state: seed data, element states, activity roll-up, earned value and forecast.

The Python state is authoritative; the graph is a projection of it (see tagwerk/graph/sync.py).
State is rebuilt at startup from seed/ + seed/history.json + every stored capture result, all
through `apply_structured`, so history and live captures follow exactly the same rules.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from tagwerk.pipeline.loop import STATES, apply_work, weight

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
HOURS_PER_DAY = 8
ABSENCE_WORKDAYS = 3  # a sick report counts for 3 working days (no doctor's note needed in Germany up to day 3)


# ---------- working days ----------

def is_workday(d: date) -> bool:
    return d.weekday() < 5


def next_workday(d: date) -> date:
    d += timedelta(days=1)
    while not is_workday(d):
        d += timedelta(days=1)
    return d


def workdays(start: date, end: date) -> list[date]:
    """Working days in [start, end]."""
    out, d = [], start
    while d <= end:
        if is_workday(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def workday_diff(a: date, b: date) -> int:
    """Signed number of working days from a to b (b later -> positive)."""
    if a == b:
        return 0
    if b > a:
        return len(workdays(a + timedelta(days=1), b))
    return -len(workdays(b + timedelta(days=1), a))


# ---------- helpers ----------

def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _num(v: str | None, default: float = 0.0) -> float:
    return float(v) if v not in (None, "") else default


def _norm_text(s: str | None) -> str:
    """Event text for duplicate checks: lowercase, single spaces, no trailing . ! ?"""
    return " ".join((s or "").lower().split()).rstrip(".!? ")


# Spoken trade -> project trade, for projects whose trades are groups (scan projects: Rohbau, Fenster/Türen, TGA,
# Ausbau, Ausstattung). An exact trade name always wins; this map is only the second choice.
TRADE_GROUPS = {
    "tga": {"elektro", "elektriker", "heizung", "heizungsbauer", "sanitär", "klempner", "lüftung", "installateur"},
    "ausbau": {"trockenbau", "maler", "bodenleger", "fliesenleger", "putz", "verputzer"},
    "rohbau": {"maurer", "beton", "zimmerer", "zimmermann"},
    "fenster/türen": {"fensterbauer", "tischler", "schreiner"},
}


def states_for(element_type: str) -> list[tuple[str, int]]:
    return STATES.get(element_type, STATES["default"])


def ifc_guid(seed: str) -> str:
    """Deterministic 22-char IFC GlobalId from a string (uuid5 compressed with the IFC alphabet)."""
    import uuid

    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
    n = uuid.uuid5(uuid.NAMESPACE_URL, f"tagwerk:{seed}").int
    out = []
    for _ in range(22):
        out.append(chars[n % 64])
        n //= 64
    return "".join(reversed(out))


@dataclass
class Project:
    zones: dict[str, dict] = field(default_factory=dict)
    elements: dict[str, dict] = field(default_factory=dict)
    activities: dict[str, dict] = field(default_factory=dict)
    wbs: dict[str, dict] = field(default_factory=dict)
    boq: dict[str, dict] = field(default_factory=dict)
    links: list[dict] = field(default_factory=list)
    trades: dict[str, dict] = field(default_factory=dict)
    captures: dict[str, dict] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    labour: list[dict] = field(default_factory=list)
    materials: list[dict] = field(default_factory=list)
    proposals: list[dict] = field(default_factory=list)
    history_log: list[dict] = field(default_factory=list)  # every state change, for curves
    meta: dict = field(default_factory=dict)  # seed/<project>/project.json: id, name, data_date, lat, lon
    _by_act: dict[str, list[dict]] = field(default_factory=dict, repr=False)
    _by_el: dict[str, list[dict]] = field(default_factory=dict, repr=False)
    _budget: dict[str, float] = field(default_factory=dict, repr=False)

    # ----- loading -----

    @classmethod
    def from_seed(cls, seed_dir: Path = SEED_DIR) -> Project:
        p = cls()
        for r in _read_csv(seed_dir / "zones.csv"):
            p.zones[r["zone_id"]] = {"id": r["zone_id"], "name_de": r["name_de"], "name_en": r["name_en"],
                                     "kind": r["kind"], "storey": r.get("storey") or None,
                                     "aliases": [x for x in (r.get("aliases") or "").split("|") if x]}
        for r in _read_csv(seed_dir / "elements.csv"):
            eid = r["element_id"]
            p.elements[eid] = {
                "id": eid, "global_id": r["global_id"] or ifc_guid(eid), "ifc_class": r["ifc_class"],
                "name_de": r["name_de"], "name_en": r["name_en"], "zone": r["zone"], "type": r["type"] or "default",
                "qty": _num(r["qty"], 1), "unit": r["unit"], "din276": r["din276"],
                "marker_id": int(r["marker_id"]) if r["marker_id"] else None,
                "aliases": [a.strip() for a in r["aliases"].split("|") if a.strip()],
                "geom": [_num(r[k]) for k in ("x", "y", "z", "dx", "dy", "dz")],
                "pct": 0, "state": None, "updated": None,
            }
        if (seed_dir / "wbs.csv").exists():
            for r in _read_csv(seed_dir / "wbs.csv"):
                p.wbs[r["wbs"]] = {"code": r["wbs"], "name": r["name"]}
        for r in _read_csv(seed_dir / "trades.csv"):
            p.trades[r["trade_id"]] = {"id": r["trade_id"], "name": r["name"], "rate_eur_h": _num(r["rate_eur_h"])}
        for r in _read_csv(seed_dir / "activities.csv"):
            p.activities[r["activity_id"]] = {
                "id": r["activity_id"], "wbs": r["wbs"], "name": r["name"], "trade_id": r["trade_id"],
                "planned_start": date.fromisoformat(r["planned_start"]),
                "planned_finish": date.fromisoformat(r["planned_finish"]),
                "crew_planned": _num(r.get("crew_planned"), 1),
                "predecessors": [x.split(":")[0] for x in (r.get("predecessors") or "").split(";") if x],
                "start_to_start": [x.split(":")[0] for x in (r.get("predecessors") or "").split(";")
                                   if x.endswith(":SS")],
                "msp_uid": r.get("msp_uid") or None,
                "manual_pct": None, "actual_start": None, "actual_finish": None,
            }
        for r in _read_csv(seed_dir / "boq.csv"):
            p.boq[r["oz"]] = {"oz": r["oz"], "lot": r["lot"], "short_text": r["short_text"], "qty": _num(r["qty"]),
                              "unit": r["unit"], "unit_price": _num(r["unit_price"]), "din276": r["din276"]}
        for r in _read_csv(seed_dir / "mapping.csv"):
            p.links.append({"oz": r["oz"], "activity_id": r["activity_id"], "element_id": r["element_id"] or None,
                            "share": _num(r["share"], 1), "from_state": r["from_state"] or None,
                            "to_state": r["to_state"] or None})
        meta_file = seed_dir / "project.json"
        p.meta = {"id": "P-HS", "name": "Hörsaal Sanierung", "client": "TUM (fictitious renovation)",
                  "lat": 48.137, "lon": 11.575, "seed_dir": str(seed_dir)}
        if meta_file.exists():
            p.meta.update(json.loads(meta_file.read_text(encoding="utf-8")))
        p._check()
        p._index()
        return p

    def _index(self) -> None:
        self._by_act, self._by_el, self._budget = defaultdict(list), defaultdict(list), defaultdict(float)
        for lk in self.links:
            lk["value"] = self.link_value(lk)
            self._by_act[lk["activity_id"]].append(lk)
            self._budget[lk["activity_id"]] += lk["value"]
            if lk["element_id"]:
                self._by_el[lk["element_id"]].append(lk)

    def _check(self) -> None:
        for link in self.links:
            assert link["oz"] in self.boq, f"mapping: unknown OZ {link['oz']}"
            assert link["activity_id"] in self.activities, f"mapping: unknown activity {link['activity_id']}"
            if link["element_id"]:
                el = self.elements.get(link["element_id"])
                assert el, f"mapping: unknown element {link['element_id']}"
                names = [s for s, _ in states_for(el["type"])]
                for k in ("from_state", "to_state"):
                    assert link[k] is None or link[k] in names, f"mapping: {link[k]} not a state of {el['id']}"
        for a in self.activities.values():
            for pred in a["predecessors"]:
                assert pred in self.activities, f"activity {a['id']}: unknown predecessor {pred}"

    def load_history(self, path: Path | None = None, upto: str | None = None) -> None:
        """Apply seed/history.json; with upto (ISO date) only the initial snapshot and days up to that date."""
        path = path or Path(self.meta.get("seed_dir", SEED_DIR)) / "history.json"
        if not path.exists():
            return
        hist = json.loads(path.read_text(encoding="utf-8"))
        init = hist.get("initial", {})
        d0 = init.get("date")
        if upto is not None and d0 and d0 > upto:
            return
        for eid, state in init.get("states", {}).items():
            el = self.elements[eid]
            el["pct"], el["state"], el["updated"] = weight(el["type"], state), state, d0
            self.history_log.append({"date": d0, "element_id": eid, "state": state, "pct": el["pct"],
                                     "capture_id": None, "initial": True})
        for aid, pct in init.get("manual_pct", {}).items():
            self.activities[aid]["manual_pct"] = float(pct)
        for day in hist.get("days", []):
            for c in day["captures"]:
                if upto is not None and c["ts"][:10] > upto:
                    continue
                meta = {k: c[k] for k in ("capture_id", "zone_id", "ts", "note") if k in c}
                self.apply_structured(meta, {"capture_id": c["capture_id"], **c["structured"]})

    # ----- applying evidence -----

    def apply_structured(self, meta: dict, structured: dict) -> list[dict]:
        """Apply one capture's structured result. Returns the list of element changes.

        meta: {capture_id, zone_id, ts (ISO), note?}. Idempotent per capture_id.
        """
        cid = meta["capture_id"]
        if cid in self.captures:
            return self.captures[cid]["changes"]
        day = date.fromisoformat(meta["ts"][:10]).isoformat()  # ValueError before anything changes
        with self.transaction():
            return self._apply(cid, day, meta, structured)

    @contextmanager
    def transaction(self):
        """Undo every change apply_structured can make if the block raises: all or nothing."""
        lists = {k: len(getattr(self, k)) for k in ("events", "labour", "materials", "proposals", "history_log")}
        elements = {eid: (el["pct"], el["state"], el["updated"]) for eid, el in self.elements.items()}
        starts = {aid: a["actual_start"] for aid, a in self.activities.items()}
        events = [dict(e) for e in self.events]  # same-day absences update count/text in place
        captures = set(self.captures)
        try:
            yield
        except BaseException:
            for k, n in lists.items():
                del getattr(self, k)[n:]
            self.events[:] = events
            for eid, (pct, state, updated) in elements.items():
                el = self.elements[eid]
                el["pct"], el["state"], el["updated"] = pct, state, updated
            for aid, start in starts.items():
                self.activities[aid]["actual_start"] = start
            for cid in set(self.captures) - captures:
                del self.captures[cid]
            raise

    def _apply(self, cid: str, day: str, meta: dict, structured: dict) -> list[dict]:
        changes: list[dict] = []
        for w in structured.get("work_done", []):
            for eid in w["element_ids"]:
                el = self.elements.get(eid)
                if not el:
                    continue
                try:
                    res = apply_work(el, w["state_proposed"], w["evidence"])
                except KeyError:
                    changes.append({"element_id": eid, "action": "invalid", "state": w["state_proposed"],
                                    "quote": w["quote"]})
                    continue
                change = {"element_id": eid, "action": res["action"], "state": w["state_proposed"],
                          "from_pct": el["pct"], "pct": res.get("proposed_pct", res["pct"]), "quote": w["quote"],
                          "evidence": w["evidence"], "activity_id": w.get("activity_id"), "t": w.get("t")}
                if res["action"] == "confirmed":
                    self._set_state(el, w["state_proposed"], res["pct"], day, cid)
                elif res["action"] == "proposed":
                    self.proposals.append({"capture_id": cid, "element_id": eid, "state": w["state_proposed"],
                                           "pct": res["proposed_pct"], "date": day})
                changes.append(change)
        for lp in structured.get("labour_present", []):
            self.labour.append({"date": day, "trade": lp["trade"], "count": lp["count"], "capture_id": cid})
        for i, ab in enumerate(structured.get("absences", [])):
            # the same sickness reported again on the same day (another capture, a replay) keeps the max, never adds
            same = next((e for e in self.events if e["type"] == "absence" and e["date"] == day
                         and e["trade"].lower() == ab["trade"].lower()), None)
            if same:
                if ab["count"] > same["count"]:
                    same["count"], same["text"] = ab["count"], f"{ab['count']}× {ab['trade']} {ab['reason']}"
                continue
            act = self.activity_for_trade(ab["trade"], date.fromisoformat(day))
            self.events.append({"id": f"{cid}:absence:{i}", "type": "absence", "trade": ab["trade"],
                                "count": ab["count"], "text": f"{ab['count']}× {ab['trade']} {ab['reason']}",
                                "severity": "medium", "date": day, "capture_id": cid,
                                "activity_id": act["id"] if act else None})
        for i, ev in enumerate(structured.get("special_events", [])):
            if any(e["type"] == ev["type"] and e["date"] == day and _norm_text(e["text"]) == _norm_text(ev["text"])
                   for e in self.events):
                continue
            self.events.append({"id": f"{cid}:event:{i}", "type": ev["type"], "text": ev["text"],
                                "severity": ev["severity"], "date": day, "capture_id": cid, "activity_id": None})
        for m in structured.get("material_delivered", []):
            self.materials.append({**m, "date": day, "capture_id": cid})
        self.captures[cid] = {**meta, "date": day, "changes": changes,
                              "quotes": [w["quote"] for w in structured.get("work_done", [])],
                              "structured": structured}
        return changes

    def manual_confirm(self, element_id: str, state: str, day: str, capture_id: str = "manual") -> dict:
        """A tap in the site manager view: confirms like voice evidence."""
        el = self.elements[element_id]
        res = apply_work(el, state, "voice")
        if res["action"] == "confirmed":
            self._set_state(el, state, res["pct"], day, capture_id)
        return res

    def _set_state(self, el: dict, state: str, pct: int, day: str, cid: str) -> None:
        el["pct"], el["state"], el["updated"] = pct, state, day
        self.history_log.append({"date": day, "element_id": el["id"], "state": state, "pct": pct, "capture_id": cid})
        for link in self._by_el.get(el["id"], []):
            a = self.activities[link["activity_id"]]
            if (a["actual_start"] is None or day < a["actual_start"]) and self._element_contrib(el, link, pct) > 0:
                a["actual_start"] = day

    # ----- lookups -----

    def trade_by_name(self, name: str) -> dict | None:
        n = name.lower()
        for t in self.trades.values():
            if t["name"].lower() == n or t["id"].lower() == n:
                return t
        for t in self.trades.values():  # group fallback: "Elektro" -> TGA
            if n in TRADE_GROUPS.get(t["name"].lower(), ()):
                return t
        return None

    def activity_for_trade(self, trade_name: str, d: date) -> dict | None:
        t = self.trade_by_name(trade_name)
        if not t:
            return None
        cands = [a for a in self.activities.values() if a["trade_id"] == t["id"]]
        if not cands:
            return None
        # prefer the one whose planned window covers d, else the unfinished one closest to d
        cover = [a for a in cands if a["planned_start"] <= d <= a["planned_finish"]]
        pool = cover or [a for a in cands if self.activity_pct(a["id"]) < 100] or cands
        return min(pool, key=lambda a: abs((a["planned_finish"] - d).days))

    def marker_map(self) -> dict[int, str]:
        return {el["marker_id"]: eid for eid, el in self.elements.items() if el["marker_id"] is not None}

    def elements_of(self, activity_id: str) -> list[str]:
        return sorted({lk["element_id"] for lk in self._by_act.get(activity_id, []) if lk["element_id"]})

    def activities_of(self, element_id: str) -> list[str]:
        return sorted({lk["activity_id"] for lk in self._by_el.get(element_id, [])})

    # ----- numbers -----

    def link_value(self, link: dict) -> float:
        b = self.boq[link["oz"]]
        return b["qty"] * b["unit_price"] * link["share"]

    def budget(self, activity_id: str) -> float:
        return round(self._budget.get(activity_id, 0.0), 2)

    def _element_contrib(self, el: dict, link: dict, pct: float | None = None) -> float:
        pct = el["pct"] if pct is None else pct
        lo = weight(el["type"], link["from_state"]) if link["from_state"] else 0
        hi = weight(el["type"], link["to_state"]) if link["to_state"] else 100
        return max(0.0, min(100.0, (pct - lo) * 100.0 / (hi - lo)))

    def activity_pct(self, activity_id: str) -> float:
        """BoQ-weighted average of element progress (weight = qty x unit price x share of the linked position)."""
        a = self.activities[activity_id]
        links = [lk for lk in self._by_act.get(activity_id, []) if lk["element_id"]]
        if not links:
            return float(a["manual_pct"] or 0.0)
        total = sum(lk["value"] for lk in links)
        if not total:  # unpriced schedule (e.g. imported BIM project): count elements equally
            return round(sum(self._element_contrib(self.elements[lk["element_id"]], lk) for lk in links) / len(links), 1)
        return round(sum(self._element_contrib(self.elements[lk["element_id"]], lk) * lk["value"]
                         for lk in links) / total, 1)

    def planned_pct(self, activity_id: str, d: date, start_of_day: bool = False) -> float:
        """Linear plan over working days, measured at the end of day d (or at its start: the morning report)."""
        a = self.activities[activity_id]
        days = workdays(a["planned_start"], a["planned_finish"]) or [a["planned_start"]]
        done = len([x for x in days if (x < d if start_of_day else x <= d)])
        return round(100.0 * done / len(days), 1)

    def absent_on(self, trade_id: str, d: date) -> float:
        """Absent crew for that trade covering day d. A report covers its own day (or the next working day when
        reported on a weekend) plus the following working days up to ABSENCE_WORKDAYS. Repeats of one spoken trade do
        not add up (highest count wins); different spoken trades mapped to one project trade (Elektro + Sanitär on TGA)
        are different people and are summed."""
        best: dict[str, float] = {}
        for e in self.events:
            if e["type"] != "absence":
                continue
            t = self.trade_by_name(e["trade"])
            if not t or t["id"] != trade_id:
                continue
            first = date.fromisoformat(e["date"])
            if not is_workday(first):
                first = next_workday(first)
            last = first
            for _ in range(ABSENCE_WORKDAYS - 1):
                last = next_workday(last)
            if first <= d <= last:
                key = e["trade"].lower()
                best[key] = max(best.get(key, 0.0), e["count"])
        return float(sum(best.values()))

    def topo_order(self) -> list[str]:
        order, seen = [], set()

        def visit(aid: str) -> None:
            if aid in seen:
                return
            seen.add(aid)
            for pred in self.activities[aid]["predecessors"]:
                visit(pred)
            order.append(aid)

        for aid in sorted(self.activities):
            visit(aid)
        return order

    def is_tracked(self, activity_id: str) -> bool:
        """Progress is measurable: it has linked elements or a manual percentage."""
        return self.activities[activity_id]["manual_pct"] is not None or any(
            lk["element_id"] for lk in self._by_act.get(activity_id, []))

    def _finish_dates(self) -> dict[str, str | None]:
        """Per activity: first day on which every linked element reached the activity's target state."""
        hist: dict[str, list[tuple[str | None, int]]] = defaultdict(list)
        for h in self.history_log:
            if h["date"]:  # initial snapshot states have no known date: assume reached on plan (None)
                hist[h["element_id"]].append((None if h.get("initial") else h["date"], h["pct"]))
        out: dict[str, str | None] = {}
        for aid, links in self._by_act.items():
            days = []
            for lk in links:
                if not lk["element_id"]:
                    continue
                el = self.elements[lk["element_id"]]
                hi = weight(el["type"], lk["to_state"]) if lk["to_state"] else 100
                hits = [d for d, pct in hist.get(el["id"], []) if pct >= hi]
                if not hits:
                    days.append(None)
                    continue
                dated = sorted(d for d in hits if d)
                days.append(dated[0] if len(dated) == len(hits) else
                            self.activities[aid]["planned_finish"].isoformat())
            out[aid] = max(days) if days and all(days) else None
        return out

    def forecast(self, today: date) -> dict[str, dict]:
        """Projection from today's evidence.

        Rate = 100 % / (planned working days x planned crew) per crew-day. Remaining work is simulated day by
        day from today with crew = planned crew minus absences reported for that day (absences count for the
        day they are reported). Successors cannot start before their predecessors' forecast finish
        (finish-to-start), so a delay passes on through the network.
        """
        out: dict[str, dict] = {}
        finished = self._finish_dates()
        for aid in self.topo_order():
            a = self.activities[aid]
            pct = self.activity_pct(aid)
            planned_days = len(workdays(a["planned_start"], a["planned_finish"])) or 1
            rate = 100.0 / (planned_days * a["crew_planned"])  # % per crew-day
            earliest = a["planned_start"]
            for pred in a["predecessors"]:
                if pred in a["start_to_start"]:  # SS: may start once the predecessor has started
                    earliest = max(earliest, out[pred]["forecast_start"])
                elif out[pred]["forecast_finish"] >= earliest:  # FS
                    earliest = next_workday(out[pred]["forecast_finish"])
            tracked = self.is_tracked(aid)
            if not tracked:  # no evidence possible: assume planned duration from its earliest start
                start = earliest if is_workday(earliest) else next_workday(earliest)
                finish = start
                for _ in range(planned_days - 1):
                    finish = next_workday(finish)
                pct = 100.0 if finish < today else 0.0
            elif pct >= 100:
                finish = date.fromisoformat(finished[aid]) if finished.get(aid) else a["planned_finish"]
                start = date.fromisoformat(a["actual_start"]) if a["actual_start"] else a["planned_start"]
            else:
                d = max(earliest, today) if pct == 0 else today
                if not is_workday(d):
                    d = next_workday(d)
                start = date.fromisoformat(a["actual_start"]) if (pct > 0 and a["actual_start"]) else d
                remaining, finish, guard = 100.0 - pct, d, 0
                while remaining > 1e-6 and guard < 400:
                    crew = max(0.0, a["crew_planned"] - self.absent_on(a["trade_id"], d))
                    remaining -= rate * crew
                    finish = d
                    d = next_workday(d)
                    guard += 1
            bac = self.budget(aid)
            ppct = self.planned_pct(aid, today, start_of_day=True)
            out[aid] = {
                "id": aid, "name": a["name"], "wbs": a["wbs"], "trade": self.trades[a["trade_id"]]["name"],
                "pct": pct, "planned_pct": ppct,
                "planned_start": a["planned_start"], "baseline_finish": a["planned_finish"],
                "forecast_start": start, "forecast_finish": finish, "tracked": tracked,
                "delay_d": workday_diff(a["planned_finish"], finish),
                "bac_eur": bac, "pv_eur": round(bac * ppct / 100, 2),
                "ev_eur": round(bac * pct / 100, 2) if tracked else 0.0,  # assumed progress earns nothing
                "crew_planned": a["crew_planned"],
                "crew_today": max(0.0, a["crew_planned"] - self.absent_on(a["trade_id"], today)),
                "elements": self.elements_of(aid), "predecessors": a["predecessors"],
            }
        return out

    def actual_cost(self, upto: date) -> float:
        """Labour hours x invented trade rates (labelled as such in the UI)."""
        total = 0.0
        for lp in self.labour:
            if lp["date"] <= upto.isoformat():
                t = self.trade_by_name(lp["trade"])
                if t:
                    total += lp["count"] * HOURS_PER_DAY * t["rate_eur_h"]
        return round(total, 2)

    # ----- outputs -----

    def dashboard(self, today: date) -> dict:
        """Data for contracts/dashboard.schema.json."""
        fc = self.forecast(today)
        acts = sorted(fc.values(), key=lambda r: (-r["delay_d"], r["pct"]))
        return {
            "date": today.isoformat(),
            "activities": [{"id": r["id"], "name": r["name"], "pct": r["pct"],
                            "baseline_finish": r["baseline_finish"].isoformat(),
                            "forecast_finish": r["forecast_finish"].isoformat(),
                            "delay_d": r["delay_d"], "ev_eur": r["ev_eur"]} for r in acts],
            "events": [{"type": e["type"], "text": e["text"], "severity": e["severity"]}
                       for e in sorted(self.events, key=lambda e: e["date"], reverse=True)],
        }

    def overview(self, today: date) -> dict:
        """Everything the Bauleiter dashboard and the site-manager view need (not a contract)."""
        fc = self.forecast(today)
        acts = list(fc.values())
        pv = sum(r["pv_eur"] for r in acts)
        ev = sum(r["ev_eur"] for r in acts)
        bac = sum(r["bac_eur"] for r in acts)
        # a project without activities (hand-made seed) still renders: no finish dates, no delay
        project_finish = max((r["forecast_finish"] for r in acts), default=None)
        baseline_finish = max((r["baseline_finish"] for r in acts), default=today)
        iso = today.isoformat()

        curve = self.curve(today, max(today, baseline_finish))
        if not bac:  # unpriced schedule: % from the element-count-weighted curve
            now = next((c for c in reversed(curve) if c["ev_pct"] is not None), None)
            if now:
                ev, pv, bac = now["ev_pct"], now["pv_pct"], 100.0

        labour_today: dict[str, int] = defaultdict(int)
        for lp in self.labour:
            if lp["date"] == iso:
                labour_today[lp["trade"]] += lp["count"]
        planned_crew: dict[str, float] = defaultdict(float)
        for a in self.activities.values():
            if a["planned_start"] <= today <= a["planned_finish"]:
                planned_crew[self.trades[a["trade_id"]]["name"]] += a["crew_planned"]
        zone_grid = []
        for zid, z in self.zones.items():
            els = [e for e in self.elements.values() if e["zone"] == zid]
            zone_grid.append({"zone_id": zid, "name": z["name_de"],
                              "elements": [{"id": e["id"], "name": e["name_de"], "pct": e["pct"],
                                            "state": e["state"], "type": e["type"],
                                            "states": [s for s, _ in states_for(e["type"])]} for e in els]})
        today_caps = [c for c in list(self.captures.values()) if c["date"] == iso]
        return {
            "date": iso,
            "kpi": {
                "pct_actual": round(100 * ev / bac, 1) if bac else 0, "pct_planned": round(100 * pv / bac, 1) if bac else 0,
                "spi": round(ev / pv, 2) if pv else None, "ev_eur": round(ev), "pv_eur": round(pv), "bac_eur": round(bac),
                "priced": any(lk["value"] for lk in self.links),
                "planned_basis": "start of report day (curve points: end of each day)",
                "ac_eur": round(self.actual_cost(today)), "ac_note": "labour hours x invented trade rates",
                "forecast_finish": project_finish.isoformat() if project_finish else None,
                "baseline_finish": baseline_finish.isoformat(),
                "delay_d": workday_diff(baseline_finish, project_finish) if project_finish else 0,
                "open_defects": len([e for e in self.events if e["type"] == "defect"]),
            },
            "activities": [{**r, "planned_start": r["planned_start"].isoformat(),
                            "forecast_start": r["forecast_start"].isoformat(),
                            "baseline_finish": r["baseline_finish"].isoformat(),
                            "forecast_finish": r["forecast_finish"].isoformat(),
                            "red": r["delay_d"] > 0 and r["pct"] < 100 and r["tracked"],
                            "done": r["pct"] >= 100,
                            "cause": self._cause(r, today, fc)}
                           for r in sorted(acts, key=lambda r: (not r["tracked"], -r["delay_d"], r["pct"]))],
            "captures": sorted([{"capture_id": c["capture_id"], "zone_id": c["zone_id"], "ts": c["ts"],
                                 "note": c.get("note"), "quotes": c["quotes"],
                                 "photos": c.get("photos", []),
                                 "changes": [ch for ch in c["changes"] if ch["action"] in ("confirmed", "proposed")]}
                                for c in list(self.captures.values())], key=lambda c: c["ts"], reverse=True),
            "today_capture_ids": [c["capture_id"] for c in today_caps],
            "events": sorted(self.events, key=lambda e: e["date"], reverse=True),
            "labour": {"present": dict(labour_today), "planned": dict(planned_crew)},
            "proposals": [p for p in self.proposals if self.elements[p["element_id"]]["pct"] < p["pct"]],
            "curve": curve,
            "zones": zone_grid,
            "weather": next((c.get("weather") for c in sorted(today_caps, key=lambda c: c["ts"], reverse=True)
                             if c.get("weather")), None),
        }

    def curve(self, today: date, until: date) -> list[dict]:
        """Planned vs earned per working day, in EUR (BoQ-weighted) and in % of the project.

        Earned is replayed incrementally from history_log, so this stays linear in the size of the log.
        Unpriced projects (imported BIM schedules) weight every element link equally instead.
        """
        priced = sum(lk["value"] for lk in self.links) > 0
        w = {id(lk): (lk["value"] if priced else 1.0) for lk in self.links}
        total = sum(w.values()) or 1.0
        act_w = {a: sum(w[id(lk)] for lk in self._by_act.get(a, [])) for a in self.activities}
        manual = sum(act_w[a] * (self.activities[a]["manual_pct"] or 0) / 100 for a in self.activities
                     if not any(lk["element_id"] for lk in self._by_act.get(a, [])))
        el_types = {e: el["type"] for e, el in self.elements.items()}
        cur: dict[str, float] = {}

        def contrib(eid: str, pct: float) -> float:
            return sum(w[id(lk)] * self._element_contrib({"type": el_types[eid]}, lk, pct) / 100
                       for lk in self._by_el.get(eid, []))

        log = sorted((h for h in self.history_log if h["date"]), key=lambda h: h["date"])
        start = min((a["planned_start"] for a in self.activities.values()), default=today)
        first_log = log[0]["date"] if log else None
        if first_log and date.fromisoformat(first_log) < start:
            start = date.fromisoformat(first_log)
        ev, i, out = manual, 0, []
        for d in workdays(start, until):
            iso = d.isoformat()
            while i < len(log) and log[i]["date"] <= iso:
                h = log[i]
                old = cur.get(h["element_id"], 0)
                if h["pct"] > old:
                    ev += contrib(h["element_id"], h["pct"]) - contrib(h["element_id"], old)
                    cur[h["element_id"]] = h["pct"]
                i += 1
            pv = sum(act_w[a] * self.planned_pct(a, d) / 100 for a in self.activities)
            row = {"date": iso, "pv": round(pv), "pv_pct": round(100 * pv / total, 1),
                   "ev": round(ev) if d <= today else None,
                   "ev_pct": round(100 * ev / total, 1) if d <= today else None,
                   "ac": round(self.actual_cost(d)) if d <= today else None}
            if not priced:
                row["pv"], row["ev"] = row["pv_pct"], row["ev_pct"]
            out.append(row)
        return out

    def _cause(self, row: dict, today: date, fc: dict[str, dict]) -> str | None:
        if row["delay_d"] <= 0:
            return None
        if row["pct"] >= 100:
            return f"finished {row['delay_d']} working days after baseline"
        reasons = []
        a = self.activities[row["id"]]
        absent = self.absent_on(a["trade_id"], today)
        if absent:
            reasons.append(f"{absent:g} of {a['crew_planned']:g} {row['trade']} absent today")
        late_preds = [p for p in a["predecessors"] if fc[p]["delay_d"] > 0 and fc[p]["pct"] < 100]
        if late_preds:
            reasons.append("waiting for " + ", ".join(self.activities[p]["name"] for p in late_preds[:3]))
        if row["pct"] < row["planned_pct"]:
            reasons.append(f"{row['pct']:.0f} % done vs {row['planned_pct']:.0f} % planned")
        return "; ".join(reasons) or "behind plan"
