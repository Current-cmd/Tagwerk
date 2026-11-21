"""Schedule-built history (tagwerk.plan_history): data over the whole lifecycle, never overriding recorded progress."""
import json
from datetime import date

import pytest

from tagwerk.contracts import validate
from tagwerk.project import SEED_DIR, Project
from tests.test_v2 import SP, _client


def test_plan_days_follow_the_schedule():
    from tagwerk.plan_history import plan_days, plan_state

    p = Project.from_seed(SEED_DIR)
    days = plan_days(p, date(2026, 11, 9), date(2026, 11, 20), "day")
    assert [d["date"] for d in days] == ["2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13",
                                         "2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19"]
    for d in days:
        c = d["captures"][0]
        assert d["source"] == "plan" and c["capture_id"] == f"plan-{d['date']}" and "Terminplan" in c["note"]
        validate("structured", {"capture_id": c["capture_id"], **c["structured"]})
    assert plan_state(p, "E-ROW-A", date(2026, 11, 12)) == "removed"  # A1020 (Rückbau) finished 11.11. by plan
    assert plan_state(p, "E-ROW-A", date(2026, 11, 8)) is None


def test_recorded_progress_wins_over_the_plan(tmp_path):
    """The full load (today) is the same with or without the plan days."""
    hist = json.loads((SEED_DIR / "history.json").read_text(encoding="utf-8"))
    assert any(d.get("source") == "plan" for d in hist["days"])
    stripped = tmp_path / "history.json"
    stripped.write_text(json.dumps({**hist, "days": [d for d in hist["days"] if d.get("source") != "plan"]}),
                        encoding="utf-8")
    a, b = Project.from_seed(SEED_DIR), Project.from_seed(SEED_DIR)
    a.load_history()
    b.load_history(stripped)
    assert {e: x["pct"] for e, x in a.elements.items()} == {e: x["pct"] for e, x in b.elements.items()}
    assert a.forecast(date(2026, 11, 26)) == b.forecast(date(2026, 11, 26))


def test_slider_has_data_over_the_whole_lifecycle(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as c:
        days = {d["date"]: d for d in c.get("/api/v2/days").json()["days"]}
        assert all(days[d]["recordings"] >= 1 for d in ("2026-11-09", "2026-11-12", "2026-11-19", "2026-11-23"))
        d12 = c.get("/api/v2/day", params={"date": "2026-11-12"}).json()
        assert d12["info"] == {"has_data": True, "first": "2026-11-09"}
        assert [r["kind"] for r in d12["recordings"]] == ["plan"]
        assert d12["kpi"]["pct_actual"] > 0
        before = c.get("/api/v2/day", params={"date": "2026-11-06"}).json()  # before the project start
        assert before["info"]["has_data"] is False


@pytest.mark.skipif(not (SP / "elements.csv").exists(), reason="run scripts/import_schependomlaan.py")
def test_schependomlaan_lifecycle_has_weekly_points(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, "schependomlaan") as c:
        days = c.get("/api/v2/days").json()["days"]
        with_data = [d["date"] for d in days if d["recordings"]]
        assert len(with_data) >= 20 and with_data[0] < "2015-03-01"
        assert c.get("/api/v2/day", params={"date": "2015-07-24"}).json()["kpi"]["pct_actual"] == pytest.approx(83.7, abs=0.1)
