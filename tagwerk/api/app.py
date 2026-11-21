"""Tagwerk API: uploads, processing, websocket events, graph snapshot, dashboard data, exports.

    uvicorn tagwerk.api.app:app --host 0.0.0.0 --port 8080
"""
import asyncio
import logging
import mimetypes
import re
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from pydantic import BaseModel

from tagwerk import bim, report, v2
from tagwerk.config import get_settings
from tagwerk.contracts import validate
from tagwerk.events import broker
from tagwerk.graph.store import get_store
from tagwerk.graph.sync import sync_capture, sync_seed
from tagwerk.pipeline import runner
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
app.add_middleware(GZipMiddleware, minimum_size=2000)  # /api/overview and /api/graph are large for big projects


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
    ctype = upload.content_type or ""
    if not ctype.startswith(("video", "audio", "image")):  # e.g. application/octet-stream: trust the extension
        ctype = mimetypes.guess_type(upload.filename or "")[0] or ""
    if ctype.startswith("video"):
        return "video"
    if ctype.startswith("audio"):
        return "audio"
    return "photo"


@app.post("/captures")
async def create_capture(
    zone_id: str | None = Form(None),  # required, except for replays (taken from the source capture)
    lang: str = Form("auto"),
    note: str | None = Form(None),
    capture_id: str | None = Form(None),  # client resends the same id on retry
    ts: str | None = Form(None),  # optional server-time override (history/replay)
    replay_of: str | None = Form(None),  # re-run an earlier capture from its cached stage outputs
    sync: str | None = Form(None),  # replays only: publish each change at its second of the video (clock starts now)
    files: list[UploadFile] = File(default=[]),
) -> dict:
    project = get_project()
    sync_t0 = runner._clock() if (replay_of and (sync or "").lower() in ("1", "true", "yes")) else None
    _check_id(capture_id, "capture_id")
    _check_id(replay_of, "replay_of")
    if replay_of and zone_id is None:
        zone_id = _cached_zone(replay_of)
    if zone_id not in project.zones:
        raise HTTPException(400, f"unknown zone {zone_id}")
    cid = capture_id or (f"replay-{uuid.uuid4().hex[:8]}" if replay_of else f"cap-{uuid.uuid4().hex[:10]}")
    if cid in project.captures:  # idempotent retry
        return {"capture_id": cid, "status": "exists"}
    if replay_of:
        _prepare_replay(replay_of, cid)
    folder = Path(get_settings().data_dir) / "captures" / cid
    folder.mkdir(parents=True, exist_ok=True)
    media = []
    for i, f in enumerate(files):  # index prefix: phones name every photo image.jpg
        dest = folder / f"{i:02d}_{Path(f.filename or 'upload.bin').name}"
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
        result = await run_capture(capture, replay=bool(replay_of), sync_t0=sync_t0)
    _results[cid] = result
    return {"capture_id": cid, "status": "processed",
            "transcript": " ".join(s["text"] for s in result["transcript"]["segments"]),
            "changes": [c for c in result["changes"] if c["action"] in ("confirmed", "proposed", "unchanged")],
            "absences": result["structured"]["absences"], "events": result["structured"]["special_events"],
            "material": result["structured"]["material_delivered"], "labour": result["structured"]["labour_present"]}


ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _check_id(value: str | None, field: str) -> None:
    """Ids become folder names: allow only [A-Za-z0-9_-] (no path traversal)."""
    if value is not None and not ID_RE.match(value):
        raise HTTPException(400, f"invalid {field}: use 1-64 characters A-Z a-z 0-9 _ -")


def _cached_zone(src: str) -> str | None:
    import json

    for name in ("context.json", "capture.json"):
        p = Path(get_settings().cache_dir) / src / name
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8")).get("zone_id")
    return None


def _prepare_replay(src: str, dst: str) -> None:
    """Copy cache/<src>/ to cache/<dst>/ with capture_id rewritten, so <dst> replays <src> exactly."""
    import json
    import shutil

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
    if (src_dir / "media").is_dir():  # the kept video/photos, so the replay shows as a video with its frames
        shutil.copytree(src_dir / "media", dst_dir / "media")


