"""Process-wide project state: seed + history + every stored capture result, rebuilt at startup.

PROJECT selects the seed: "hoersaal" -> seed/, anything else -> seed/projects/<PROJECT>/.
"""
import json
import logging
from datetime import date
from pathlib import Path

from tagwerk.config import get_settings
from tagwerk.project import SEED_DIR, Project

log = logging.getLogger(__name__)
_project: Project | None = None


def seed_dir() -> Path:
    name = get_settings().project
    return SEED_DIR if name in ("", "hoersaal") else SEED_DIR / "projects" / name


def results_dir() -> Path:
    name = get_settings().project
    d = Path(get_settings().data_dir) / ("results" if name in ("", "hoersaal") else f"results-{name}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def today() -> date:
    """The forecast's "today": the project's data_date (project.json) or DATA_DATE."""
    p = get_project()
    return date.fromisoformat(p.meta.get("data_date") or get_settings().data_date)


def get_project() -> Project:
    global _project
    if _project is None:
        p = Project.from_seed(seed_dir())
        p.load_history()
        results = []
        for f in results_dir().glob("*.json"):
            try:
                results.append(json.loads(f.read_text(encoding="utf-8")))
            except (OSError, ValueError, KeyError) as exc:  # one broken file must not take the API down
                log.warning("skipping unreadable result %s: %s", f.name, exc)
        for r in sorted(results, key=lambda r: r["meta"]["ts"]):
            p.apply_structured(r["meta"], r["structured"])
            p.captures[r["meta"]["capture_id"]].update({k: r["meta"][k] for k in ("photos", "weather", "lang")
                                                         if k in r["meta"]})
        _project = p
        log.info("project %s: %d elements, %d activities, %d captures", p.meta.get("name"), len(p.elements),
                 len(p.activities), len(p.captures))
    return _project


def save_result(meta: dict, structured: dict) -> None:
    import os

    final = results_dir() / f"{meta['capture_id']}.json"
    tmp = final.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"meta": meta, "structured": structured}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, final)  # atomic: a crash never leaves a truncated result


def reset() -> None:
    global _project
    _project = None
