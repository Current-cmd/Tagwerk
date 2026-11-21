"""Runs one capture through every stage, validates each output, updates the project state,
writes the graph and emits websocket events so the live graph grows while it runs.

Speech and vision run on the GPU worker when GPU_WORKER_URL is set, otherwise in-process.
Every stage output is cached in cache/<capture_id>/; with REPLAY_MODE=true cached outputs are used
(no GPU, no Claude) and steps are paced so the graph still animates.
"""
import asyncio
import json
import logging
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


async def _gpu_stage(stage: str, capture: dict, derived: dict | None, replay: bool = False) -> dict:
    s = get_settings()
    if (s.replay_mode or replay) and (hit := _cached(capture["capture_id"], stage)) is not None:
        await asyncio.sleep(REPLAY_PAUSE_S)
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


async def run_capture(capture: dict, replay: bool = False) -> dict:
    """replay=True: use cache/<capture_id>/ stage outputs (see API field replay_of) - no GPU, no Claude."""
    validate("capture", capture)
    cid = capture["capture_id"]
    s = get_settings()
    replay = replay or s.replay_mode
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

    transcript = validate("transcript", await _gpu_stage("speech", capture, derived, replay))
    await _status(cid, "transcribed", text=" ".join(seg["text"] for seg in transcript["segments"])[:300])

    vis = validate("vision", await _gpu_stage("vision", capture, derived, replay))
    labels: dict[str, int] = {}
    for f in vis["frames"]:
        for o in f["objects"]:
            labels[o["label"]] = labels.get(o["label"], 0) + 1
    await _status(cid, "vision", detections=labels,
                  markers=sorted({o["marker_id"] for f in vis["frames"] for o in f["objects"]
                                  if o.get("marker_id") is not None}))

    if replay:
        await asyncio.sleep(REPLAY_PAUSE_S)
    ctx = validate("context", context.build_context(capture, vis, project))
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
    await asyncio.to_thread(sync_capture, store, project, cid, vis)

    fc = project.forecast(today())
    for ch in changes:
        if ch["action"] not in ("confirmed", "proposed", "unchanged"):
            continue
        eid = ch["element_id"]
        el = project.elements[eid]
        rel = "PROPOSES" if ch["action"] == "proposed" else "CONFIRMED"
        await broker.publish({"type": "edge", "label": rel, "id": f"{cid}->{eid}",
                              "props": {"src": cid, "dst": eid, "state": ch["state"], "quote": ch["quote"]}})
        await broker.publish({"type": "update", "label": "Element", "id": eid,
                              "props": {"state": el["state"], "pct": el["pct"], "via": rel,
                                        "proposed": ch["state"] if rel == "PROPOSES" else None,
                                        "name": el["name_de"]}})
        if replay:
            await asyncio.sleep(REPLAY_PAUSE_S / 2)
    for aid in sorted({a for ch in changes for a in project.activities_of(ch["element_id"])}):
        r = fc[aid]
        await broker.publish({"type": "update", "label": "Activity", "id": aid,
                              "props": {"pct": r["pct"], "delay_d": r["delay_d"], "name": r["name"],
                                        "forecast_finish": r["forecast_finish"].isoformat()}})
    for e in project.events:
        if e["capture_id"] == cid:
            short = e["text"] if len(e["text"]) <= 48 else e["text"][:48].rsplit(" ", 1)[0] + " …"
            await broker.publish({"type": "node", "label": "Event", "id": e["id"],
                                  "props": {"name": short, "text": e["text"], "type": e["type"], "capture": cid,
                                            "severity": e["severity"], "activity_id": e.get("activity_id")}})
    await _status(cid, "done")
    return {"capture": capture, "transcript": transcript, "vision": vis, "context": ctx, "structured": structured,
            "changes": changes}
