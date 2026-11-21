"""UI v2 payloads (docs/UI-V2-CONTRACT.md): the day list, the day snapshot "as of day D" and the task graph.

"As of day D" = seed + history + stored capture results with date <= D, applied in date order, rebuilt from the seed
(the live project in tagwerk.state is not touched). Forecasts use today = min(D, project today); days after the
project's today show the plan only. No cost fields anywhere.
"""
from __future__ import annotations

import json
import logging
import threading
from collections import OrderedDict
from datetime import date, timedelta
from pathlib import Path

from tagwerk.config import get_settings
from tagwerk.labels import STATE_DE
from tagwerk.project import Project, is_workday, next_workday
from tagwerk.state import get_project, results_dir, seed_dir, today

log = logging.getLogger(__name__)
VIDEO_EXT = (".mp4", ".mov", ".webm", ".m4v")
PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")
AUDIO_EXT = (".m4a", ".mp3", ".wav", ".ogg", ".aac", ".opus")
KIND_DE = {"video": "Video", "photo": "Foto", "audio": "Sprachnotiz", "note": "Notiz", "manual": "Manuell",
           "plan": "Terminplan"}
# weather constraints (contract): precip >= 5 mm, wind >= 50 km/h, temp <= 0 °C
RAIN_MM, WIND_KMH, FROST_C = 5.0, 50.0, 0.0

_cache: OrderedDict[tuple, Project] = OrderedDict()
_cache_lock = threading.Lock()
CACHE_SIZE = 64


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


# ---------- state as of day D ----------

def _stored_results() -> list[dict]:
    out = []
    for f in results_dir().glob("*.json"):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            log.warning("skipping unreadable result %s: %s", f.name, exc)
    return out


def project_as_of(d: date) -> Project:
    """Seed + history + stored captures with date <= d, cached per (project, d, number of stored captures)."""
    files = list(results_dir().glob("*.json"))
    key = (str(seed_dir()), str(results_dir()), d.isoformat(), len(files))
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    iso = d.isoformat()
    p = Project.from_seed(seed_dir())
    p.load_history(upto=iso)
    results = [r for r in _stored_results() if r["meta"]["ts"][:10] <= iso]
    for r in sorted(results, key=lambda r: r["meta"]["ts"]):
        p.apply_structured(r["meta"], r["structured"])
        p.captures[r["meta"]["capture_id"]].update({k: r["meta"][k] for k in ("photos", "weather", "lang")
                                                     if k in r["meta"]})
    with _cache_lock:
        _cache[key] = p
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return p


# ---------- small helpers ----------

def _has_reading(w: dict | None) -> bool:
    return bool(w) and any(w.get(k) is not None for k in ("tempC", "precipMm", "windKmh"))


def _weather_of(p: Project, iso: str) -> dict | None:
    caps = sorted((c for c in p.captures.values() if c["date"] == iso and _has_reading(c.get("weather"))),
                  key=lambda c: c["ts"], reverse=True)
    if not caps:
        return None
    w = caps[0]["weather"]
    return {k: w.get(k) for k in ("tempC", "precipMm", "windKmh", "source")}


def _weather_event(iso: str, w: dict | None) -> dict | None:
    if not _has_reading(w):
        return None
    parts = []
    if (w.get("precipMm") or 0) >= RAIN_MM:
        parts.append(f"Starkregen {w['precipMm']:g} mm: Außenarbeiten ruhen")
    if (w.get("windKmh") or 0) >= WIND_KMH:
        parts.append(f"Sturm {w['windKmh']:g} km/h: kein Kranbetrieb")
    if w.get("tempC") is not None and w["tempC"] <= FROST_C:
        parts.append(f"Frost {w['tempC']:g} °C: kein Beton/Estrich")
    if not parts:
        return None
    return {"id": f"weather:{iso}", "date": iso, "type": "weather", "text": "; ".join(parts),
            "severity": "high" if len(parts) > 1 else "medium", "activity_id": None, "capture_id": None,
            "source": "weather"}


def _weather_events(p: Project, upto: str | None = None) -> list[dict]:
    days = sorted({c["date"] for c in p.captures.values() if upto is None or c["date"] <= upto})
    return [e for e in (_weather_event(iso, _weather_of(p, iso)) for iso in days) if e]


