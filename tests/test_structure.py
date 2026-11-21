import pytest

from tagwerk.pipeline import structure
from tagwerk.pipeline.context import build_context
from tagwerk.project import Project


@pytest.fixture()
def p(monkeypatch):
    import tagwerk.pipeline.context as context

    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": None, "precipMm": None, "windKmh": None,
                                                              "source": "test"})
    proj = Project.from_seed()
    proj.load_history()
    return proj


def run(p, text, zone="Z-AUDIENCE", markers=()):
    cap = {"capture_id": "c", "zone_id": zone, "note": None}
    tr = {"capture_id": "c", "lang": "de", "segments": [{"start": 0.0, "end": 5.0, "text": text}]}
    vis = {"capture_id": "c", "frames": [{"t": 1.0, "media_path": "x", "triplets": [], "objects": [
        {"obj_id": f"o{m}", "label": "marker", "bbox": [0, 0, 1, 1], "conf": 1.0, "marker_id": m, "source": "marker"}
        for m in markers]}]}
    ctx = build_context(cap, vis, p)
    s = structure.structure.__wrapped__(cap, tr, vis, ctx, p) if hasattr(structure.structure, "__wrapped__") \
        else structure.structure(cap, tr, vis, ctx, p)
    return s


@pytest.fixture(autouse=True)
def _cache(tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from tagwerk.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_demo_sentence(p):
    s = run(p, "Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind heute krank. Die Traverse hinten ist verkabelt.")
    wd = {(tuple(w["element_ids"]), w["state_proposed"], w["evidence"]) for w in s["work_done"]}
    assert (("E-ROW-A",), "installed", "voice") in wd
    assert (("E-TRUSS-2",), "wired", "voice") in wd
    assert s["absences"] == [{"trade": "Trockenbau", "count": 2, "reason": "krank"}]
    assert not s["special_events"]  # the absence is its own event, no duplicate delay


def test_row_ranges_and_marker_both(p):
    s = run(p, "Reihen F bis H Unterkonstruktion fertig gestellt", markers=[4])
    rows = {e for w in s["work_done"] for e in w["element_ids"] if w["evidence"] != "vision"}
    assert {"E-ROW-F", "E-ROW-G", "E-ROW-H"} <= rows
    # marker 4 = row A seen but not spoken about -> vision proposal of the next state
    assert any(w["element_ids"] == ["E-ROW-A"] and w["evidence"] == "vision" for w in s["work_done"])


def test_voice_plus_marker_is_both(p):
    s = run(p, "Reihe A montiert", markers=[4])
    assert s["work_done"][0]["evidence"] == "both"


def test_labour_delivery_defect_english(p):
    s = run(p, "Drei Elektriker sind da. 40 Stühle geliefert. Kratzer an der Bühne. The projector is mounted.",
            zone="Z-STAGE")
    assert {"trade": "Elektro", "count": 3} in s["labour_present"]
    assert s["material_delivered"][0]["qty"] == 40
    assert any(e["type"] == "defect" for e in s["special_events"])
    assert any(w["element_ids"] == ["E-PROJECTOR"] and w["state_proposed"] == "mounted" for w in s["work_done"])


def test_result_is_cached_and_valid(p, tmp_path):
    from tagwerk.contracts import validate

    validate("structured", run(p, "Leinwand angeschlossen", zone="Z-STAGE"))
    assert (tmp_path / "c" / "structured.json").exists()


def test_whisper_comma_run_on(p):
    s = run(p, "Stuhlreihe A ist montiert, zwei Mann vom Trockenbau sind heute krank, die hintere Traverse ist verkabelt",
            markers=[4])
    wd = {(tuple(w["element_ids"]), w["state_proposed"], w["evidence"]) for w in s["work_done"]}
    assert (("E-ROW-A",), "installed", "both") in wd and (("E-TRUSS-2",), "wired", "voice") in wd
    assert s["absences"] == [{"trade": "Trockenbau", "count": 2, "reason": "krank"}]


def test_row_list_with_commas(p):
    s = run(p, "Reihe C, D und E sind montiert")
    assert {"E-ROW-C", "E-ROW-D", "E-ROW-E"} <= {e for w in s["work_done"] for e in w["element_ids"]}


def test_future_and_questions_are_not_progress(p):
    s = run(p, "Die Leinwand wird noch angeschlossen. Ist der Beamer montiert? Der Vorhang ist montiert.",
            zone="Z-STAGE")
    ids = {e for w in s["work_done"] for e in w["element_ids"]}
    assert "E-CURTAIN" in ids and "E-SCREEN" not in ids and "E-PROJECTOR" not in ids


def test_fehlt_about_work_is_not_an_absence(p):
    s = run(p, "Bei Reihe B fehlt noch die Unterkonstruktion")
    assert not s["absences"]
    s = run(p, "Zwei Monteure fehlen heute")
    assert s["absences"] and s["absences"][0]["count"] == 2
