"""GPU worker: runs speech and vision on the machine with the GPU.

    uvicorn tagwerk.worker_api:app --host 0.0.0.0 --port 8100

The API posts multipart form data: field `capture` (JSON, capture contract) + files `media`.
"""
import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

from tagwerk.contracts import validate
from tagwerk.pipeline import normalize, speech, vision


def warm_models() -> None:
    """Load the models once at startup so the first upload does not pay for it (Whisper turbo takes ~8 s, the vision
    models ~10 s). Vision first: Whisper goes where the GPU memory is left. TAGWERK_NO_WARMUP=1 skips this."""
    import logging
    import os

    if os.environ.get("TAGWERK_NO_WARMUP") == "1":
        return
    log = logging.getLogger(__name__)
    try:
        if vision.ml_available():
            vision.models()
        speech._model()
        log.info("worker models warm")
    except Exception as exc:  # noqa: BLE001 - a failed warm-up must not stop the worker; the first request retries
        log.warning("warm-up failed: %s", exc)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    import asyncio
    import os

    if os.environ.get("TAGWERK_STUBS") != "1":  # tests run with stubs: nothing to load
        asyncio.get_running_loop().run_in_executor(None, warm_models)
    yield


app = FastAPI(title="Tagwerk GPU worker", lifespan=_lifespan)


def _gpu_info() -> dict:
    try:
        import torch  # only installed on the GPU machine

        ok = torch.cuda.is_available()
        return {"torch": torch.__version__, "cuda": ok, "device": torch.cuda.get_device_name(0) if ok else None}
    except ImportError:
        return {"torch": None, "cuda": False, "device": None}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", **_gpu_info()}


async def _save(capture_json: str, media: list[UploadFile]) -> tuple[dict, Path]:
    capture = validate("capture", json.loads(capture_json))
    workdir = Path(tempfile.mkdtemp(prefix=f"tagwerk-{capture['capture_id']}-"))
    by_name = {}
    for f in media:  # the API already made names unique (index prefix)
        dest = workdir / Path(f.filename or "upload.bin").name
        dest.write_bytes(await f.read())
        by_name[dest.name] = str(dest)
    for m in capture["media"]:  # repoint media at the local copies
        m["path"] = by_name.get(Path(m["path"]).name, m["path"])
    return capture, workdir


async def _prepare(capture_json: str, media: list[UploadFile]) -> tuple[dict, dict]:
    capture, workdir = await _save(capture_json, media)
    return capture, normalize.normalize(capture, workdir / "derived")


@app.post("/speech")
async def run_speech(capture: str = Form(...), media: list[UploadFile] = File(default=[])) -> dict:
    cap, derived = await _prepare(capture, media)
    return validate("transcript", speech.transcribe(cap, derived))


@app.post("/vision")
async def run_vision(capture: str = Form(...), media: list[UploadFile] = File(default=[])) -> dict:
    cap, derived = await _prepare(capture, media)
    return validate("vision", vision.analyse(cap, derived))


@app.post("/sfm")
async def run_sfm(capture: str = Form(...), media: list[UploadFile] = File(default=[])) -> dict:
    """3D reconstruction + objects lifted into it (pipeline/sfm.py). Never fails: ok=false carries a German reason.
    Runs in a thread (pycolmap itself in a subprocess with a 150 s limit) so health checks keep answering."""
    import asyncio

    from tagwerk.pipeline import sfm

    cap, workdir = await _save(capture, media)
    return await asyncio.to_thread(sfm.analyse, cap, workdir / "sfm")

