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
        return {"available": False, "source": None, "date": d.isoformat(), "elements": []}
    source = json.loads(meta.read_text(encoding="utf-8")).get("source")
    p = v2.project_as_of(min(d, v2.today()))
    out = []
    for gid, eid in _global_ids().items():
        el = p.elements.get(eid)
        if not el:
            continue
        targets = [weight(el["type"], lk["to_state"]) if lk["to_state"] else 100 for lk in p._by_el.get(eid, [])]
        done = el["pct"] > 0 and el["pct"] >= max(targets or [100])  # reached what its activities ask for
        acts = p.activities_of(eid)
        aid = acts[0] if acts else None
        out.append({"gid": gid, "element_id": eid, "name": el["name_de"], "pct": el["pct"], "done": done,
                    "state": el["state"],
                    "state_de": STATE_DE.get(el["state"], el["state"]) if el["state"] else "nicht begonnen",
                    "activity_id": aid, "activity_name": p.activities[aid]["name"] if aid else None,
                    "zone": (p.zones.get(el["zone"]) or {}).get("name_de")})
    return {"available": True, "source": source, "date": d.isoformat(), "elements": out}
