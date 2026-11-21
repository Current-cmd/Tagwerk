"""Speech matching on a scan-generated room project: German plurals, state fallbacks, trade groups."""
from datetime import date

import pytest

from tagwerk.pipeline import structure
from tagwerk.pipeline.context import build_context
from tagwerk.pipeline.scan import CATALOG, CATEGORY_DE, seed_from_scan
from tagwerk.project import Project

SPEC = {"wall": 4, "door": 1, "window": 2, "ceiling": 1, "floor": 1, "radiator": 1, "socket": 3,
        "light fixture": 2, "tv": 1, "chair": 4, "dining table": 1}


@pytest.fixture()
def room(tmp_path, monkeypatch):
    import tagwerk.pipeline.context as context
    from tagwerk.config import get_settings

    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": None, "precipMm": None, "windKmh": None,
                                                              "source": "test"})
    items = []
    for label, n in SPEC.items():
        cat, ifc, name_de, et = CATALOG[label]
        items.append({"label": label, "category": cat, "category_de": CATEGORY_DE[cat], "ifc_class": ifc,
                      "name_de": name_de, "type": et, "frames": 5, "instances": n, "first_t": 0, "last_t": 5,
                      "best_conf": 0.8, "best": None, "sources": ["yolo"]})
    inv = {"capture_id": "rt", "frames": 5, "items": items, "transcript": None, "summary": {}, "people_max": 0,
           "element_count": sum(SPEC.values())}
    seed_from_scan(inv, tmp_path / "room", "room", date(2026, 11, 23), zone_name="Raum")
    yield Project.from_seed(tmp_path / "room")
    get_settings.cache_clear()


def say(p, text):
    cap = {"capture_id": "c", "zone_id": "Z-SITE", "note": text}
    tr = {"capture_id": "c", "lang": "de", "segments": []}
    vis = {"capture_id": "c", "frames": []}
    return structure.structure(cap, tr, vis, build_context(cap, vis, p), p)


def work(p, text):
    out = {}
    for w in say(p, text)["work_done"]:
        for e in w["element_ids"]:
            out[e] = w["state_proposed"]
    return out


@pytest.mark.parametrize("text,prefix,count,state", [
    ("Die Steckdosen sind installiert.", "S-SOCKET", 3, "installed"),
    ("Die Wände sind gestrichen.", "S-WALL", 4, "painted"),
    ("Die Stühle stehen.", "S-CHAIR", 4, "installed"),
    ("Die Leuchten hängen.", "S-LIGHT-FIXTURE", 2, "mounted"),
    ("Die Tische stehen.", "S-DINING-TABLE", 1, "installed"),
    ("Die Fenster sind eingesetzt.", "S-WINDOW", 2, "installed"),
    ("Die Türen sind eingebaut.", "S-DOOR", 1, "installed"),
])
def test_german_plurals_match_singular_names(room, text, prefix, count, state):
    w = work(room, text)
    assert len(w) == count and all(k.startswith(prefix) and v == state for k, v in w.items())


@pytest.mark.parametrize("text,prefix,count,state", [
    ("Die Steckdose ist angeschlossen.", "S-SOCKET", 3, "installed"),
    ("Die Decke ist verputzt.", "S-CEILING", 1, "started"),
    ("Die Stühle sind aufgestellt.", "S-CHAIR", 4, "installed"),
    ("Der Tisch ist aufgebaut.", "S-DINING-TABLE", 1, "installed"),
])
def test_state_fallback_for_states_missing_in_type(room, text, prefix, count, state):
    w = work(room, text)
    assert len(w) == count and all(k.startswith(prefix) and v == state for k, v in w.items())


def test_state_fallback_keeps_direct_states():
    assert structure._state_for("der lautsprecher ist angeschlossen", "av") == "connected"
    assert structure._state_for("die unterkonstruktion steht", "seat_row") == "substructure"
    assert structure._state_for("die wand ist verputzt", "wall") == "prepared"
    assert structure._state_for("die wand ist angeschlossen", "wall") is None  # no mapping target: dropped


def test_plural_forms():
    f = structure._plural_forms
    assert {"wände", "wand", "wänder"} <= set(f("wand")) and "stühle" in f("stuhl") and "dächer" in f("dach")
    assert "räume" in f("raum") and "steckdosen" in f("steckdose") and "leuchten" in f("leuchte")
    assert f("ab") == ("ab",)  # too short to inflect
    assert f("tür") == ("tür", "türen")  # 3 letters: only the -en plural (Türen), nothing that could collide


def test_absence_trade_groups(room):
    s = say(room, "Zwei Mann vom Elektriker sind krank.")
    assert s["absences"] == [{"trade": "Elektro", "count": 2, "reason": "krank"}]
    ch = room.apply_structured({"capture_id": "c", "zone_id": "Z-SITE", "ts": "2026-11-23T09:00:00Z"}, s)
    assert ch == [] and room.events[-1]["activity_id"] == "A030"
    assert room.absent_on("T-TGA", date(2026, 11, 23)) == 2
    assert room.absent_on("T-ROH", date(2026, 11, 23)) == 0


def test_tga_is_a_trade_word_and_exact_names_win(room):
    assert say(room, "Zwei Mann vom TGA sind krank.")["absences"][0]["trade"] == "TGA"
    assert room.trade_by_name("TGA")["id"] == "T-TGA" and room.trade_by_name("Maler")["id"] == "T-AUS"
    assert room.trade_by_name("Tischler")["id"] == "T-FEN" and room.trade_by_name("Gärtner") is None


def test_hoersaal_trades_unchanged():
    p = Project.from_seed()
    assert p.trade_by_name("Trockenbau")["id"] == "T-TROCKENBAU" and p.trade_by_name("Elektro")["id"] == "T-ELEKTRO"
    assert p.trade_by_name("Maler")["id"] == "T-MALER" and p.trade_by_name("Tischler")["id"] == "T-TISCHLER"
