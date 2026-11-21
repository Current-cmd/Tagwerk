"""Fill history.json with schedule-built days ("Soll-Stand aus dem Terminplan") from the project start up to the first
recorded snapshot/capture, so the day slider has data over the whole lifecycle. Idempotent (old plan days replaced).

    python scripts/build_plan_history.py seed --every day                          # Hörsaal: every working day
    python scripts/build_plan_history.py seed/projects/schependomlaan --every week # Schependomlaan: every Friday
"""
import argparse
import json
from datetime import date
from pathlib import Path

from tagwerk.plan_history import plan_days
from tagwerk.project import Project

ap = argparse.ArgumentParser()
ap.add_argument("seed", type=Path)
ap.add_argument("--every", choices=("day", "week"), default="week")
a = ap.parse_args()
path = a.seed / "history.json"
hist = json.loads(path.read_text(encoding="utf-8"))
real = [d for d in hist.get("days", []) if d.get("source") != "plan"]
firsts = [x for x in [hist.get("initial", {}).get("date")] + [d["date"] for d in real] if x]
p = Project.from_seed(a.seed)
start = min(act["planned_start"] for act in p.activities.values())
end = date.fromisoformat(min(firsts)) if firsts else date.today()
plan = plan_days(p, start, end, a.every)
hist["days"] = sorted(plan + real, key=lambda d: d["date"])
path.write_text(json.dumps(hist, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"{len(plan)} plan days {start}..{end} (exclusive) -> {path}")
