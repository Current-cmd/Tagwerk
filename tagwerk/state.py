"""Process-wide project state: seed + history + every stored capture result, rebuilt at startup."""
import json
import logging
from datetime import date
from pathlib import Path

from tagwerk.config import get_settings
from tagwerk.project import Project

log = logging.getLogger(__name__)
_project: Project | None = None


def results_dir() -> Path:
    d = Path(get_settings().data_dir) / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def today() -> date:
    return date.fromisoformat(get_settings().data_date)


def get_project() -> Project:
    global _project
    if _project is None:
        p = Project.from_seed()
        p.load_history()
        for f in sorted(results_dir().glob("*.json"), key=lambda f: json.loads(f.read_text())["meta"]["ts"]):
            r = json.loads(f.read_text(encoding="utf-8"))
            p.apply_structured(r["meta"], r["structured"])
            p.captures[r["meta"]["capture_id"]].update({k: r["meta"][k] for k in ("photos", "weather", "lang")
                                                         if k in r["meta"]})
        _project = p
        log.info("project: %d elements, %d activities, %d captures", len(p.elements), len(p.activities),
                 len(p.captures))
    return _project


def save_result(meta: dict, structured: dict) -> None:
    (results_dir() / f"{meta['capture_id']}.json").write_text(
        json.dumps({"meta": meta, "structured": structured}, ensure_ascii=False, indent=1), encoding="utf-8")


def reset() -> None:
    global _project
    _project = None
