"""Runs one capture through every stage, validates each output, writes the graph, emits events.

Speech and vision run on the remote GPU worker when GPU_WORKER_URL is set, otherwise in-process.
"""
import json
import logging
from pathlib import Path

import httpx

from tagwerk.config import get_settings
from tagwerk.contracts import validate
from tagwerk.events import broker
from tagwerk.graph.store import get_store
from tagwerk.pipeline import context, normalize, speech, structure, vision

log = logging.getLogger(__name__)


async def _remote(stage: str, capture: dict) -> dict:
    s = get_settings()
    files = [("media", (Path(m["path"]).name, open(m["path"], "rb"))) for m in capture["media"]
             if Path(m["path"]).exists()]
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{s.gpu_worker_url.rstrip('/')}/{stage}",
                                  data={"capture": json.dumps(capture)}, files=files)
            r.raise_for_status()
            return r.json()
    finally:
        for _, (_, fh) in files:
            fh.close()


async def _gpu_stage(stage: str, capture: dict, derived: dict) -> dict:
    if get_settings().gpu_worker_url:
        return await _remote(stage, capture)
    return speech.transcribe(capture, derived) if stage == "speech" else vision.analyse(capture, derived)


async def _status(capture_id: str, step: str) -> None:
    await broker.publish({"type": "status", "label": "Capture", "id": capture_id, "props": {"step": step}})


async def run_capture(capture: dict) -> dict:
    validate("capture", capture)
    cid = capture["capture_id"]
    store = get_store()
    s = get_settings()

    # 1. capture node appears immediately
    store.merge_node("Capture", cid, {"zone_id": capture["zone_id"], "ts": capture["ts_server"]})
    store.merge_node("Zone", capture["zone_id"], {})
    store.merge_edge(cid, "IN_ZONE", capture["zone_id"])
    await broker.publish({"type": "node", "label": "Capture", "id": cid, "props": {"zone_id": capture["zone_id"]}})

    derived = normalize.normalize(capture, Path(s.data_dir) / "work" / cid)
    await _status(cid, "normalized")

    transcript = validate("transcript", await _gpu_stage("speech", capture, derived))
    await _status(cid, "transcribed")

    vis = validate("vision", await _gpu_stage("vision", capture, derived))
    for frame in vis["frames"]:
        for o in frame["objects"]:
            oid = f"{cid}:{o['obj_id']}"
            store.merge_node("Observation", oid, {"label": o["label"], "conf": o["conf"]})
            store.merge_edge(cid, "DETECTED", oid)
            await broker.publish({"type": "node", "label": "Observation", "id": oid, "props": {"label": o["label"]}})
        for t in frame["triplets"]:
            store.merge_edge(f"{cid}:{t['s']}", "REL", f"{cid}:{t['o']}", {"predicate": t["rel"], "score": t["score"]})
    await _status(cid, "vision")

    ctx = validate("context", context.build_context(capture, vis))
    wid = f"{cid}:weather"
    store.merge_node("WeatherReading", wid, ctx["weather"])
    store.merge_edge(cid, "UNDER", wid)

    structured = validate("structured", structure.structure(capture, transcript, vis, ctx))
    for w in structured["work_done"]:
        for eid in w["element_ids"]:
            store.merge_node("Element", eid, {})
            rel = "CONFIRMED" if w["evidence"] in ("voice", "both") else "PROPOSES"
            store.merge_edge(cid, rel, eid, {"state": w["state_proposed"], "quote": w["quote"]})
            await broker.publish({"type": "update", "label": "Element", "id": eid,
                                  "props": {"state": w["state_proposed"], "via": rel}})
    for i, a in enumerate(structured["absences"]):
        ev = f"{cid}:absence:{i}"
        store.merge_node("Event", ev, {"type": "absence", **a})
        store.merge_edge(cid, "RAISED", ev)
    await _status(cid, "done")

    return {"capture": capture, "transcript": transcript, "vision": vis, "context": ctx, "structured": structured}
