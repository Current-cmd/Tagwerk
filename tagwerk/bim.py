"""BIM viewer data: the tessellated IFC model of the project (bim.json + bim.bin from scripts/ifc_to_bim.py, next to
the project's seed files) and the element states as of day D keyed by IFC GlobalId."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from tagwerk import v2
from tagwerk.labels import STATE_DE
from tagwerk.pipeline.loop import weight
from tagwerk.state import seed_dir


def model_dir() -> Path:
    return Path(seed_dir())


def model_file(name: str) -> Path | None:
    f = model_dir() / name
    return f if f.is_file() else None


def _global_ids() -> dict[str, str]:
    """IFC GlobalId -> element id (elements.csv `global_id`)."""
    p = v2.get_project()
    return {el["global_id"]: eid for eid, el in p.elements.items() if el.get("global_id")}


def states(d: date) -> dict:
    import json

    meta = model_file("bim.json")
    if meta is None:
        return {"available": False, "source": None, "date": d.isoformat(), "is_future": False, "mode": "actual",
                "elements": []}
    source = json.loads(meta.read_text(encoding="utf-8")).get("source")
    t = v2.today()
    is_future = d > t
    first = v2.first_info()
    mode = "forecast" if is_future else "plan" if (first is None or d.isoformat() < first) else "actual"
    p = v2.project_as_of(min(d, t))
    fc = p.forecast(t) if is_future else {}
    out = []
    for gid, eid in _global_ids().items():
        el = p.elements.get(eid)
        if not el:
            continue
        targets = [weight(el["type"], lk["to_state"]) if lk["to_state"] else 100 for lk in p._by_el.get(eid, [])]
        done = el["pct"] > 0 and el["pct"] >= max(targets or [100])  # reached what its activities ask for
        acts = p.activities_of(eid)
        planned, pct = False, el["pct"]
        if mode == "plan" and acts:  # no evidence yet: the baseline schedule, per link (finished -> its target)
            reached = 0
            for lk in p._by_el.get(eid, []):
                a = p.activities[lk["activity_id"]]
                hi = weight(el["type"], lk["to_state"]) if lk["to_state"] else 100
                reached = max(reached, hi if a["planned_finish"] < d else 1 if a["planned_start"] <= d else 0)
            pct, planned = reached, reached > 0
            done = reached > 0 and reached >= max(targets or [100])
        if is_future and not done and acts:  # after the data date: the forecast schedule (as of today) plays on
            if all(fc[a]["forecast_finish"] < d for a in acts):
                done, planned, pct = True, True, max(targets or [100])
            elif any(fc[a]["forecast_start"] <= d for a in acts):
                planned, pct = True, max(pct, 1)
        aid = acts[0] if acts else None
        out.append({"gid": gid, "element_id": eid, "name": el["name_de"], "pct": pct, "done": done, "planned": planned,
                    "state": el["state"],
                    "state_de": STATE_DE.get(el["state"], el["state"]) if el["state"] else "nicht begonnen",
                    "activity_id": aid, "activity_name": p.activities[aid]["name"] if aid else None,
                    "zone": (p.zones.get(el["zone"]) or {}).get("name_de")})
    return {"available": True, "source": source, "date": d.isoformat(), "is_future": is_future, "mode": mode,
            "first": first, "elements": out}
