"""History from the schedule for the time before the first recorded evidence ("Soll-Stand aus dem Terminplan").

Each plan day is a capture `plan-<date>` with the element states the baseline schedule expects by that day
(per link: activity finished by plan -> its target state, started -> the element's first state) and the planned crews
of the running activities. Plan days are stored in history.json with `"source": "plan"` and are only used before the
first real snapshot/capture: they never override recorded progress (Project.load_history skips them once the
initial snapshot applies).
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from tagwerk.labels import STATE_DE
from tagwerk.pipeline.loop import STATES, weight
from tagwerk.project import Project, is_workday

PLAN_NOTE = "Soll-Stand aus dem Terminplan (keine Aufnahme)"


def _states(el: dict) -> list[tuple[str, int]]:
    return STATES.get(el["type"], STATES["default"])


def plan_state(p: Project, eid: str, d: date) -> str | None:
    """The state the baseline schedule expects for element eid at the end of day d (None: not started)."""
    el = p.elements[eid]
    best: tuple[int, str] | None = None
    for lk in p._by_el.get(eid, []):
        a = p.activities[lk["activity_id"]]
        if a["planned_finish"] <= d:
            st = lk["to_state"] or _states(el)[-1][0]
        elif a["planned_start"] <= d:
            st = _states(el)[0][0]
        else:
            continue
        w = weight(el["type"], st)
        if best is None or w > best[0]:
            best = (w, st)
    return best[1] if best else None


def plan_days(p: Project, start: date, end: date, every: str = "week") -> list[dict]:
    """History days from start to end (exclusive): every working day ("day") or every Friday ("week")."""
    reached: dict[str, int] = {}
    out, d = [], start
    while d < end:
        if is_workday(d) and (every == "day" or d.weekday() == 4):
            out.append(_day(p, d, reached))
        d += timedelta(days=1)
    return [x for x in out if x]


def _day(p: Project, d: date, reached: dict[str, int]) -> dict | None:
    groups: dict[tuple[str | None, str], list[str]] = {}
    for eid, el in p.elements.items():
        st = plan_state(p, eid, d)
        if st is None:
            continue
        w = weight(el["type"], st)
        if w <= reached.get(eid, 0):
            continue
        reached[eid] = w
        acts = p.activities_of(eid)
        groups.setdefault((acts[0] if acts else None, st), []).append(eid)
    running = [a for a in p.activities.values() if a["planned_start"] <= d <= a["planned_finish"]]
    if not groups and not running:
        return None
    work = [{"element_ids": eids, "activity_id": aid, "state_proposed": st, "evidence": "voice",
             "quote": f"Terminplan: {p.activities[aid]['name'] if aid else 'Bauteile'} {STATE_DE.get(st, st)}", "t": None}
            for (aid, st), eids in sorted(groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1]))]
    crews: Counter[str] = Counter()
    for a in running:
        trade = p.trades.get(a["trade_id"], {}).get("name") or a["trade_id"]
        crews[trade] += max(1, round(a["crew_planned"]))
    zones = Counter(p.elements[e]["zone"] for g in groups.values() for e in g if p.elements[e]["zone"] in p.zones)
    zone = zones.most_common(1)[0][0] if zones else next(iter(p.zones))
    iso = d.isoformat()
    return {"date": iso, "source": "plan", "captures": [{
        "capture_id": f"plan-{iso}", "zone_id": zone, "ts": f"{iso}T07:00:00Z", "lang": "de", "note": PLAN_NOTE,
        "structured": {"labour_present": [{"trade": t, "count": n} for t, n in sorted(crews.items())], "absences": [],
                       "material_delivered": [], "work_done": work, "special_events": [], "unmatched": []}}]}
