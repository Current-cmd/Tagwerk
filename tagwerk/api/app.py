"""Tagwerk API: uploads, processing, websocket events, graph snapshot, dashboard data, exports.

    uvicorn tagwerk.api.app:app --host 0.0.0.0 --port 8000
"""
import asyncio
import logging
import mimetypes
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel

from tagwerk.config import get_settings
from tagwerk.contracts import validate
from tagwerk.events import broker
from tagwerk.graph.store import get_store
from tagwerk.graph.sync import sync_capture, sync_seed
from tagwerk.pipeline.export import captures_to_ics, gaeb_xml, p6_xml
from tagwerk.pipeline.runner import run_capture
from tagwerk.state import get_project, save_result, today

log = logging.getLogger(__name__)
WEB = Path(__file__).resolve().parents[2] / "web"
_results: dict[str, dict] = {}
_lock = asyncio.Lock()  # one capture at a time: the GPU and the state are shared


def _sync_all() -> None:
    store, project = get_store(), get_project()
    with store.batch():
        sync_seed(store, project)
        for cid in project.captures:
            sync_capture(store, project, cid)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await asyncio.to_thread(_sync_all)
    except Exception as exc:  # the API must come up even if the graph write fails
        log.warning("initial graph sync failed: %s", exc)
    yield


app = FastAPI(title="Tagwerk", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "graph": type(get_store()).__name__, "gpu_worker": s.gpu_worker_url or "in-process",
            "replay_mode": s.replay_mode, "structuring": "claude" if s.anthropic_api_key else "rules",
            "data_date": today().isoformat(), "project": get_project().meta.get("name"),
            "elements": len(get_project().elements), "activities": len(get_project().activities)}


@app.get("/zones")
def zones() -> list[dict]:
    return [{"id": z["id"], "name": f"{z['name_de']} / {z['name_en']}"} for z in get_project().zones.values()]


def _kind(upload: UploadFile) -> str:
    ctype = upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or ""
    if ctype.startswith("video"):
        return "video"
    if ctype.startswith("audio"):
        return "audio"
    return "photo"


@app.post("/captures")
async def create_capture(
    zone_id: str = Form(...),
    lang: str = Form("auto"),
    note: str | None = Form(None),
    capture_id: str | None = Form(None),  # client resends the same id on retry
    ts: str | None = Form(None),  # optional server-time override (history/replay)
    replay_of: str | None = Form(None),  # re-run an earlier capture from its cached stage outputs
    files: list[UploadFile] = File(default=[]),
) -> dict:
    project = get_project()
    if replay_of:
        _prepare_replay(replay_of, capture_id or f"replay-{uuid.uuid4().hex[:8]}")
        capture_id = capture_id or _last_replay_id
    if zone_id not in project.zones:
        raise HTTPException(400, f"unknown zone {zone_id}")
    cid = capture_id or f"cap-{uuid.uuid4().hex[:10]}"
    if cid in project.captures:  # idempotent retry
        return {"capture_id": cid, "status": "exists"}
    folder = Path(get_settings().data_dir) / "captures" / cid
    folder.mkdir(parents=True, exist_ok=True)
    media = []
    for f in files:
        dest = folder / Path(f.filename or "upload.bin").name
        dest.write_bytes(await f.read())
        media.append({"type": _kind(f), "path": str(dest)})
    now = datetime.now(UTC).replace(microsecond=0)
    if ts is None:  # put live captures on the project's data date so they count as "today"
        ts = f"{today().isoformat()}T{now.strftime('%H:%M:%S')}Z"
    capture = {"capture_id": cid, "ts_server": ts, "gps": None, "zone_id": zone_id,
               "lang": lang if lang in ("de", "en", "auto") else "auto", "media": media,
               "note": (note or "").strip() or None}
    async with _lock:
        if cid in project.captures:
            return {"capture_id": cid, "status": "exists"}
        result = await run_capture(capture, replay=bool(replay_of))
    _results[cid] = result
    return {"capture_id": cid, "status": "processed",
            "transcript": " ".join(s["text"] for s in result["transcript"]["segments"]),
            "changes": [c for c in result["changes"] if c["action"] in ("confirmed", "proposed", "unchanged")],
            "absences": result["structured"]["absences"], "events": result["structured"]["special_events"]}


_last_replay_id = None


