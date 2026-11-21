import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("NEO4J_URI", "")
    monkeypatch.setenv("GPU_WORKER_URL", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("REPLAY_MODE", "false")
    import tagwerk.graph.store as store
    import tagwerk.pipeline.context as context
    import tagwerk.state as state
    from tagwerk.config import get_settings

    get_settings.cache_clear()
    store._store = None
    state.reset()
    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": 5.0, "precipMm": 0.0, "windKmh": 8.0,
                                                              "source": "test"})
    from tagwerk.api.app import _results, app

    _results.clear()
    with TestClient(app) as c:
        yield c


NOTE = "Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind heute krank."


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["graph"] == "MemoryStore" and body["structuring"] == "rules"


def test_seed_graph_is_loaded(client):
    ids = {n["id"] for n in client.get("/api/graph").json()["nodes"]}
    assert {"E-ROW-A", "A1080", "01.06.0010", "Z-AUDIENCE", "hist-1125-a"} <= ids


def test_upload_note_confirms_row_and_absence_moves_forecast(client):
    before = {a["id"]: a for a in client.get("/api/dashboard").json()["activities"]}
    with client.websocket_connect("/events") as ws:
        r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "lang": "de", "capture_id": "cap-t1",
                                           "note": NOTE},
                        files={"files": ("walk.jpg", b"\x00" * 10, "image/jpeg")})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "processed"
        seen = []
        while True:  # history replays first; read until our capture is done
            ev = ws.receive_json()
            seen.append(ev)
            if ev == {"type": "status", "label": "Capture", "id": "cap-t1", "props": {"step": "done"}}:
                break
    assert {"type": "node", "label": "Capture", "id": "cap-t1"} in [{k: e[k] for k in ("type", "label", "id")}
                                                                    for e in seen]
    assert any(c["element_id"] == "E-ROW-A" and c["action"] == "confirmed" and c["state"] == "installed"
               for c in body["changes"])
    assert body["absences"] == [{"trade": "Trockenbau", "count": 2, "reason": "krank"}]
    after = {a["id"]: a for a in client.get("/api/dashboard").json()["activities"]}
    assert after["A1080"]["pct"] > before["A1080"]["pct"]
    assert after["A1080"]["forecast_finish"] > before["A1080"]["forecast_finish"]
    edges = client.get("/api/graph").json()["edges"]
    assert any(e["src"] == "cap-t1" and e["rel"] == "CONFIRMED" and e["dst"] == "E-ROW-A" for e in edges)


def test_retry_is_idempotent(client):
    data = {"zone_id": "Z-STAGE", "capture_id": "cap-t2", "note": "Leinwand angeschlossen"}
    assert client.post("/captures", data=data).json()["status"] == "processed"
    assert client.post("/captures", data=data).json()["status"] == "exists"


def test_unknown_zone_rejected(client):
    assert client.post("/captures", data={"zone_id": "nowhere"}).status_code == 400


def test_manual_confirm(client):
    r = client.post("/api/elements/E-ROW-H/confirm", json={"state": "substructure"})
    assert r.status_code == 200 and r.json()["pct"] == 50
    assert client.post("/api/elements/E-ROW-H/confirm", json={"state": "nonsense"}).status_code == 400


def test_exports(client):
    client.post("/captures", data={"zone_id": "Z-STAGE", "capture_id": "cap-t3", "note": "Beamer angeschlossen"})
    ics = client.get("/export/day.ics").text
    assert "UID:capture-cap-t3@tagwerk" in ics and "UID:report-2026-11-26@tagwerk" in ics
    p6 = client.get("/export/p6.xml").text
    assert "<PhysicalPercentComplete>" in p6 and "<Id>A1080</Id>" in p6 and "<DataDate>2026-11-26" in p6
    assert "<Item RNoPart=\"0010\">" in client.get("/export/boq.x84").text


def test_overview_and_pages(client):
    ov = client.get("/api/overview").json()
    assert ov["kpi"]["bac_eur"] > 0 and ov["zones"] and ov["curve"]
    for page in ("/", "/upload", "/graph", "/dashboard", "/site", "/scan"):
        assert client.get(page).status_code == 200, page


def test_replay_of_cached_capture(client):
    client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-src", "note": "Reihe H Unterkonstruktion"})
    assert "cap-src" in client.get("/api/replayable").json()
    import tagwerk.pipeline.runner as runner

    runner.REPLAY_PAUSE_S = 0
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-rep", "replay_of": "cap-src"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "processed"
    assert client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "x", "replay_of": "nope"}).status_code == 404
