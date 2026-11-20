import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEO4J_URI", "")
    monkeypatch.setenv("GPU_WORKER_URL", "")
    import tagwerk.graph.store as store
    from tagwerk.config import get_settings

    get_settings.cache_clear()
    store._store = None
    from tagwerk.api.app import _captures, app

    _captures.clear()
    return TestClient(app)


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["graph"] == "MemoryStore"


def test_upload_runs_pipeline_and_updates_graph(client):
    with client.websocket_connect("/events") as ws:
        r = client.post("/captures", data={"zone_id": "Z-STAGE", "lang": "de", "capture_id": "cap-t1"},
                        files={"files": ("walk.mp4", b"\x00" * 10, "video/mp4")})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "processed"
        first = ws.receive_json()
        assert first == {"type": "node", "label": "Capture", "id": "cap-t1", "props": {"zone_id": "Z-STAGE"}}
    graph = client.get("/api/graph").json()
    ids = {n["id"] for n in graph["nodes"]}
    assert {"cap-t1", "Z-STAGE", "E-ROW-A"} <= ids
    assert any(e["rel"] == "CONFIRMED" for e in graph["edges"])


def test_retry_is_idempotent(client):
    data = {"zone_id": "Z-STAGE", "capture_id": "cap-t2"}
    client.post("/captures", data=data)
    assert client.post("/captures", data=data).json()["status"] == "exists"


def test_unknown_zone_rejected(client):
    assert client.post("/captures", data={"zone_id": "nowhere"}).status_code == 400


def test_ics_export(client):
    client.post("/captures", data={"zone_id": "Z-STAGE", "capture_id": "cap-t3"})
    assert "UID:capture-cap-t3@tagwerk" in client.get("/export/day.ics").text


def test_pages_served(client):
    for page in ("/upload", "/graph", "/dashboard"):
        assert client.get(page).status_code == 200
