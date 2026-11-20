"""Replay a stored file through the running API (demo fallback).

    python scripts/replay.py path/to/walk.mp4 --zone Z-STAGE --api http://localhost:8000

TODO(feat/replay): with REPLAY_MODE=true the API serves cache/<capture_id>/*.json instead of
calling the GPU worker and Claude, and re-sends websocket events with realistic delays.
"""
import argparse
import mimetypes
from pathlib import Path

import httpx

p = argparse.ArgumentParser()
p.add_argument("file", type=Path)
p.add_argument("--zone", default="Z-STAGE")
p.add_argument("--lang", default="de")
p.add_argument("--capture-id", default=None)
p.add_argument("--api", default="http://localhost:8000")
a = p.parse_args()

ctype = mimetypes.guess_type(a.file.name)[0] or "application/octet-stream"
data = {"zone_id": a.zone, "lang": a.lang}
if a.capture_id:
    data["capture_id"] = a.capture_id
with a.file.open("rb") as fh:
    r = httpx.post(f"{a.api}/captures", data=data, files={"files": (a.file.name, fh, ctype)}, timeout=300)
print(r.status_code, r.text)
