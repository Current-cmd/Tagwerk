"""UI v2 API (docs/UI-V2-CONTRACT.md): days, day snapshot "as of day D", task graph, SPA routes."""
import time

import pytest
from fastapi.testclient import TestClient

from tagwerk.project import SEED_DIR

COST_KEYS = {"ev_eur", "pv_eur", "ac_eur", "bac_eur", "ac_note", "rate_eur_h", "unit_price"}
NOTE = "Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind heute krank."


def _client(tmp_path, monkeypatch, project="hoersaal"):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("NEO4J_URI", "")
    monkeypatch.setenv("GPU_WORKER_URL", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("REPLAY_MODE", "false")
    monkeypatch.setenv("PROJECT", project)
    import tagwerk.graph.store as store
    import tagwerk.pipeline.context as context
    import tagwerk.state as state
    import tagwerk.v2 as v2
    from tagwerk.config import get_settings
    from tagwerk.pipeline import speech, vision

    get_settings.cache_clear()
    store._store = None
    state.reset()
    v2.clear_cache()
    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": 5.0, "precipMm": 0.0, "windKmh": 8.0,
                                                              "source": "test"})
    monkeypatch.setattr(speech, "transcribe", lambda capture, derived: {"capture_id": capture["capture_id"],
                                                                        "lang": "de", "segments": []})
    monkeypatch.setattr(vision, "analyse", lambda capture, derived: {"capture_id": capture["capture_id"], "frames": []})
    from tagwerk.api.app import _results, app

    _results.clear()
    return TestClient(app)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as c:
        yield c


def _post_note(client, cid="cap-v2"):
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "lang": "de", "capture_id": cid, "note": NOTE},
                    files={"files": ("walk.jpg", b"\x00" * 10, "image/jpeg")})
    assert r.status_code == 200, r.text
    return r.json()


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_days_range_and_counts(client):
    body = client.get("/api/v2/days").json()
    assert body["today"] == "2026-11-26" and body["first"] == "2026-11-09"
    dates = [d["date"] for d in body["days"]]
    assert dates[0] == body["first"] and dates[-1] == body["last"] and body["last"] >= "2026-11-27"
    assert len(dates) == len(set(dates)) and sorted(dates) == dates
    by = {d["date"]: d for d in body["days"]}
    assert by["2026-11-23"]["recordings"] == 2 and by["2026-11-25"]["recordings"] == 2
    assert by["2026-11-26"]["recordings"] == 0
    assert by["2026-11-25"]["events"] >= 1  # the late chair delivery
    assert by["2026-11-21"]["workday"] is False and by["2026-11-23"]["workday"] is True
    _post_note(client)
    by = {d["date"]: d for d in client.get("/api/v2/days").json()["days"]}
    assert by["2026-11-26"]["recordings"] == 1 and by["2026-11-26"]["events"] >= 1


def test_day_past_uses_history_up_to_that_day(client):
    d24 = client.get("/api/v2/day", params={"date": "2026-11-24"}).json()
    d25 = client.get("/api/v2/day", params={"date": "2026-11-25"}).json()
    assert d24["date"] == "2026-11-24" and d24["today"] == "2026-11-26" and d24["is_future"] is False
    assert d24["project"] == {"name": "Hörsaal Sanierung", "bim": False}
    assert [r["capture_id"] for r in d24["recordings"]] == ["hist-1124-b", "hist-1124-a"]  # newest first
    starts = [a["planned_start"] for a in d24["activities"]]
    assert starts == sorted(starts) and len(starts) == 10
    a24 = {a["id"]: a for a in d24["activities"]}
    a25 = {a["id"]: a for a in d25["activities"]}
    assert a24["A1080"]["pct"] < a25["A1080"]["pct"]  # rows D/E substructure only on the 25th
    assert all(e["date"] <= "2026-11-24" for e in d24["events"])
    assert not any("Reihe F" in e["text"] for e in d24["events"])
    assert any("Reihe F" in e["text"] for e in d25["events"])
    act = a25["A1080"]
    assert act["zones"] == ["Zuschauerraum"] and act["gaeb"] and all(set(g) == {"oz", "text"} for g in act["gaeb"])
    assert {"capture_id": "hist-1125-a", "date": "2026-11-25", "time": "08:20"} in act["recordings"]
    assert act["last_recording"] == "2026-11-25"
    assert act["predecessors"] == ["A1030", "A1070"]
    assert len(d24["lookahead"]) == 3 and d24["lookahead"][0]["date"] == "2026-11-25"
    assert {"id", "name", "trade", "zones", "planned_pct_by_end"} <= set(d24["lookahead"][0]["activities"][0])
    rec = d25["recordings"][-1]
    assert rec["capture_id"] == "hist-1125-a" and rec["time"] == "08:20" and rec["zone_name"] == "Zuschauerraum"
    ch = next(c for c in rec["changes"] if c["element_id"] == "E-ROW-D")
    assert ch == {"element_id": "E-ROW-D", "element_name": ch["element_name"], "action": "confirmed",
                  "state": "substructure", "activity_id": "A1080", "activity_name": "Bestuhlung neu",
                  "quote": "Unterkonstruktion Reihe D und E", "evidence": "voice"}


