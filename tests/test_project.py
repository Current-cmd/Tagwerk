from datetime import date

import pytest

from tagwerk.project import Project, workday_diff, workdays

TODAY = date(2026, 11, 26)


@pytest.fixture()
def p():
    proj = Project.from_seed()
    proj.load_history()
    return proj


def _cap(cid, work=(), absences=(), day="2026-11-26", events=()):
    return ({"capture_id": cid, "zone_id": "Z-AUDIENCE", "ts": f"{day}T09:00:00Z"},
            {"capture_id": cid, "labour_present": [], "absences": list(absences), "material_delivered": [],
             "work_done": list(work), "special_events": list(events), "unmatched": []})


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


def test_history_has_only_valid_changes(p):
    bad = [ch for c in p.captures.values() for ch in c["changes"] if ch["action"] == "invalid"]
    assert not bad


def test_finished_activity_keeps_its_real_finish(p):
    fc = p.forecast(TODAY)
    assert fc["A1020"]["pct"] == 100 and fc["A1020"]["delay_d"] == 0  # initial snapshot = on plan
    assert fc["A1040"]["pct"] == 100 and fc["A1040"]["forecast_finish"].isoformat() == "2026-11-24"


def test_repeated_absence_reports_do_not_add_up(p):
    ab = [{"trade": "Trockenbau", "count": 2, "reason": "krank"}]
    p.apply_structured(*_cap("c5", absences=ab))
    p.apply_structured(*_cap("c6", absences=ab))
    assert p.forecast(TODAY)["A1080"]["crew_today"] == 1


def test_untracked_activity_follows_predecessors(p):
    fc = p.forecast(TODAY)
    a = fc["A1090"]  # Abnahme: no elements, no manual pct
    assert a["tracked"] is False
    assert a["forecast_start"] > fc["A1080"]["forecast_finish"]


def test_absence_on_weekend_counts_from_monday(p):
    from datetime import date as d

    p.apply_structured(*_cap("c7", absences=[{"trade": "Trockenbau", "count": 2, "reason": "krank"}], day="2026-11-28"))
    assert p.absent_on("T-TROCKENBAU", d(2026, 11, 30)) == 2
    assert p.absent_on("T-TROCKENBAU", d(2026, 12, 3)) == 0


def test_exports_for_imported_project():
    from xml.etree.ElementTree import fromstring

    from tagwerk.pipeline.export import gaeb_xml, p6_xml
    from tagwerk.project import SEED_DIR

    sp_dir = SEED_DIR / "projects" / "schependomlaan"
    if not (sp_dir / "elements.csv").exists():
        import pytest

        pytest.skip("no Schependomlaan seed")
    sp = Project.from_seed(sp_dir)
    sp.load_history()
    x84 = fromstring(gaeb_xml(sp, 84))
    assert len(x84.findall(".//{*}Item")) == len(sp.boq)
    xml = p6_xml(sp, date.fromisoformat(sp.meta["data_date"]))
    assert "Schependomlaan" in xml and "Start to Start" in xml


def _events(p, kind, day="2026-11-26"):
    return [e for e in p.events if e["type"] == kind and e["date"] == day]


def test_same_day_absence_from_two_captures_is_one_event(p):
    ab = {"trade": "Trockenbau", "count": 2, "reason": "krank"}
    p.apply_structured(*_cap("d1", absences=[ab]))
    p.apply_structured(*_cap("d2", absences=[ab]))
    assert len(_events(p, "absence")) == 1
    p.apply_structured(*_cap("d3", absences=[{**ab, "trade": "trockenbau", "count": 3}]))
    (ev,) = _events(p, "absence")
    assert ev["count"] == 3 and ev["text"].startswith("3×")
    assert p.absent_on("T-TROCKENBAU", TODAY) == 3
    assert {"d1", "d2", "d3"} <= set(p.captures)  # the captures themselves are still recorded


def test_same_day_defect_with_different_casing_is_one_event(p):
    before = p.overview(TODAY)["kpi"]["open_defects"]
    p.apply_structured(*_cap("d4", events=[{"type": "defect", "text": "Scheur in de vloer bij de lift.", "severity": "low"}]))
    p.apply_structured(*_cap("d5", events=[{"type": "defect", "text": "scheur in de  vloer bij de lift", "severity": "low"}]))
    assert len([e for e in _events(p, "defect") if "scheur" in e["text"].lower()]) == 1
    assert p.overview(TODAY)["kpi"]["open_defects"] == before + 1


def test_same_defect_on_another_day_is_kept(p):
    ev = {"type": "defect", "text": "Scheur in de vloer bij de lift.", "severity": "low"}
    p.apply_structured(*_cap("d6", events=[ev]))
    p.apply_structured(*_cap("d7", events=[ev], day="2026-11-27"))
    assert len([e for e in p.events if e["type"] == "defect" and "scheur" in e["text"].lower()]) == 2
