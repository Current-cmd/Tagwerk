"""Demo fallback: replay an earlier capture from its cached stage outputs (no GPU, no network, no Claude).

    python scripts/replay.py --list
    python scripts/replay.py cap-e2e-2 --zone Z-AUDIENCE [--api http://localhost:8080]

The graph animates exactly as in the original run, under a new capture id.
Upload a fresh file instead with:  python scripts/replay.py --file walk.mp4 --zone Z-STAGE
"""
import argparse
import mimetypes
import uuid
from pathlib import Path

import httpx

p = argparse.ArgumentParser()
p.add_argument("source", nargs="?", help="capture id whose cached outputs to replay")
p.add_argument("--list", action="store_true")
p.add_argument("--file", type=Path)
p.add_argument("--zone", default="Z-AUDIENCE")
p.add_argument("--lang", default="de")
p.add_argument("--api", default="http://localhost:8080")
a = p.parse_args()

if a.list:
    print("\n".join(httpx.get(f"{a.api}/api/replayable").json()))
elif a.file:
    ctype = mimetypes.guess_type(a.file.name)[0] or "application/octet-stream"
    with a.file.open("rb") as fh:
        r = httpx.post(f"{a.api}/captures", data={"zone_id": a.zone, "lang": a.lang},
                       files={"files": (a.file.name, fh, ctype)}, timeout=600)
    print(r.status_code, r.text)
else:
    cid = f"replay-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{a.api}/captures", data={"zone_id": a.zone, "lang": a.lang, "replay_of": a.source,
                                             "capture_id": cid}, timeout=120)
    print(r.status_code, r.text)