def _event(e: dict) -> dict:
    return {"id": e["id"], "date": e["date"], "type": e["type"], "text": e["text"], "severity": e["severity"],
            "activity_id": e.get("activity_id"), "capture_id": e.get("capture_id"),
            "source": "capture" if e.get("capture_id") else "seed"}


def _media(cid: str) -> tuple[str | None, list[str], bool]:
    """(video URL, photo URLs, has audio) from data/captures/<cid>/ and cache/<cid>/media/ (served by /media)."""
    s = get_settings()
    names: list[str] = []
    for root in (Path(s.data_dir) / "captures" / cid, Path(s.cache_dir) / cid / "media"):
        if root.is_dir():
            names += sorted(f.name for f in root.iterdir() if f.is_file())
    seen, files = set(), []
    for n in names:  # uploads are prefixed with an index, the kept copy is not: keep the first of each
        bare = n[3:] if len(n) > 3 and n[:2].isdigit() and n[2] == "_" else n
        if bare not in seen:
            seen.add(bare)
            files.append(n)
    low = [(f, f.lower()) for f in files]
    video = next((f for f, lf in low if lf.endswith(VIDEO_EXT)), None)
    photos = [f"/media/{cid}/{f}" for f, lf in low if lf.endswith(PHOTO_EXT)]
    return (f"/media/{cid}/{video}" if video else None), photos, any(lf.endswith(AUDIO_EXT) for _, lf in low)


def _has_3d(cid: str) -> bool:
    """A finished reconstruction: cache/<cid>/sfm.json with "ok": true (a failed one keeps its 2D objects only)."""
    try:
        return json.loads((Path(get_settings().cache_dir) / cid / "sfm.json").read_text(encoding="utf-8")).get("ok") is True
    except (OSError, ValueError, AttributeError):
        return False


def _transcript(cid: str) -> str | None:
    f = Path(get_settings().cache_dir) / cid / "speech.json"
    try:
        segs = json.loads(f.read_text(encoding="utf-8")).get("segments", [])
    except (OSError, ValueError):
        return None
    return " ".join(s["text"] for s in segs).strip() or None


def _change_activities(p: Project, ch: dict) -> list[str]:
    return [ch["activity_id"]] if ch.get("activity_id") in p.activities else p.activities_of(ch["element_id"])


def _capture_activities(p: Project) -> dict[str, set[str]]:
    """capture id -> activities it touched (element changes, absences/events linked to an activity)."""
    out: dict[str, set[str]] = {cid: set() for cid in p.captures}
    for cid, c in p.captures.items():
        for ch in c["changes"]:
            if ch["action"] != "invalid":
                out[cid].update(_change_activities(p, ch))
    for e in p.events:
        if e.get("capture_id") in out and e.get("activity_id"):
            out[e["capture_id"]].add(e["activity_id"])
    return out


def _activity_zones(p: Project) -> dict[str, list[str]]:
    """activity id -> zone ids of its elements, in seed zone order."""
    order = {z: i for i, z in enumerate(p.zones)}
    return {aid: sorted({p.elements[e]["zone"] for e in p.elements_of(aid) if p.elements[e]["zone"] in p.zones},
                        key=order.get) for aid in p.activities}


def _gaeb(p: Project) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {aid: [] for aid in p.activities}
    for lk in p.links:
        if lk["oz"] not in out[lk["activity_id"]]:
            out[lk["activity_id"]].append(lk["oz"])
    return out


def _cause(p: Project, row: dict, d: date, fc: dict) -> str | None:
    """Delay cause in German (the UI language); same reasoning as Project._cause."""
    if row["delay_d"] <= 0:
        return None
    if row["pct"] >= 100:
        return f"{row['delay_d']} AT nach Basisplan fertig"
    a = p.activities[row["id"]]
    reasons = []
    absent = p.absent_on(a["trade_id"], d)
    if absent:
        reasons.append(f"{absent:g} von {a['crew_planned']:g} {row['trade']} abwesend")
    late = [x for x in a["predecessors"] if fc[x]["delay_d"] > 0 and fc[x]["pct"] < 100]
    if late:
        reasons.append("wartet auf " + ", ".join(p.activities[x]["name"] for x in late[:3]))
    if row["pct"] < row["planned_pct"]:
        reasons.append(f"{row['pct']:.0f} % fertig statt {row['planned_pct']:.0f} % geplant")
    return "; ".join(reasons) or "hinter Plan"


