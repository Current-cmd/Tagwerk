"""Runs one capture through every stage, validates each output, updates the project state,
writes the graph and emits websocket events so the live graph grows while it runs.

Speech and vision run on the GPU worker when GPU_WORKER_URL is set, otherwise in-process.
Every stage output is cached in cache/<capture_id>/; with REPLAY_MODE=true cached outputs are used
(no GPU, no Claude) and steps are paced so the graph still animates.
"""
import asyncio
import json
import logging
import re
import shutil
import time
from pathlib import Path

import httpx

from tagwerk.config import get_settings
from tagwerk.contracts import validate
from tagwerk.events import broker
from tagwerk.graph.store import get_store
from tagwerk.graph.sync import sync_capture
from tagwerk.pipeline import context, normalize, speech, structure, vision
from tagwerk.state import get_project, save_result, today

log = logging.getLogger(__name__)
REPLAY_PAUSE_S = 0.8
MAX_KEPT_MEDIA_BYTES = 300 * 1024 * 1024
_clock = time.monotonic  # replaced in tests
_sleep = asyncio.sleep


def _keep_media(capture: dict) -> None:
    """Copy the first video and up to 3 photos next to the stage cache (cache/<cid>/media/) so a replay can show the
    video after reset_demo.py deleted the uploads; also keep the typed note. Files over 300 MB are skipped."""
    d = structure.cache_path(capture["capture_id"], "x").parent
    d.mkdir(parents=True, exist_ok=True)
    cap_file = d / "capture.json"
    if not cap_file.exists():
        cap_file.write_text(json.dumps({"capture_id": capture["capture_id"], "zone_id": capture["zone_id"],
                                        "note": capture.get("note"), "ts": capture["ts_server"]}, ensure_ascii=False),
                            encoding="utf-8")
    picks = [m for m in capture["media"] if m["type"] == "video"][:1] + [m for m in capture["media"]
                                                                          if m["type"] == "photo"][:3]
    for m in picks:
        src = Path(m["path"])
        dest = d / "media" / re.sub(r"^\d{2}_", "", src.name)  # the API prefixes uploads with an index
        try:
            if src.is_file() and not dest.exists() and src.stat().st_size <= MAX_KEPT_MEDIA_BYTES:
                dest.parent.mkdir(exist_ok=True)
                shutil.copyfile(src, dest)
        except OSError as exc:
            log.warning("could not keep %s: %s", src.name, exc)


def _locate(transcript: dict, pattern: str) -> float | None:
    """Estimated second at which `pattern` (regex, case-insensitive) is spoken: segment start plus its character
    position inside the segment, scaled to the segment's duration."""
    for seg in transcript.get("segments", []):
        m = re.search(pattern, seg["text"], re.I)
        if m:
            return round(seg["start"] + m.start() / max(1, len(seg["text"])) * (seg["end"] - seg["start"]), 2)
    return None


def estimate_t(quote: str, transcript: dict) -> float:
    """Video time of a quote (0.0 when it is not in the transcript, e.g. a typed note)."""
    q = (quote or "").strip().rstrip(".!?")
    return (_locate(transcript, re.escape(q)) if q else None) or 0.0


async def _remote(stage: str, capture: dict) -> dict:
    s = get_settings()
    files = [("media", (Path(m["path"]).name, open(m["path"], "rb"))) for m in capture["media"]
             if Path(m["path"]).exists()]
    try:
        async with httpx.AsyncClient(timeout=600) as client:
            r = await client.post(f"{s.gpu_worker_url.rstrip('/')}/{stage}",
                                  data={"capture": json.dumps(capture)}, files=files)
            r.raise_for_status()
            return r.json()
    finally:
        for _, (_, fh) in files:
            fh.close()


