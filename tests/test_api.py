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


def test_upload_kind_falls_back_to_extension():
    from starlette.datastructures import Headers, UploadFile

    from tagwerk.api.app import _kind

    up = UploadFile(file=None, filename="walk.mp4", headers=Headers({"content-type": "application/octet-stream"}))
    assert _kind(up) == "video"
    assert _kind(UploadFile(file=None, filename="x.jpg", headers=Headers({"content-type": "image/jpeg"}))) == "photo"


def test_path_traversal_ids_rejected(client, tmp_path):
    for bad in ("../x", "a/b", "..", "x" * 65, "a b"):
        r = client.post("/captures", data={"zone_id": "Z-STAGE", "capture_id": bad})
        assert r.status_code == 400, bad
        r = client.post("/captures", data={"zone_id": "Z-STAGE", "capture_id": "ok-1", "replay_of": bad})
        assert r.status_code == 400, bad
    assert not (tmp_path / "x").exists() and not (tmp_path / "data" / "captures" / "..").resolve().name == "x"


def test_graph_failure_does_not_fail_capture(client, monkeypatch):
    import tagwerk.pipeline.runner as runner

    def broken(*a, **k):
        raise RuntimeError("neo4j down")

    monkeypatch.setattr(runner, "sync_capture", broken)
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-g1", "note": "Reihe H Unterkonstruktion"})
    assert r.status_code == 200 and r.json()["changes"][0]["action"] == "confirmed"


def test_same_filenames_do_not_overwrite(client, tmp_path):
    files = [("files", ("image.jpg", b"\xff\xd8a", "image/jpeg")), ("files", ("image.jpg", b"\xff\xd8b", "image/jpeg"))]
    client.post("/captures", data={"zone_id": "Z-STAGE", "capture_id": "cap-f1"}, files=files)
    saved = sorted(p.name for p in (tmp_path / "data" / "captures" / "cap-f1").iterdir())
    assert saved == ["00_image.jpg", "01_image.jpg"]


def test_absence_only_capture_publishes_activity_update_and_graph_delay(client, monkeypatch):
    """An absence changes the forecast of its activity: /graph and the websocket must show it without a reload."""
    from tagwerk.pipeline import speech, vision  # no media: without the models the fixture stubs would add work
    monkeypatch.setattr(speech, "transcribe", lambda cap, derived: {"capture_id": cap["capture_id"], "lang": "de",
                                                                     "segments": []})
    monkeypatch.setattr(vision, "analyse", lambda cap, derived: {"capture_id": cap["capture_id"], "frames": []})
    with client.websocket_connect("/events") as ws:
        r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-abs",
                                           "note": "Zwei Mann vom Trockenbau sind krank."})
        assert r.json()["changes"] == []
        seen = []
        while True:
            ev = ws.receive_json()
            seen.append(ev)
            if ev["type"] == "status" and ev["id"] == "cap-abs" and ev["props"]["step"] == "done":
                break
    assert any(e["type"] == "update" and e["label"] == "Activity" and e["id"] == "A1080" for e in seen)
    node = next(n for n in client.get("/api/graph").json()["nodes"] if n["id"] == "A1080")
    fc = {a["id"]: a for a in client.get("/api/dashboard").json()["activities"]}
    assert node["props"]["delay_d"] == fc["A1080"]["delay_d"]


def _fake_cache(cid, text="", zone="Z-AUDIENCE", note=None):
    import json

    from tagwerk.config import get_settings

    d = get_settings().cache_dir / cid
    d.mkdir(parents=True, exist_ok=True)
    (d / "speech.json").write_text(json.dumps({"capture_id": cid, "lang": "de", "segments": (
        [{"start": 0, "end": 1, "text": text}] if text else [])}), encoding="utf-8")
    (d / "context.json").write_text(json.dumps({"capture_id": cid, "zone_id": zone}), encoding="utf-8")
    if note:
        (d / "structured.json").write_text(json.dumps({"capture_id": cid, "note": note}), encoding="utf-8")