def test_day_today_after_typed_note(client):
    _post_note(client)
    day = client.get("/api/v2/day").json()  # default: project today
    assert day["date"] == day["today"] == "2026-11-26" and day["is_future"] is False
    assert day["weather"] == {"tempC": 5.0, "precipMm": 0.0, "windKmh": 8.0, "source": "test"}
    assert [r["capture_id"] for r in day["recordings"]] == ["cap-v2"]
    rec = day["recordings"][0]
    assert rec["kind"] == "photo" and rec["note"] == NOTE and rec["video"] is None
    assert rec["photos"] == ["/media/cap-v2/00_walk.jpg"]
    assert client.get(rec["photos"][0]).status_code == 200
    row = next(c for c in rec["changes"] if c["element_id"] == "E-ROW-A")
    assert row["element_name"] == "Stuhlreihe A" and row["state"] == "installed" and row["activity_id"] == "A1080"
    assert rec["absences"] == [{"trade": "Trockenbau", "count": 2, "reason": "krank", "activity_id": "A1080"}]
    ev = next(e for e in day["events"] if e["type"] == "absence")
    assert ev["capture_id"] == "cap-v2" and ev["source"] == "capture" and ev["date"] == "2026-11-26"
    a = {x["id"]: x for x in day["activities"]}["A1080"]
    assert "cap-v2" in [r["capture_id"] for r in a["recordings"]] and a["last_recording"] == "2026-11-26"
    assert a["recordings"] == sorted(a["recordings"], key=lambda r: (r["date"], r["time"]))  # oldest first
    assert set(day["kpi"]) == {"pct_actual", "pct_planned", "spi", "forecast_finish", "baseline_finish", "delay_d",
                               "open_defects"}
    # the day before is unaffected by today's capture
    d25 = client.get("/api/v2/day", params={"date": "2026-11-25"}).json()
    assert all(r["capture_id"] != "cap-v2" for r in d25["recordings"])


def test_day_future_is_plan_only(client):
    today = client.get("/api/v2/day").json()
    fut = client.get("/api/v2/day", params={"date": "2026-12-01"}).json()
    assert fut["is_future"] is True and fut["recordings"] == [] and fut["today"] == "2026-11-26"
    pct_today = {a["id"]: a["pct"] for a in today["activities"]}
    assert {a["id"]: a["pct"] for a in fut["activities"]} == pct_today
    assert fut["kpi"]["pct_planned"] >= today["kpi"]["pct_planned"]


def test_no_cost_fields_anywhere(client):
    _post_note(client)
    for url in ("/api/v2/days", "/api/v2/day", "/api/v2/day?date=2026-11-24", "/api/v2/day?date=2026-12-02",
                "/api/v2/taskgraph", "/api/v2/taskgraph?date=2026-11-25"):
        keys = set(_keys(client.get(url).json()))
        assert not keys & COST_KEYS, (url, keys & COST_KEYS)
        assert not any("eur" in k.lower() or "cost" in k.lower() for k in keys), url


def test_taskgraph_links_capture_to_activity(client):
    _post_note(client)
    g = client.get("/api/v2/taskgraph", params={"date": "2026-11-26"}).json()
    assert g["date"] == "2026-11-26"
    types = {n["type"] for n in g["nodes"]}
    assert types <= {"gaeb", "activity", "zone", "recording", "event", "proposal"}
    assert {"gaeb", "activity", "zone", "recording", "event"} <= types
    ids = {n["id"] for n in g["nodes"]}
    assert "E-ROW-A" not in ids and len(ids) == len(g["nodes"])
    assert all(e["src"] in ids and e["dst"] in ids for e in g["edges"])
    edges = {(e["src"], e["dst"], e["type"]) for e in g["edges"]}
    assert ("cap-v2", "A1080", "PROGRESSED") in edges
    assert ("A1070", "A1080", "PRECEDES") in edges and ("A1080", "Z-AUDIENCE", "IN_ZONE") in edges
    assert any(t == "PRICES" and d == "A1080" for _, d, t in edges)
    assert any(t == "AFFECTS" and d == "A1080" for _, d, t in edges)
    rec = next(n for n in g["nodes"] if n["id"] == "cap-v2")
    assert rec["type"] == "recording" and rec["date"] == "2026-11-26"
    # recordings of other days are not in the graph
    assert not any(n["type"] == "recording" and n["id"].startswith("hist-") for n in g["nodes"])
    g25 = client.get("/api/v2/taskgraph", params={"date": "2026-11-25"}).json()
    assert {n["id"] for n in g25["nodes"] if n["type"] == "recording"} == {"hist-1125-a", "hist-1125-b"}