def _bim(p: Project) -> bool:
    """A BIM project: it has a tessellated IFC model (bim.json, scripts/ifc_to_bim.py) or BIM storeys in its meta."""
    return (Path(seed_dir()) / "bim.json").is_file() or bool(p.meta.get("bim", "storeys" in p.meta))


def first_info() -> str | None:
    """First day with any evidence: the history snapshot or the first capture (before it the app shows the plan)."""
    p = get_project()
    dates = ([h["date"] for h in p.history_log if h.get("date")] + [c["date"] for c in p.captures.values()]
             + list(p.plan_dates))  # schedule-built days count as information (labelled "Terminplan")
    return min(dates) if dates else None


def parse_date(value: str | None) -> date:
    """ISO date or project today (None). Raises ValueError on anything else."""
    if value is None:
        return today()
    if len(value) != 10:
        raise ValueError(value)
    return date.fromisoformat(value)


# ---------- recordings ----------

def _recording(p: Project, c: dict) -> dict:
    cid, s = c["capture_id"], c.get("structured", {})
    video, photos, audio = _media(cid)
    kind = ("video" if video else "audio" if audio else "photo" if photos else
            "manual" if cid.startswith("manual-") else "plan" if cid.startswith("plan-") else "note")

    def el_name(eid: str) -> str:
        return p.elements[eid]["name_de"] if eid in p.elements else eid

    changes, proposals = [], []
    for ch in c["changes"]:
        if ch["action"] == "invalid":
            continue
        acts = _change_activities(p, ch)
        aid = acts[0] if acts else None
        if ch["action"] == "proposed":
            proposals.append({"element_id": ch["element_id"], "element_name": el_name(ch["element_id"]),
                              "state": ch["state"], "activity_id": aid})
            continue
        changes.append({"element_id": ch["element_id"], "element_name": el_name(ch["element_id"]),
                        "action": ch["action"], "state": ch["state"], "activity_id": aid,
                        "activity_name": p.activities[aid]["name"] if aid else None, "quote": ch["quote"],
                        "evidence": ch.get("evidence")})
    absences = []
    for i, ab in enumerate(s.get("absences", [])):
        ev = next((e for e in p.events if e["id"] == f"{cid}:absence:{i}"), None) or next(
            (e for e in p.events if e["type"] == "absence" and e["date"] == c["date"]
             and e["trade"].lower() == ab["trade"].lower()), None)
        absences.append({"trade": ab["trade"], "count": ab["count"], "reason": ab.get("reason"),
                         "activity_id": ev["activity_id"] if ev else None})
    events = [{"type": ev["type"], "text": ev["text"], "severity": ev["severity"], "activity_id": None}
              for ev in s.get("special_events", [])]
    zone = p.zones.get(c["zone_id"]) or {}
    return {"capture_id": cid, "time": c["ts"][11:16], "zone_id": c["zone_id"], "zone_name": zone.get("name_de"),
            "kind": kind, "transcript": _transcript(cid), "note": c.get("note"), "video": video, "photos": photos,
            "changes": changes, "proposals": proposals, "absences": absences, "events": events,
            "material": list(s.get("material_delivered", [])), "labour": list(s.get("labour_present", [])),
            "has_3d": _has_3d(cid)}


# ---------- payloads ----------

def days() -> dict:
    p = get_project()
    t = today()
    fc = p.forecast(t)
    hist_first = min((c["date"] for c in p.captures.values()), default=None)
    init = p.history_log[0]["date"] if p.history_log and p.history_log[0].get("initial") else None
    starts = [a["planned_start"] for a in p.activities.values()]
    starts += [date.fromisoformat(x) for x in (hist_first, init) if x]
    first = min(starts, default=t)
    last = max([r["baseline_finish"] for r in fc.values()] + [r["forecast_finish"] for r in fc.values()] + [t, first])
    rec: dict[str, int] = {}
    for c in p.captures.values():
        rec[c["date"]] = rec.get(c["date"], 0) + 1
    for iso in p.plan_dates:  # schedule-built days are skipped in the full load (recorded progress wins)
        rec[iso] = rec.get(iso, 0) + (0 if f"plan-{iso}" in p.captures else 1)
    evs: dict[str, int] = {}
    for e in p.events + _weather_events(p):
        evs[e["date"]] = evs.get(e["date"], 0) + 1
    out, d = [], first
    while d <= last:
        iso = d.isoformat()
        out.append({"date": iso, "workday": is_workday(d), "recordings": rec.get(iso, 0), "events": evs.get(iso, 0)})
        d += timedelta(days=1)
    return {"today": t.isoformat(), "first": first.isoformat(), "last": last.isoformat(), "days": out}