def test_replays_hoersaal_curated_list_from_seed_skips_missing_cache(client):
    assert client.get("/api/replays").json() == []  # curated entry has no cache yet
    _fake_cache("cap-e2e-2", "Stuhlreihe A ist montiert")
    r = client.get("/api/replays").json()
    assert [e["id"] for e in r] == ["cap-e2e-2"] and r[0]["label"].startswith("Demo-Video") and r[0]["zone_id"] == "Z-AUDIENCE"
    assert client.get("/api/replayable").json() == ["cap-e2e-2"]  # unchanged contract: plain list of ids


def test_replays_curated_order_and_fallback_filter(client):
    from tagwerk.state import get_project

    for cid, text in [("a-first", "Erste Notiz"), ("b-second", "x" * 100), ("dt-x", "test"), ("replay-1", "r"),
                      ("scan-9", "s"), ("cap-ui-3", "u"), ("c-empty", "")]:
        _fake_cache(cid, text)
    meta = get_project().meta
    meta["demo_replays"] = [{"id": "b-second", "label": "Zweite"}, {"id": "ghost", "label": "fehlt"},
                            {"id": "a-first", "label": "Erste"}]
    assert [(e["id"], e["label"]) for e in client.get("/api/replays").json()] == [("b-second", "Zweite"),
                                                                                  ("a-first", "Erste")]
    meta.pop("demo_replays")
    r = client.get("/api/replays").json()
    assert [e["id"] for e in r] == ["a-first", "b-second", "c-empty"]  # dt-, replay-, scan-, cap-ui- are hidden
    labels = {e["id"]: e["label"] for e in r}
    assert labels["a-first"] == "Erste Notiz" and len(labels["b-second"]) <= 61 and labels["c-empty"] == "c-empty"


# ---------------------------------------------------------------- video view: kept media, /media fallback, timed replay

SEG_TEXT = "Stuhlreihe A ist montiert, zwei Mann vom Trockenbau sind heute krank, die hintere Traverse ist verkabelt"


def _cached_demo(cid="cap-vid", with_media=True):
    import json

    from tagwerk.config import get_settings

    d = get_settings().cache_dir / cid
    (d / "media").mkdir(parents=True, exist_ok=True)
    w = lambda n, o: (d / n).write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")  # noqa: E731
    w("speech.json", {"capture_id": cid, "lang": "de", "segments": [{"start": 0.0, "end": 6.6, "text": SEG_TEXT}]})
    w("vision.json", {"capture_id": cid, "frames": []})
    w("structured.json", {"capture_id": cid, "labour_present": [], "absences": [], "material_delivered": [], "unmatched": [],
                          "special_events": [], "work_done": [
                              {"element_ids": ["E-ROW-A"], "activity_id": None, "state_proposed": "installed",
                               "evidence": "voice", "quote": "Stuhlreihe A ist montiert", "t": 2.0}]})
    w("capture.json", {"capture_id": cid, "zone_id": "Z-AUDIENCE", "note": "typed words", "ts": "2026-11-26T09:00:00Z"})
    if with_media:
        (d / "media" / "demo.mp4").write_bytes(b"\x00\x00\x00 ftypmp42")
        (d / "media" / "a.jpg").write_bytes(b"\xff\xd8\xff")
    (get_settings().cache_dir / "secret.txt").write_text("nope", encoding="utf-8")
    return d


def test_media_served_from_cache_when_uploads_are_gone_and_traversal_blocked(client):
    _cached_demo()
    assert client.get("/media/cap-vid/demo.mp4").status_code == 200
    for bad in ("../secret.txt", "..%2fsecret.txt", "%2e%2e/%2e%2e/secret.txt", "../../secret.txt"):
        assert client.get(f"/media/cap-vid/{bad}").status_code == 404, bad
    assert client.get("/media/cap-vid/missing.mp4").status_code == 404
    assert client.get("/media/../secret.txt").status_code == 404 and client.get("/media/%2e%2e/secret.txt").status_code == 404


