from datetime import date

import pytest

from tagwerk.project import Project, workday_diff, workdays

TODAY = date(2026, 11, 26)


@pytest.fixture()
def p():
    proj = Project.from_seed()
    proj.load_history()
    return proj


def _cap(cid, work=(), absences=(), day="2026-11-26"):
    return ({"capture_id": cid, "zone_id": "Z-AUDIENCE", "ts": f"{day}T09:00:00Z"},
            {"capture_id": cid, "labour_present": [], "absences": list(absences), "material_delivered": [],
             "work_done": list(work), "special_events": [], "unmatched": []})


def test_workdays():
    assert len(workdays(date(2026, 11, 23), date(2026, 11, 27))) == 5
    assert workday_diff(date(2026, 11, 26), date(2026, 11, 30)) == 2


def test_seed_is_consistent(p):
    assert len(p.elements) >= 30 and len(p.activities) == 10
    for oz in p.boq:  # shares per BoQ position sum to 1
        assert abs(sum(lk["share"] for lk in p.links if lk["oz"] == oz) - 1) < 0.01, oz


def test_history_rollup(p):
    assert p.activity_pct("A1020") == 100.0  # all rows removed
    assert p.activity_pct("A1010") == 100.0  # manual
    assert 0 < p.activity_pct("A1080") < 50


def test_budget_matches_hand_calculation(p):
    assert p.budget("A1080") == 160 * 265
    assert p.budget("A1060") == 9800 + 7400


def test_voice_confirm_is_idempotent(p):
    w = {"element_ids": ["E-ROW-A"], "activity_id": "A1080", "state_proposed": "installed", "evidence": "voice",
         "quote": "Reihe A montiert", "t": 1.0}
    p.apply_structured(*_cap("c1", [w]))
    pct = p.activity_pct("A1080")
    p.apply_structured(*_cap("c1", [w]))
    p.apply_structured(*_cap("c2", [w]))
    assert p.activity_pct("A1080") == pct and p.elements["E-ROW-A"]["pct"] == 85


def test_vision_only_proposes(p):
    w = {"element_ids": ["E-ROW-H"], "activity_id": None, "state_proposed": "substructure", "evidence": "vision",
         "quote": "marker", "t": None}
    ch = p.apply_structured(*_cap("c3", [w]))
    assert ch[0]["action"] == "proposed" and p.elements["E-ROW-H"]["pct"] == 20


def test_absence_moves_forecast_and_successor(p):
    base = p.forecast(TODAY)
    p.apply_structured(*_cap("c4", absences=[{"trade": "Trockenbau", "count": 2, "reason": "krank"}]))
    sick = p.forecast(TODAY)
    assert sick["A1080"]["forecast_finish"] > base["A1080"]["forecast_finish"]
    assert sick["A1090"]["forecast_finish"] > base["A1090"]["forecast_finish"]  # Abnahme follows
    assert sick["A1080"]["crew_today"] == 1


def test_dashboard_contract(p):
    from tagwerk.contracts import validate

    validate("dashboard", p.dashboard(TODAY))
    ov = p.overview(TODAY)
    assert ov["kpi"]["spi"] is not None and ov["kpi"]["delay_d"] >= 0
    assert ov["curve"][-1]["ev"] is not None


def test_p6_and_gaeb_export_parse(p):
    from xml.etree.ElementTree import fromstring

    from tagwerk.pipeline.export import gaeb_xml, p6_xml

    root = fromstring(p6_xml(p, TODAY))
    ns = {"p": "http://xmlns.oracle.com/Primavera/P6/V8.3/API/BusinessObjects"}
    acts = root.findall("p:Project/p:Activity", ns)
    assert len(acts) == 10
    assert len(root.findall("p:Project/p:Relationship", ns)) == sum(len(a["predecessors"])
                                                                   for a in p.activities.values())
    x84 = fromstring(gaeb_xml(p, 84))
    assert len(x84.findall(".//{*}Item")) == len(p.boq)
