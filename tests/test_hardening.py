"""Phase 0 hardening: auth, upload limits, timestamp validation and all-or-nothing state changes."""
import copy

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

TOKEN = "s3cret-token"


@pytest.fixture()
def secured(client, monkeypatch):
    """The same app with API_TOKEN set and dev mode off."""
    from tagwerk.config import get_settings

    monkeypatch.setenv("API_TOKEN", TOKEN)
    monkeypatch.setenv("TAGWERK_DEV", "0")
    get_settings.cache_clear()
    yield client
    get_settings.cache_clear()


AUTH = {"Authorization": f"Bearer {TOKEN}"}


# ----- R1: authentication -----

def test_api_requires_token(secured):
    assert secured.get("/api/dashboard").status_code == 401
    assert secured.get("/api/dashboard", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert secured.get("/api/dashboard", headers=AUTH).status_code == 200


def test_token_also_accepted_as_cookie_and_query(secured):
    assert secured.get(f"/api/graph?token={TOKEN}").status_code == 200
    secured.cookies.set("tagwerk_token", TOKEN)
    try:
        assert secured.get("/api/graph").status_code == 200
    finally:
        secured.cookies.clear()


def test_health_and_pages_stay_open(secured):
    assert secured.get("/health").status_code == 200
    for page in ("/", "/upload", "/graph", "/dashboard", "/scan", "/site", "/auth.js"):
        assert secured.get(page).status_code == 200, page


def test_upload_requires_token(secured):
    r = secured.post("/captures", data={"zone_id": "Z-AUDIENCE", "note": "Stuhlreihe A ist montiert."})
    assert r.status_code == 401


def test_websocket_requires_token(secured):
    with pytest.raises(WebSocketDisconnect):
        with secured.websocket_connect("/events") as ws:
            ws.receive_json()
    with secured.websocket_connect(f"/events?token={TOKEN}") as ws:
        assert ws.receive_json()  # history replays first


def test_refuses_to_start_without_token(tmp_path, monkeypatch):
    from tagwerk.api.app import app
    from tagwerk.config import get_settings

    monkeypatch.setenv("API_TOKEN", "")
    monkeypatch.setenv("TAGWERK_DEV", "0")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="API_TOKEN"):
            with TestClient(app):
                pass
    finally:
        get_settings.cache_clear()


def test_make_project_needs_flag(client, monkeypatch):
    r = client.post("/api/scan", data={"make_project": "neu"}, files={"files": ("a.jpg", b"\x00" * 10, "image/jpeg")})
    assert r.status_code == 403


# ----- R2: upload limits -----

def test_oversized_upload_is_rejected_without_leftovers(client, monkeypatch, tmp_path):
    from tagwerk.config import get_settings

    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-big", "note": "x"},
                    files={"files": ("big.mp4", b"\x00" * (2 * 1024 * 1024), "video/mp4")})
    assert r.status_code == 413
    folder = get_settings().data_dir / "captures" / "cap-big"
    assert not folder.exists() or not any(folder.iterdir())
    assert client.get("/captures/cap-big").status_code == 404


def test_total_upload_size_is_capped(client, monkeypatch):
    from tagwerk.config import get_settings

    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    part = b"\x00" * (600 * 1024)  # each under the cap, together over it
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-two", "note": "x"},
                    files=[("files", ("a.jpg", part, "image/jpeg")), ("files", ("b.jpg", part, "image/jpeg"))])
    assert r.status_code == 413


def test_too_many_files_rejected(client, monkeypatch):
    from tagwerk.config import get_settings

    monkeypatch.setenv("MAX_UPLOAD_FILES", "2")
    get_settings.cache_clear()
    files = [("files", (f"{i}.jpg", b"\x00", "image/jpeg")) for i in range(3)]
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "note": "x"}, files=files)
    assert r.status_code == 413


def test_scan_same_name_files_do_not_overwrite(client, monkeypatch):
    seen = {}

    async def fake_stage(stage, capture, derived=None, *a, **k):
        seen["media"] = [m["path"] for m in capture["media"]]
        from tagwerk.contracts import fixture
        return {**fixture(stage if stage == "vision" else "transcript"), "capture_id": capture["capture_id"]}

    monkeypatch.setattr("tagwerk.pipeline.runner._gpu_stage", fake_stage)
    monkeypatch.setattr("tagwerk.pipeline.normalize.normalize", lambda capture, out: {})
    files = [("files", ("image.jpg", b"\x01", "image/jpeg")), ("files", ("image.jpg", b"\x02", "image/jpeg"))]
    r = client.post("/api/scan", files=files)
    assert r.status_code == 200, r.text
    assert len(set(seen["media"])) == 2
    assert [open(p, "rb").read() for p in seen["media"]] == [b"\x01", b"\x02"]


# ----- A: timestamps -----

def test_garbage_ts_is_rejected_and_state_unchanged(client):
    from tagwerk.state import get_project

    before = get_project().elements["E-ROW-A"]["pct"]
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-badts", "ts": "garbage",
                                       "note": "Stuhlreihe A ist montiert."})
    assert r.status_code == 400
    assert get_project().elements["E-ROW-A"]["pct"] == before
    assert "cap-badts" not in get_project().captures


def test_ts_without_timezone_is_rejected(client):
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "ts": "2026-11-26T10:00:00", "note": "x"})
    assert r.status_code == 400


def test_capture_contract_checks_date_time_format():
    from tagwerk.contracts import ContractError, fixture, validate

    cap = {**fixture("capture"), "ts_server": "x"}
    with pytest.raises(ContractError):
        validate("capture", cap)


def _snapshot(p):
    return copy.deepcopy((p.elements, p.activities, p.labour, p.events, p.materials, p.proposals, p.history_log,
                          sorted(p.captures)))


def test_apply_structured_is_all_or_nothing(client):
    from tagwerk.state import get_project

    p = get_project()
    before = _snapshot(p)
    structured = {"capture_id": "cap-atomic", "material_delivered": [], "special_events": [], "unmatched": [],
                  "labour_present": [{"trade": "Trockenbau", "count": 3}],
                  "work_done": [{"element_ids": ["E-ROW-A"], "activity_id": None, "state_proposed": "installed",
                                 "evidence": "voice", "quote": "Reihe A montiert", "t": None}],
                  "absences": [{"trade": "Trockenbau", "count": 2, "reason": "krank"}]}
    with pytest.raises(ValueError):
        p.apply_structured({"capture_id": "cap-atomic", "zone_id": "Z-AUDIENCE", "ts": "garbage"}, structured)
    assert _snapshot(p) == before


def test_state_rolls_back_when_saving_fails(client, monkeypatch):
    from tagwerk.pipeline import runner
    from tagwerk.state import get_project

    p = get_project()
    before = _snapshot(p)

    def boom(meta, structured):
        raise OSError("disk full")

    monkeypatch.setattr(runner, "save_result", boom)
    with pytest.raises(OSError):
        client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-disk",
                                       "note": "Stuhlreihe A ist montiert."})
    assert _snapshot(p) == before


def test_v2_api_needs_token_but_app_shell_is_open(secured):
    assert secured.get("/app").status_code == 200
    assert secured.get("/api/v2/days").status_code == 401
    assert secured.get("/api/v2/days", headers=AUTH).status_code == 200