def test_replays_entry_has_video_photos_note_and_segments(client):
    from tagwerk.state import get_project

    get_project().meta["demo_replays"] = []  # fall back to "every cached capture"
    _cached_demo()
    e = next(x for x in client.get("/api/replays").json() if x["id"] == "cap-vid")
    assert e["video"] == "/media/cap-vid/demo.mp4" and e["photos"] == ["/media/cap-vid/a.jpg"]
    assert e["note"] == "typed words" and e["zone_id"] == "Z-AUDIENCE" and e["ts"] == "2026-11-26T09:00:00Z"
    assert e["segments"] == [{"start": 0.0, "end": 6.6, "text": SEG_TEXT}]
    _cached_demo("cap-novid", with_media=False)
    n = next(x for x in client.get("/api/replays").json() if x["id"] == "cap-novid")
    assert n["video"] is None and n["photos"] == []


def test_estimate_t_places_a_quote_inside_its_segment():
    from tagwerk.pipeline.runner import estimate_t

    tr = {"segments": [{"start": 0.0, "end": 6.6, "text": SEG_TEXT}]}
    assert estimate_t("Stuhlreihe A ist montiert", tr) == 0.0
    assert 3.5 < estimate_t("die hintere Traverse ist verkabelt", tr) < 4.5
    assert estimate_t("nicht gesagt", tr) == 0.0 and estimate_t("x", {"segments": []}) == 0.0


def test_sync_replay_publishes_each_change_at_its_time(client, monkeypatch):
    import tagwerk.pipeline.runner as runner

    _cached_demo()
    clock = {"t": 1000.0}
    monkeypatch.setattr(runner, "_clock", lambda: clock["t"])

    async def fake_sleep(s):
        clock["t"] += s

    monkeypatch.setattr(runner, "_sleep", fake_sleep)
    runner.REPLAY_PAUSE_S = 0
    stamps = []
    real = runner.broker.publish

    async def spy(ev):
        if ev.get("type") == "edge" and ev.get("label") == "CONFIRMED":
            stamps.append(clock["t"] - 1000.0)
        await real(ev)

    monkeypatch.setattr(runner.broker, "publish", spy)
    r = client.post("/captures", data={"capture_id": "cap-timed", "replay_of": "cap-vid", "sync": "1"})
    assert r.status_code == 200 and r.json()["status"] == "processed", r.text
    assert stamps and min(stamps) >= 2.0  # the work item says t=2.0 (video time == time since the POST)
    stamps.clear()
    clock["t"] = 1000.0
    r = client.post("/captures", data={"capture_id": "cap-plain", "replay_of": "cap-vid"})
    assert r.status_code == 200 and (not stamps or max(stamps) < 1.0)  # without sync nothing waits


def test_processed_capture_keeps_its_video_with_the_cache(client, monkeypatch):
    from tagwerk.config import get_settings
    from tagwerk.pipeline import speech, vision

    monkeypatch.setattr(speech, "transcribe", lambda cap, derived: {"capture_id": cap["capture_id"], "lang": "de",
                                                                     "segments": []})
    monkeypatch.setattr(vision, "analyse", lambda cap, derived: {"capture_id": cap["capture_id"], "frames": []})
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-keep", "note": "Kratzer an der Bühne"},
                    files=[("files", ("walk.mp4", b"\x00" * 64, "video/mp4")), ("files", ("a.jpg", b"\xff\xd8", "image/jpeg"))])
    assert r.status_code == 200, r.text
    kept = sorted(p.name for p in (get_settings().cache_dir / "cap-keep" / "media").iterdir())
    assert kept == ["a.jpg", "walk.mp4"]  # index prefixes stripped
    assert client.get("/media/cap-keep/walk.mp4").status_code == 200
    import json

    assert json.loads((get_settings().cache_dir / "cap-keep" / "capture.json").read_text())["note"] == "Kratzer an der Bühne"
