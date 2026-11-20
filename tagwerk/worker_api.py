"""GPU worker: runs speech and vision on the machine with the GPU.

    uvicorn tagwerk.worker_api:app --host 0.0.0.0 --port 8100

The API posts multipart form data: field `capture` (JSON, capture contract) + files `media`.
"""
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

from tagwerk.contracts import validate
from tagwerk.pipeline import normalize, speech, vision

app = FastAPI(title="Tagwerk GPU worker")


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


async def _prepare(capture_json: str, media: list[UploadFile]) -> tuple[dict, dict]:
    capture = validate("capture", json.loads(capture_json))
    workdir = Path(tempfile.mkdtemp(prefix=f"tagwerk-{capture['capture_id']}-"))
    by_name = {}
    for f in media:
        dest = workdir / Path(f.filename or "upload.bin").name
        dest.write_bytes(await f.read())
        by_name[dest.name] = str(dest)
    for m in capture["media"]:  # repoint media at the local copies
        m["path"] = by_name.get(Path(m["path"]).name, m["path"])
    return capture, normalize.normalize(capture, workdir / "derived")


@app.post("/speech")
async def run_speech(capture: str = Form(...), media: list[UploadFile] = File(default=[])) -> dict:
    cap, derived = await _prepare(capture, media)
    return validate("transcript", speech.transcribe(cap, derived))


@app.post("/vision")
async def run_vision(capture: str = Form(...), media: list[UploadFile] = File(default=[])) -> dict:
    cap, derived = await _prepare(capture, media)
    return validate("vision", vision.analyse(cap, derived))
