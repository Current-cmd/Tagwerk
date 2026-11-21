"""Every phrase in docs/DEMO.md must visibly change the freshly reset demo state."""
from datetime import date

import pytest

from tagwerk.pipeline import structure
from tagwerk.pipeline.context import build_context
from tagwerk.project import Project

PHRASES = [
    ("Z-AUDIENCE", "Stuhlreihe A ist montiert"),
    ("Z-AUDIENCE", "Reihen F bis H Unterkonstruktion"),
    ("Z-AUDIENCE", "zwei Mann vom Trockenbau sind krank"),
    ("Z-STAGE", "Lautsprecher links und Lautsprecher rechts angeschlossen"),
    ("Z-STAGE", "die Leinwand ist in Betrieb"),
    ("Z-STAGE", "40 Stühle geliefert"),
    ("Z-STAGE", "Kratzer an der Bühne"),
]


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    import tagwerk.pipeline.context as context
    from tagwerk.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": None, "precipMm": None, "windKmh": None,
                                                              "source": "test"})
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize("zone,phrase", PHRASES)
def test_phrase_changes_state(zone, phrase):
    p = Project.from_seed()
    p.load_history()
    cid = "demo-" + str(abs(hash(phrase)))[:8]
    cap = {"capture_id": cid, "zone_id": zone, "note": phrase}
    vis = {"capture_id": cid, "frames": []}
    s = structure.structure(cap, {"capture_id": cid, "lang": "de", "segments": []}, vis, build_context(cap, vis, p), p)
    changes = p.apply_structured({"capture_id": cid, "zone_id": zone, "ts": "2026-11-26T09:00:00Z"}, s)
    moved = [c for c in changes if c["action"] == "confirmed"]
    assert moved or s["absences"] or s["material_delivered"] or s["special_events"], (phrase, changes)


def test_baseline_has_no_delay_without_evidence():
    p = Project.from_seed()  # no history: nothing reported yet
    fc = p.forecast(date(2026, 11, 2))
    assert all(r["delay_d"] <= 0 for r in fc.values()), {k: v["delay_d"] for k, v in fc.items() if v["delay_d"] > 0}


def test_both_speakers_connected_by_the_demo_phrase():
    p = Project.from_seed()
    p.load_history()
    phrase = "Lautsprecher links und Lautsprecher rechts angeschlossen"
    cap = {"capture_id": "spk", "zone_id": "Z-STAGE", "note": phrase}
    vis = {"capture_id": "spk", "frames": []}
    s = structure.structure(cap, {"capture_id": "spk", "lang": "de", "segments": []}, vis, build_context(cap, vis, p), p)
    ch = p.apply_structured({"capture_id": "spk", "zone_id": "Z-STAGE", "ts": "2026-11-26T09:00:00Z"}, s)
    assert {(c["element_id"], c["state"]) for c in ch if c["action"] == "confirmed"} >= {
        ("E-SPK-L", "connected"), ("E-SPK-R", "connected")}
