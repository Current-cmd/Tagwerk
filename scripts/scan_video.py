"""Scan a video with the running API: what do the models see, in which categories?

    python scripts/scan_video.py clip.mp4                      # print the inventory
    python scripts/scan_video.py clip.mp4 --make-project site1 # also write seed/projects/site1/
    PROJECT=site1 uvicorn tagwerk.api.app:app --port 8082      # then run Tagwerk on it
"""
import argparse
import json
import mimetypes
from pathlib import Path

import httpx

ap = argparse.ArgumentParser()
ap.add_argument("file", type=Path)
ap.add_argument("--api", default="http://localhost:8080")
ap.add_argument("--make-project")
ap.add_argument("--zone-name", default="Baustelle")
ap.add_argument("--json", action="store_true")
a = ap.parse_args()
ctype = mimetypes.guess_type(a.file.name)[0] or "video/mp4"
data = {"zone_name": a.zone_name}
if a.make_project:
    data["make_project"] = a.make_project
with a.file.open("rb") as fh:
    r = httpx.post(f"{a.api}/api/scan", data=data, files={"files": (a.file.name, fh, ctype)}, timeout=900)
r.raise_for_status()
inv = r.json()
if a.json:
    print(json.dumps(inv, ensure_ascii=False, indent=1))
else:
    print(f"{a.file.name}: {inv['frames']} frames, {inv['element_count']} building elements, "
          f"up to {inv['people_max']} people")
    for cat, items in inv["summary"].items():
        print(f"  {cat:14} {', '.join(items)}")
    if inv.get("project"):
        print("project:", inv["project"])