def _future_planned_pct(p: Project, d: date) -> float:
    """Project-level planned % at the start of day d, weighted like Project.curve (BoQ value, else per link)."""
    priced = any(lk["value"] for lk in p.links)
    w = {aid: 0.0 for aid in p.activities}
    for lk in p.links:
        w[lk["activity_id"]] += lk["value"] if priced else 1.0
    total = sum(w.values())
    if not total:
        return 0.0
    return round(sum(w[a] * p.planned_pct(a, d, start_of_day=True) for a in p.activities) / total, 1)


def day(d: date) -> dict:
    t = today()
    is_future = d > t
    eff = min(d, t)
    iso, eff_iso = d.isoformat(), eff.isoformat()
    p = project_as_of(eff)
    ov = p.overview(eff)
    fc = p.forecast(eff)
    k = ov["kpi"]
    kpi = {key: k[key] for key in ("pct_actual", "pct_planned", "spi", "forecast_finish", "baseline_finish", "delay_d",
                                   "open_defects")}
    if is_future:  # plan only: actuals stay at today, the plan moves on
        kpi["pct_planned"] = _future_planned_pct(p, d)
        kpi["spi"] = None
    first = first_info()
    no_info = not first or iso < first  # nothing recorded yet: no judgement (not "0 % done, late")
    if no_info:
        kpi.update(spi=None, delay_d=0, forecast_finish=kpi["baseline_finish"])

    caps = sorted((c for c in p.captures.values() if c["date"] == iso), key=lambda c: c["ts"], reverse=True)
    recordings = [_recording(p, c) for c in caps]

    zones, gaeb, cap_acts = _activity_zones(p), _gaeb(p), _capture_activities(p)
    by_act: dict[str, list[tuple[str, str]]] = {aid: [] for aid in p.activities}
    for cid, acts in cap_acts.items():
        for aid in acts:
            by_act[aid].append((p.captures[cid]["ts"], cid))
    activities = []
    for r in sorted(fc.values(), key=lambda r: (r["planned_start"], r["id"])):
        aid = r["id"]
        linked = sorted(by_act[aid])
        planned = p.planned_pct(aid, d, start_of_day=True) if is_future else r["planned_pct"]
        activities.append({
            "id": aid, "name": r["name"], "wbs": r["wbs"], "trade": r["trade"],
            "zones": [p.zones[z]["name_de"] for z in zones[aid]],
            "gaeb": [{"oz": oz, "text": p.boq[oz]["short_text"]} for oz in gaeb[aid]],
            "planned_start": r["planned_start"].isoformat(), "baseline_finish": r["baseline_finish"].isoformat(),
            "forecast_start": (r["planned_start"] if no_info else r["forecast_start"]).isoformat(),
            "forecast_finish": (r["baseline_finish"] if no_info else r["forecast_finish"]).isoformat(),
            "pct": r["pct"], "planned_pct": planned, "delay_d": 0 if no_info else r["delay_d"], "tracked": r["tracked"],
            "done": r["pct"] >= 100, "cause": None if no_info else _cause(p, r, eff, fc),
            "recordings": [{"capture_id": cid, "date": ts[:10], "time": ts[11:16]} for ts, cid in linked],
            "last_recording": linked[-1][0][:10] if linked else None,
            "predecessors": list(r["predecessors"]),
        })

    lookahead, nd = [], d
    for _ in range(3):
        nd = next_workday(nd)
        runs = [r for r in sorted(fc.values(), key=lambda r: (r["planned_start"], r["id"]))
                if r["planned_start"] <= nd <= r["baseline_finish"]
                or (r["pct"] < 100 and r["forecast_start"] <= nd <= r["forecast_finish"])]
        lookahead.append({"date": nd.isoformat(), "activities": [
            {"id": r["id"], "name": r["name"], "trade": r["trade"], "zones": [p.zones[z]["name_de"] for z in zones[r["id"]]],
             "planned_pct_by_end": p.planned_pct(r["id"], nd)} for r in runs]})

    events = [_event(e) for e in p.events if e["date"] <= eff_iso] + _weather_events(p, eff_iso)
    events.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    return {"date": iso, "today": t.isoformat(), "is_future": is_future,
            "info": {"has_data": bool(first) and iso >= first, "first": first},
            "project": {"name": p.meta.get("name"), "bim": _bim(p)}, "kpi": kpi,
            "weather": None if is_future else _weather_of(p, iso), "recordings": recordings,
            "activities": activities, "lookahead": lookahead, "events": events}


