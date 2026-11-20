"""Tagwerk API: uploads, processing, websocket events, graph snapshot, dashboard data, .ics export.

    uvicorn tagwerk.api.app:app --reload --port 8000
"""
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse

from tagwerk.config import get_settings
from tagwerk.contracts import fixture
from tagwerk.events import broker
from tagwerk.graph.store import get_store
from tagwerk.pipeline.export import captures_to_ics
from tagwerk.pipeline.runner import run_capture

WEB = Path(__file__).resolve().parents[2] / "web"
app = FastAPI(title="Tagwerk")
_captures: dict[str, dict] = {}

# Placeholder zones until seed/ is loaded into the graph (TODO(feat/seed): read Zone nodes).
ZONES = [
    {"id": "Z-STAGE", "name": "Bühne / Stage"},
    {"id": "Z-AUDIENCE", "name": "Zuschauerraum / Audience"},
    {"id": "Z-TECH", "name": "Technik / Tech booth"},
    {"id": "Z-ENTRANCE", "name": "Eingang / Entrance"},
]


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "graph": type(get_store()).__name__, "gpu_worker": s.gpu_worker_url or "in-process",
            "replay_mode": s.replay_mode}


@app.get("/zones")
def zones() -> list[dict]:
    return ZONES


@app.post("/captures")
async def create_capture(
    zone_id: str = Form(...),
    lang: str = Form("auto"),
    note: str | None = Form(None),
    capture_id: str | None = Form(None),  # client may resend the same id on retry
    files: list[UploadFile] = File(default=[]),
) -> dict:
    if zone_id not in {z["id"] for z in ZONES}:
        raise HTTPException(400, f"unknown zone {zone_id}")
    cid = capture_id or f"cap-{uuid.uuid4().hex[:10]}"
    if cid in _captures:  # idempotent retry
        return {"capture_id": cid, "status": "exists"}
    folder = Path(get_settings().data_dir) / "captures" / cid
    folder.mkdir(parents=True, exist_ok=True)
    media = []
    for f in files:
        dest = folder / Path(f.filename or "upload.bin").name
        dest.write_bytes(await f.read())
        ctype = f.content_type or ""
        kind = "video" if ctype.startswith("video") else "audio" if ctype.startswith("audio") else "photo"
        media.append({"type": kind, "path": str(dest)})
    capture = {
        "capture_id": cid,
        "ts_device": None,
        "ts_server": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "gps": None,
        "zone_id": zone_id,
        "lang": lang if lang in ("de", "en", "auto") else "auto",
        "media": media,
        "note": note,
    }
    capture.pop("ts_device")  # optional field; set from EXIF/metadata later
    result = await run_capture(capture)
    _captures[cid] = result
    return {"capture_id": cid, "status": "processed", "work_done": result["structured"]["work_done"]}


@app.get("/captures/{capture_id}")
def get_capture(capture_id: str) -> dict:
    if capture_id not in _captures:
        raise HTTPException(404)
    return _captures[capture_id]


@app.get("/api/graph")
def graph_snapshot() -> dict:
    return get_store().snapshot()


@app.get("/api/dashboard")
def dashboard() -> dict:
    # TODO(feat/loop): compute from the graph (roll-up, EV, forecast). Fixture until then.
    return fixture("dashboard")


@app.get("/export/day.ics", response_class=PlainTextResponse)
def export_ics() -> PlainTextResponse:
    caps = [{"capture_id": cid, "ts_server": r["capture"]["ts_server"], "zone_id": r["capture"]["zone_id"],
             "description": "; ".join(w["quote"] for w in r["structured"]["work_done"])}
            for cid, r in _captures.items()]
    return PlainTextResponse(captures_to_ics(caps), media_type="text/calendar")


@app.websocket("/events")
async def events(ws: WebSocket) -> None:
    await broker.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        broker.disconnect(ws)


@app.get("/upload")
def upload_page() -> FileResponse:
    return FileResponse(WEB / "upload" / "index.html")


@app.get("/graph")
def graph_page() -> FileResponse:
    return FileResponse(WEB / "graph" / "index.html")


@app.get("/dashboard")
def dashboard_page() -> FileResponse:
    return FileResponse(WEB / "dashboard" / "index.html")