def _prepare_replay(src: str, dst: str) -> None:
    """Copy cache/<src>/ to cache/<dst>/ with capture_id rewritten, so <dst> replays <src> exactly."""
    import json
    import shutil

    global _last_replay_id
    s = get_settings()
    src_dir, dst_dir = Path(s.cache_dir) / src, Path(s.cache_dir) / dst
    if not (src_dir / "speech.json").exists() or not (src_dir / "vision.json").exists():
        raise HTTPException(404, f"no cached stage outputs for {src}")
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True)
    for f in src_dir.glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        data["capture_id"] = dst
        (dst_dir / f.name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    _last_replay_id = dst


@app.get("/api/replayable")
def replayable() -> list[str]:
    d = Path(get_settings().cache_dir)
    return sorted(p.name for p in d.iterdir() if (p / "speech.json").exists()) if d.exists() else []


@app.get("/captures/{capture_id}")
def get_capture(capture_id: str) -> dict:
    if capture_id in _results:
        return _results[capture_id]
    c = get_project().captures.get(capture_id)
    if not c:
        raise HTTPException(404)
    return c


@app.get("/media/{capture_id}/{name}")
def media(capture_id: str, name: str) -> FileResponse:
    base = (Path(get_settings().data_dir) / "captures").resolve()
    path = (base / capture_id / name).resolve()
    if base not in path.parents or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


class Confirm(BaseModel):
    state: str


@app.post("/api/elements/{element_id}/confirm")
async def confirm_element(element_id: str, body: Confirm) -> dict:
    """Manual tap in the site-manager view; counts like voice evidence."""
    project = get_project()
    el = project.elements.get(element_id)
    if not el:
        raise HTTPException(404)
    cid = f"manual-{uuid.uuid4().hex[:8]}"
    ts = f"{today().isoformat()}T{datetime.now(UTC).strftime('%H:%M:%S')}Z"
    structured = {"capture_id": cid, "labour_present": [], "absences": [], "material_delivered": [],
                  "work_done": [{"element_ids": [element_id], "activity_id": None, "state_proposed": body.state,
                                 "evidence": "voice", "quote": f"manual: {el['name_de']} {body.state}", "t": None}],
                  "special_events": [], "unmatched": []}
    validate("structured", structured)
    meta = {"capture_id": cid, "zone_id": el["zone"], "ts": ts, "note": "manual confirmation"}
    async with _lock:
        changes = project.apply_structured(meta, structured)
        if changes and changes[0]["action"] == "invalid":
            del project.captures[cid]
            raise HTTPException(400, f"{body.state!r} is not a state of {element_id}")
        save_result(meta, structured)
        await asyncio.to_thread(sync_capture, get_store(), project, cid)
    await broker.publish({"type": "update", "label": "Element", "id": element_id,
                          "props": {"state": el["state"], "pct": el["pct"], "via": "CONFIRMED", "name": el["name_de"]}})
    for aid in project.activities_of(element_id):
        await broker.publish({"type": "update", "label": "Activity", "id": aid,
                              "props": {"pct": project.activity_pct(aid), "name": project.activities[aid]["name"]}})
    return {"element_id": element_id, "action": changes[0]["action"], "pct": el["pct"], "state": el["state"]}


@app.get("/api/graph")
def graph_snapshot() -> dict:
    return get_store().snapshot()


@app.get("/api/dashboard")
def dashboard() -> dict:
    return validate("dashboard", get_project().dashboard(today()))


@app.get("/api/overview")
def overview() -> dict:
    return get_project().overview(today())


@app.get("/export/day.ics", response_class=PlainTextResponse)
def export_ics() -> PlainTextResponse:
    project = get_project()
    caps = [{"capture_id": cid, "ts_server": c["ts"], "zone_id": c["zone_id"],
             "summary": f"Baustellenaufnahme {project.zones[c['zone_id']]['name_de']}",
             "description": "; ".join(c["quotes"]) or (c.get("note") or "")}
            for cid, c in sorted(project.captures.items(), key=lambda kv: kv[1]["ts"])]
    return PlainTextResponse(captures_to_ics(caps, daily_reports=sorted({c["date"] for c in project.captures.values()})),
                             media_type="text/calendar",
                             headers={"Content-Disposition": "attachment; filename=tagwerk.ics"})


@app.get("/export/p6.xml")
def export_p6() -> Response:
    return Response(p6_xml(get_project(), today(), progress=True), media_type="application/xml",
                    headers={"Content-Disposition": "attachment; filename=hoersaal_progress_p6.xml"})


@app.get("/export/p6-baseline.xml")
def export_p6_baseline() -> Response:
    return Response(p6_xml(get_project(), progress=False), media_type="application/xml",
                    headers={"Content-Disposition": "attachment; filename=hoersaal_baseline_p6.xml"})


@app.get("/export/boq.{phase}")
def export_gaeb(phase: str) -> Response:
    if phase not in ("x83", "x84"):
        raise HTTPException(404)
    return Response(gaeb_xml(get_project(), int(phase[1:])), media_type="application/xml",
                    headers={"Content-Disposition": f"attachment; filename=hoersaal.{phase}"})


@app.websocket("/events")
async def events(ws: WebSocket) -> None:
    await broker.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        broker.disconnect(ws)


def _page(name: str) -> FileResponse:
    return FileResponse(WEB / name / "index.html")


@app.get("/")
def index() -> FileResponse:
    return _page("dashboard")


@app.get("/upload")
def upload_page() -> FileResponse:
    return _page("upload")


@app.get("/graph")
def graph_page() -> FileResponse:
    return _page("graph")


@app.get("/dashboard")
def dashboard_page() -> FileResponse:
    return _page("dashboard")


@app.get("/site")
def site_page() -> FileResponse:
    return _page("site")