def _short(text: str, n: int = 40) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def taskgraph(d: date) -> dict:
    t = today()
    eff = min(d, t)
    iso = d.isoformat()
    p = project_as_of(eff)
    fc = p.forecast(eff)
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edges: set[tuple] = set()

    def edge(src: str, dst: str, typ: str, label: str | None = None) -> None:
        if (src, dst, typ) in seen_edges or src not in nodes or dst not in nodes:
            return
        seen_edges.add((src, dst, typ))
        edges.append({"src": src, "dst": dst, "type": typ, **({"label": label} if label else {})})

    for aid, r in fc.items():
        nodes[aid] = {"id": aid, "type": "activity", "label": r["name"], "pct": r["pct"], "delay_d": r["delay_d"],
                      "done": r["pct"] >= 100, "planned_start": r["planned_start"].isoformat(),
                      "forecast_finish": r["forecast_finish"].isoformat()}
    for oz in dict.fromkeys(lk["oz"] for lk in p.links):
        nodes[f"oz:{oz}"] = {"id": f"oz:{oz}", "type": "gaeb", "label": _short(f"{oz} {p.boq[oz]['short_text']}")}
    zones = _activity_zones(p)
    caps = sorted((c for c in p.captures.values() if c["date"] == iso), key=lambda c: c["ts"])
    for zid in dict.fromkeys([z for zs in zones.values() for z in zs] + [c["zone_id"] for c in caps]):
        if zid in p.zones:
            nodes[zid] = {"id": zid, "type": "zone", "label": p.zones[zid]["name_de"]}
    for lk in p.links:
        edge(f"oz:{lk['oz']}", lk["activity_id"], "PRICES")
    for aid, zs in zones.items():
        for z in zs:
            edge(aid, z, "IN_ZONE")
    for aid, a in p.activities.items():
        for pred in a["predecessors"]:
            edge(pred, aid, "PRECEDES")

    for c in caps:
        cid = c["capture_id"]
        video, photos, audio = _media(cid)
        kind = ("video" if video else "audio" if audio else "photo" if photos else
                "manual" if cid.startswith("manual-") else "plan" if cid.startswith("plan-") else "note")
        nodes[cid] = {"id": cid, "type": "recording", "label": f"{c['ts'][11:16]} {KIND_DE[kind]}", "date": c["date"]}
        edge(cid, c["zone_id"], "IN_ZONE")
        quotes: dict[str, str] = {}
        for ch in c["changes"]:
            if ch["action"] in ("confirmed", "unchanged"):
                for aid in _change_activities(p, ch):
                    quotes.setdefault(aid, ch["quote"])
        for aid, q in quotes.items():
            edge(cid, aid, "PROGRESSED", q)
    day_events = [_event(e) for e in p.events if e["date"] == iso]
    wev = _weather_event(iso, _weather_of(p, iso))
    for e in day_events + ([wev] if wev else []):
        nodes[e["id"]] = {"id": e["id"], "type": "event", "label": e["text"], "severity": e["severity"]}
        if e["activity_id"]:
            edge(e["id"], e["activity_id"], "AFFECTS")
        if e.get("capture_id"):
            edge(e["capture_id"], e["id"], "RAISED")
    for pr in p.proposals:
        if pr["date"] != iso:
            continue
        pid = f"prop:{pr['capture_id']}:{pr['element_id']}"
        name = p.elements[pr["element_id"]]["name_de"]
        nodes[pid] = {"id": pid, "type": "proposal",
                      "label": f"{name}: {STATE_DE.get(pr['state'], pr['state'])}? (nur Bild)"}
        ch = next((x for x in p.captures.get(pr["capture_id"], {}).get("changes", [])
                   if x["element_id"] == pr["element_id"] and x["action"] == "proposed"), {"element_id": pr["element_id"]})
        for aid in _change_activities(p, ch):
            edge(pid, aid, "PROPOSES")
        edge(pr["capture_id"], pid, "RAISED")
    return {"date": iso, "nodes": list(nodes.values()), "edges": edges}