def test_bad_date_rejected(client):
    for bad in ("2026-13-01", "yesterday", "26.11.2026", ""):
        assert client.get("/api/v2/day", params={"date": bad}).status_code == 400, bad
        assert client.get("/api/v2/taskgraph", params={"date": bad}).status_code == 400, bad


def test_spa_routes_and_path_confinement(client):
    r = client.get("/app")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    r = client.get("/app/some/client/route")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    for evil in ("/app/..%2f..%2fpyproject.toml", "/app/assets/..%2f..%2f..%2fpyproject.toml",
                 "/app/%2e%2e/%2e%2e/pyproject.toml", "/app/assets/%2e%2e/%2e%2e/%2e%2e/tagwerk/config.py"):
        r = client.get(evil)
        assert "[project]" not in r.text and "BaseSettings" not in r.text, evil


def test_hoersaal_day_is_fast(client):
    client.get("/api/v2/day", params={"date": "2026-11-20"})  # warm imports
    t = time.perf_counter()
    for d in ("2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"):
        assert client.get("/api/v2/day", params={"date": d}).status_code == 200
    assert (time.perf_counter() - t) / 4 < 0.3


SP = SEED_DIR / "projects" / "schependomlaan"


@pytest.mark.skipif(not (SP / "elements.csv").exists(), reason="run scripts/import_schependomlaan.py")
def test_schependomlaan_snapshot(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, "schependomlaan") as c:
        days = c.get("/api/v2/days").json()
        assert days["today"] == "2015-07-24"
        t = time.perf_counter()
        day = c.get("/api/v2/day", params={"date": "2015-07-17"}).json()
        elapsed = time.perf_counter() - t
        assert elapsed < 1.5, elapsed
        assert day["project"]["bim"] is True and len(day["activities"]) == 100
        assert day["recordings"] and day["kpi"]["pct_actual"] > 0
        t = time.perf_counter()
        g = c.get("/api/v2/taskgraph", params={"date": "2015-07-17"}).json()
        assert time.perf_counter() - t < 1.5
        assert not any(n["type"] == "element" for n in g["nodes"])
        assert not set(_keys(day)) & COST_KEYS


def test_has_3d_only_for_a_successful_reconstruction(client):
    import json

    from tagwerk.config import get_settings

    _post_note(client, "cap-3d-ok")
    _post_note(client, "cap-3d-fail")
    for cid, ok in (("cap-3d-ok", True), ("cap-3d-fail", False)):
        d = get_settings().cache_dir / cid
        d.mkdir(parents=True, exist_ok=True)
        (d / "sfm.json").write_text(json.dumps({"capture_id": cid, "ok": ok, "reason": None if ok else "zu wenig Bilder",
                                                "objects": []}), encoding="utf-8")
    recs = {r["capture_id"]: r["has_3d"] for r in client.get("/api/v2/day").json()["recordings"]}
    assert recs["cap-3d-ok"] is True and recs["cap-3d-fail"] is False


def test_one_german_state_mapping():
    from tagwerk import report, v2
    from tagwerk.labels import STATE_DE

    assert v2.STATE_DE is STATE_DE and report.STATE_DE is STATE_DE
    assert STATE_DE["checked"] == "abgenommen" and STATE_DE["tested"] == "geprüft"


def test_taskgraph_links_recordings_to_their_events_and_proposals(client):
    _post_note(client, "cap-raise")
    g = client.get("/api/v2/taskgraph").json()
    raised = {(e["src"], e["dst"]) for e in g["edges"] if e["type"] == "RAISED"}
    assert ("cap-raise", "cap-raise:absence:0") in raised
    g25 = client.get("/api/v2/taskgraph", params={"date": "2026-11-25"}).json()
    ev = next(n["id"] for n in g25["nodes"] if n["type"] == "event" and n["id"].startswith("hist-1125"))
    assert (ev.split(":")[0], ev) in {(e["src"], e["dst"]) for e in g25["edges"] if e["type"] == "RAISED"}