def _cached(cid: str, name: str) -> dict | None:
    p = structure.cache_path(cid, name)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _store_cache(cid: str, name: str, data: dict) -> None:
    p = structure.cache_path(cid, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


async def _gpu_stage(stage: str, capture: dict, derived: dict | None, replay: bool = False,
                     pause: float | None = None) -> dict:
    s = get_settings()
    if (s.replay_mode or replay) and (hit := _cached(capture["capture_id"], stage)) is not None:
        await asyncio.sleep(REPLAY_PAUSE_S if pause is None else pause)
        return hit
    if s.gpu_worker_url:
        try:
            out = await _remote(stage, capture)
        except Exception as exc:  # worker down: degrade to in-process rather than fail the capture
            log.warning("GPU worker %s failed (%s); running in-process", stage, exc)
            out = await _local(stage, capture, derived)
    else:
        out = await _local(stage, capture, derived)
    _store_cache(capture["capture_id"], stage, out)
    return out


async def _local(stage: str, capture: dict, derived: dict | None) -> dict:
    if derived is None:
        derived = normalize.normalize(capture, Path(get_settings().data_dir) / "work" / capture["capture_id"])
    fn = speech.transcribe if stage == "speech" else vision.analyse
    return await asyncio.to_thread(fn, capture, derived)


async def _status(capture_id: str, step: str, **props) -> None:
    await broker.publish({"type": "status", "label": "Capture", "id": capture_id, "props": {"step": step, **props}})


async def run_capture(capture: dict, replay: bool = False, sync_t0: float | None = None) -> dict:
    """replay=True: use cache/<capture_id>/ stage outputs (see API field replay_of) - no GPU, no Claude.
    sync_t0 (replays): clock value when the POST arrived; each change is then published at that time + its second in
    the video, so a video started with the POST and the graph stay in step."""
    validate("capture", capture)
    cid = capture["capture_id"]
    s = get_settings()
    replay = replay or s.replay_mode
    pause = REPLAY_PAUSE_S / 3 if sync_t0 is not None else None  # timed replay: the video clock is already running
    store = get_store()
    project = get_project()

    await broker.publish({"type": "node", "label": "Capture", "id": cid,
                          "props": {"zone_id": capture["zone_id"], "name": f"Capture {capture['ts_server'][11:16]}",
                                    "ts": capture["ts_server"], "date": capture["ts_server"][:10]}})
    await broker.publish({"type": "edge", "label": "IN_ZONE", "id": f"{cid}->{capture['zone_id']}",
                          "props": {"src": cid, "dst": capture["zone_id"]}})

    derived = None
    if not s.gpu_worker_url and not replay:
        derived = await asyncio.to_thread(normalize.normalize, capture, Path(s.data_dir) / "work" / cid)
    await _status(cid, "normalized")

    transcript = validate("transcript", await _gpu_stage("speech", capture, derived, replay, pause))
    if not replay:
        await asyncio.to_thread(_keep_media, capture)
    await _status(cid, "transcribed", text=" ".join(seg["text"] for seg in transcript["segments"])[:300])

    vis = validate("vision", await _gpu_stage("vision", capture, derived, replay, pause))
    labels: dict[str, int] = {}
    for f in vis["frames"]:
        for o in f["objects"]:
            labels[o["label"]] = labels.get(o["label"], 0) + 1
    await _status(cid, "vision", detections=labels,
                  markers=sorted({o["marker_id"] for f in vis["frames"] for o in f["objects"]
                                  if o.get("marker_id") is not None}))

    if replay:
        await asyncio.sleep(REPLAY_PAUSE_S if pause is None else pause)
    cached_ctx = _cached(cid, "context") if replay else None
    ctx = validate("context", cached_ctx or context.build_context(capture, vis, project, transcript))
    _store_cache(cid, "context", ctx)
    structured = validate("structured", await asyncio.to_thread(structure.structure, capture, transcript, vis,
                                                                 ctx, project, replay))
    await _status(cid, "structured")

    photos = [Path(m["path"]).name for m in capture["media"] if m["type"] == "photo"]
    meta = {"capture_id": cid, "zone_id": capture["zone_id"], "ts": capture["ts_server"],
            "note": capture.get("note"), "lang": transcript["lang"], "photos": photos, "weather": ctx["weather"]}
    changes = project.apply_structured(meta, structured)
    project.captures[cid].update({"photos": photos, "weather": ctx["weather"], "lang": transcript["lang"]})
    save_result(meta, structured)
    try:
        await asyncio.to_thread(sync_capture, store, project, cid, vis)
    except Exception as exc:  # the state is saved; a graph hiccup must not fail the capture or the live view
        log.warning("graph sync failed for %s: %s", cid, exc)
    try:
        await _publish_results(project, cid, changes, replay, transcript, sync_t0)
    except Exception as exc:  # noqa: BLE001
        log.warning("websocket publish failed for %s: %s", cid, exc)
    try:
        await _status(cid, "done")
    except Exception:  # noqa: BLE001
        pass
    return {"capture": capture, "transcript": transcript, "vision": vis, "context": ctx, "structured": structured,
            "changes": changes}


async def _publish_change(project, cid: str, ch: dict, replay: bool) -> None:
    eid = ch["element_id"]
    el = project.elements[eid]
    rel = "PROPOSES" if ch["action"] == "proposed" else "CONFIRMED"
    await broker.publish({"type": "edge", "label": rel, "id": f"{cid}->{eid}",
                          "props": {"src": cid, "dst": eid, "state": ch["state"], "quote": ch["quote"]}})
    await broker.publish({"type": "update", "label": "Element", "id": eid,
                          "props": {"state": el["state"], "pct": el["pct"], "via": rel,
                                    "proposed": ch["state"] if rel == "PROPOSES" else None, "name": el["name_de"]}})


async def _publish_event(e: dict, cid: str) -> None:
    short = e["text"] if len(e["text"]) <= 48 else e["text"][:48].rsplit(" ", 1)[0] + " …"
    await broker.publish({"type": "node", "label": "Event", "id": e["id"],
                          "props": {"name": short, "text": e["text"], "type": e["type"], "capture": cid,
                                    "severity": e["severity"], "activity_id": e.get("activity_id")}})


async def _publish_results(project, cid: str, changes: list[dict], replay: bool, transcript: dict | None = None,
                           sync_t0: float | None = None) -> None:
    fc = project.forecast(today())
    shown = [ch for ch in changes if ch["action"] in ("confirmed", "proposed", "unchanged")]
    events = [e for e in project.events if e["capture_id"] == cid]
    if sync_t0 is None:  # live or plain replay: everything right away (replays keep a short pause per element)
        for ch in shown:
            await _publish_change(project, cid, ch, replay)
            if replay:
                await _sleep(REPLAY_PAUSE_S / 2)
    else:  # timed replay: each item at its second of the video
        tr = transcript or {"segments": []}
        timeline = [(ch.get("t") or estimate_t(ch["quote"], tr), 0, ch) for ch in shown]
        for e in events:
            t = _locate(tr, r"krank|abwesend|\bsick\b|fehl") if e["type"] == "absence" else estimate_t(e["text"], tr)
            timeline.append((t or 0.0, 1, e))
        timeline.sort(key=lambda x: (x[0], x[1]))
        for t, kind, item in timeline:
            delay = sync_t0 + t - _clock()
            # wait for its second; an item that is already due (typed note, t=0) gets the usual pause so it animates
            await _sleep(delay if delay > 0 else REPLAY_PAUSE_S / 2)
            await (_publish_change(project, cid, item, replay) if kind == 0 else _publish_event(item, cid))
    touched = {a for ch in changes for a in project.activities_of(ch["element_id"])}
    touched |= {e["activity_id"] for e in events if e.get("activity_id")}
    for aid in sorted(touched):  # an absence moves its activity's forecast too
        r = fc[aid]
        await broker.publish({"type": "update", "label": "Activity", "id": aid,
                              "props": {"pct": r["pct"], "delay_d": r["delay_d"], "name": r["name"],
                                        "forecast_finish": r["forecast_finish"].isoformat()}})
    if sync_t0 is None:
        for e in events:
            await _publish_event(e, cid)