@app.post("/api/scan")
async def scan_video(files: list[UploadFile] = File(...), make_project: str | None = Form(None),
                     zone_name: str = Form("Baustelle")) -> dict:
    """Run the vision stage on an uploaded video/photos and categorise what was seen. With make_project=<name>
    also write seed/projects/<name>/ (start the API with PROJECT=<name> to work on it)."""
    import re

    from tagwerk.pipeline.runner import _gpu_stage
    from tagwerk.pipeline.scan import inventory, seed_from_scan
    from tagwerk.project import SEED_DIR

    sid = f"scan-{uuid.uuid4().hex[:8]}"
    name = out = None
    if make_project:  # check the name before the (slow) vision pass
        slug = make_project.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        name = re.sub(r"[^a-z0-9_-]", "", re.sub(r"\s+", "-", slug.strip()))[:40] or sid
        out = SEED_DIR / "projects" / name
        if name in ("hoersaal", "schependomlaan") or (out / "history.json").exists():  # never clobber real projects
            raise HTTPException(409, f"project {name} exists; choose another name")
    folder = Path(get_settings().data_dir) / "captures" / sid
    folder.mkdir(parents=True, exist_ok=True)
    media = []
    for f in files:
        dest = folder / Path(f.filename or "upload.bin").name
        dest.write_bytes(await f.read())
        media.append({"type": _kind(f), "path": str(dest)})
    capture = {"capture_id": sid, "ts_server": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "gps": None,
               "zone_id": next(iter(get_project().zones)), "lang": "auto", "media": media, "note": None}
    from tagwerk.pipeline import normalize

    # frames locally too (same 1 fps numbering as the worker), so the page can show where each label was seen
    derived = await asyncio.to_thread(normalize.normalize, capture, folder / "derived")
    async with _lock:
        stage_derived = None if get_settings().gpu_worker_url else derived
        vis = validate("vision", await _gpu_stage("vision", capture, stage_derived))
        tr = validate("transcript", await _gpu_stage("speech", capture, stage_derived))
    inv = inventory(vis, transcript=tr)
    inv["scan_id"] = sid
    for item in inv["items"]:
        best = item.get("best") or {}
        name = Path(best.get("media_path") or "").name
        if name and (folder / "derived" / "frames" / name).exists():
            item["thumb"] = f"/media/{sid}/derived/frames/{name}"
    sf = await runner.sfm_stage(capture, get_project())  # 3D reconstruction of the same clip (<= 150 s, never raises)
    if sf is not None:
        inv["scan3d"] = {"ok": sf["ok"], "reason": sf["reason"], "frames_registered": sf["frames_registered"],
                         "objects": len(sf["objects"]), "url": f"/api/v2/scan3d/{sid}"}
    if make_project and not inv["element_count"]:  # a project without elements has no activities: dashboard/P6 break
        inv["project_error"] = "Keine Bauteile erkannt: Projekt nicht angelegt. Näher heran, mehr Licht, nochmal scannen."
    elif make_project:
        inv["project"] = seed_from_scan(inv, out, name, today(), zone_name)
    return inv


@app.get("/api/replayable")
def replayable() -> list[str]:
    d = Path(get_settings().cache_dir)
    return sorted(p.name for p in d.iterdir() if (p / "speech.json").exists()) if d.exists() else []


HIDDEN_REPLAY_PREFIXES = ("replay-", "dt-", "scan-", "cap-ui-")


