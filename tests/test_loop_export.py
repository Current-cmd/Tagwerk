from tagwerk.pipeline.export import captures_to_ics
from tagwerk.pipeline.loop import apply_work


def test_voice_confirms_vision_proposes():
    row = {"type": "seat_row", "pct": 20}
    assert apply_work(row, "installed", "voice") == {"action": "confirmed", "pct": 85}
    assert apply_work(row, "installed", "vision")["action"] == "proposed"


def test_state_never_goes_down():
    row = {"type": "seat_row", "pct": 85}
    assert apply_work(row, "removed", "voice") == {"action": "unchanged", "pct": 85}


def test_unknown_type_uses_default_states():
    assert apply_work({"type": "door"}, "installed", "both")["pct"] == 70


def test_ics_is_utc_with_stable_uid():
    ics = captures_to_ics([{"capture_id": "c1", "ts_server": "2026-11-26T08:12:03Z", "zone_id": "Z-STAGE"}])
    assert "UID:capture-c1@tagwerk" in ics
    assert "DTSTART:20261126T081203Z" in ics
    assert "TZID" not in ics