def _replay_entry(cid: str, label: str | None = None) -> dict:
    """Picker entry from the cached stage outputs (best effort, nothing is required but speech.json): label, zone, time,
    the kept video/photos (`/media/<id>/<file>`), the typed note and the speech segments for live captions."""
    import json

    d = Path(get_settings().cache_dir) / cid

    def load(name: str) -> dict:
        try:
            return json.loads((d / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    ctx, structured, speech, cap = load("context.json"), load("structured.json"), load("speech.json"), load("capture.json")
    segments = [{"start": g["start"], "end": g["end"], "text": g["text"]} for g in speech.get("segments", [])]
    note = (cap.get("note") or ctx.get("note") or structured.get("note") or "").strip() or None
    if not label:
        text = " ".join(g["text"] for g in segments).strip() or note or ""
        label = (text[:60].rstrip() + ("…" if len(text) > 60 else "")) if text else cid
    files = sorted(p.name for p in (d / "media").iterdir() if p.is_file()) if (d / "media").is_dir() else []
    video = next((f for f in files if f.lower().endswith((".mp4", ".mov", ".webm", ".m4v"))), None)
    photos = [f"/media/{cid}/{f}" for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    return {"id": cid, "label": label, "zone_id": cap.get("zone_id") or ctx.get("zone_id"),
            "ts": cap.get("ts") or ctx.get("ts") or structured.get("ts"), "video": f"/media/{cid}/{video}" if video else None,
            "photos": photos, "note": note, "segments": segments}


@app.get("/api/replays")
def replays() -> list[dict]:
    """Replay picker for /graph: the project's curated `demo_replays` (project.json) that have a cache, else every
    cached capture except test/scan/replay runs."""
    d = Path(get_settings().cache_dir)
    cached = {p.name for p in d.iterdir() if (p / "speech.json").exists()} if d.exists() else set()
    curated = get_project().meta.get("demo_replays")
    if curated:
        return [_replay_entry(e["id"], e.get("label")) for e in curated if e.get("id") in cached]
    return [_replay_entry(cid) for cid in sorted(cached) if not cid.startswith(HIDDEN_REPLAY_PREFIXES)]


@app.get("/captures/{capture_id}")
def get_capture(capture_id: str) -> dict:
    if capture_id in _results:
        return _results[capture_id]
    c = get_project().captures.get(capture_id)
    if not c:
        raise HTTPException(404)
    return c


@app.get("/media/{capture_id}/{name:path}")
def media(capture_id: str, name: str) -> FileResponse:
    """Uploads of a capture (data/captures/<id>/) or, once those are gone, the copy kept with its cache
    (cache/<id>/media/). Both are confined to their folder."""
    s = get_settings()
    if not ID_RE.match(capture_id):  # ".." as the id would move the base itself
        raise HTTPException(404)
    for root in (Path(s.data_dir) / "captures" / capture_id, Path(s.cache_dir) / capture_id / "media"):
        base = root.resolve()
        path = (base / name).resolve()
        if base in path.parents and path.is_file():
            return FileResponse(path)
    raise HTTPException(404)


class Confirm(BaseModel):
    state: str


@app.post("/api/elements/{element_id}/confirm")
async def confirm_element(element_id: str, body: Confirm) -> dict:
    """Manual tap in the site-manager view; counts like voice evidence."""
    project = get_project()
    _check_id(element_id, "element_id")
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


def _v2_date(value: str | None):
    try:
        return v2.parse_date(value)
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD") from None


@app.get("/api/v2/days")
def v2_days() -> dict:
    return v2.days()


@app.get("/api/v2/day")
def v2_day(date: str | None = None) -> dict:
    return v2.day(_v2_date(date))


@app.get("/api/v2/taskgraph")
def v2_taskgraph(date: str | None = None) -> dict:
    return v2.taskgraph(_v2_date(date))


@app.get("/api/v2/report")
def v2_report(date: str | None = None) -> dict:
    """Tagesbericht / Bautagebuch of the day (default: the project's today)."""
    return report.report(_v2_date(date))


@app.get("/export/report.html", response_class=HTMLResponse)
def export_report(date: str | None = None) -> HTMLResponse:
    """Print-ready German A4 Bautagebuch page (print to PDF in the browser)."""
    return HTMLResponse(report.report_html(_v2_date(date)))


@app.get("/api/v2/bim")
def v2_bim(date: str | None = None) -> dict:
    """Element states as of the day keyed by IFC GlobalId, for the BIM viewer (available: false without a model)."""
    return bim.states(_v2_date(date))


@app.get("/api/v2/bim/model.{ext}")
def v2_bim_model(ext: str) -> FileResponse:
    """The tessellated IFC model (scripts/ifc_to_bim.py): model.json (element index) and model.bin (geometry)."""
    f = bim.model_file(f"bim.{ext}") if ext in ("json", "bin") else None
    if f is None:
        raise HTTPException(404, "no BIM model for this project")
    return FileResponse(f, media_type="application/json" if ext == "json" else "application/octet-stream",
                        headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/v2/scan3d/{capture_id}")
def v2_scan3d(capture_id: str) -> dict:
    """cache/<id>/sfm.json (Scan 3D); 404 when the capture has none."""
    import json

    _check_id(capture_id, "capture_id")
    from tagwerk.pipeline.sfm import drop_person_pairs

    try:
        data = json.loads((Path(get_settings().cache_dir) / capture_id / "sfm.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(404, "no scan3d for this capture") from None
    drop_person_pairs(data.get("objects") or [])
    return data


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


def _slug() -> str:
    return get_settings().project or "hoersaal"


@app.get("/export/p6.xml")
def export_p6() -> Response:
    return Response(p6_xml(get_project(), today(), progress=True), media_type="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={_slug()}_progress_p6.xml"})


@app.get("/export/p6-baseline.xml")
def export_p6_baseline() -> Response:
    return Response(p6_xml(get_project(), progress=False), media_type="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={_slug()}_baseline_p6.xml"})


@app.get("/export/boq.{phase}")
def export_gaeb(phase: str) -> Response:
    if phase not in ("x83", "x84"):
        raise HTTPException(404)
    return Response(gaeb_xml(get_project(), int(phase[1:])), media_type="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={_slug()}.{phase}"})


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


VENDOR = {"echarts.min.js", "vis-network.min.js"}  # bundled so the pages work without internet at the venue


@app.get("/vendor/{name}")
def vendor(name: str) -> FileResponse:
    if name not in VENDOR:
        raise HTTPException(404)
    return FileResponse(WEB / "vendor" / name, media_type="text/javascript",
                        headers={"Cache-Control": "public, max-age=86400"})


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


@app.get("/scan")
def scan_page() -> FileResponse:
    return _page("scan")


@app.get("/site")
def site_page() -> FileResponse:
    return _page("site")


APP_PLACEHOLDER = "<!doctype html><meta charset=utf-8><title>Tagwerk</title><p>UI v2 not built (web/app/index.html missing).</p>"


def _spa_index() -> Response:
    index = WEB / "app" / "index.html"
    return FileResponse(index) if index.is_file() else HTMLResponse(APP_PLACEHOLDER)


@app.get("/app")
def spa() -> Response:
    return _spa_index()


@app.get("/app/{path:path}")
def spa_path(path: str) -> Response:
    """Built files of the React app (confined to web/app/); anything else is a client route: index.html."""
    base = (WEB / "app").resolve()
    target = (base / path).resolve()
    if path and base in target.parents and target.is_file():
        return FileResponse(target)
    return _spa_index()
