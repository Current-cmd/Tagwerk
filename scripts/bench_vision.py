"""Run the vision stage on a folder of images and print per-stage timings and GPU memory.

    python scripts/bench_vision.py IMAGE_DIR [--repeat 2] [--json out.json]
    python scripts/bench_vision.py --make-markers DIR   # render ArUco ids 1-5 onto test images

Images are passed as photos (t = null). The first run includes model loading; later runs are warm.
"""
import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tagwerk.contracts import validate  # noqa: E402
from tagwerk.pipeline import vision  # noqa: E402

EXTS = {".jpg", ".jpeg", ".png"}


def make_markers(out: Path, n: int = 15) -> None:
    """n 960x540 images with 1-3 ArUco markers (ids 1-5) at varying positions, sizes and rotations."""
    import cv2
    import numpy as np
    out.mkdir(parents=True, exist_ok=True)
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    rng = np.random.default_rng(0)
    for k in range(n):
        img = rng.integers(90, 200, (540, 960, 3), dtype=np.uint8)
        img = cv2.GaussianBlur(img, (31, 31), 0)
        for j in range(1 + k % 3):
            mid = 1 + (k + j) % 5
            size = int(rng.integers(70, 160))
            tile = cv2.copyMakeBorder(cv2.aruco.generateImageMarker(d, mid, size), 12, 12, 12, 12,
                                      cv2.BORDER_CONSTANT, value=255)
            rot = cv2.getRotationMatrix2D((tile.shape[1] / 2, tile.shape[0] / 2), float(rng.uniform(-25, 25)), 1)
            tile = cv2.warpAffine(tile, rot, tile.shape[::-1], borderValue=255)
            x, y = 40 + j * 300 + int(rng.integers(0, 80)), int(rng.integers(20, 540 - tile.shape[0] - 20))
            img[y:y + tile.shape[0], x:x + tile.shape[1]] = tile[..., None]
        cv2.imwrite(str(out / f"marker_{k + 1:02d}.jpg"), img)
    print(f"wrote {n} images to {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", type=Path)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--make-markers", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if a.make_markers:
        return make_markers(a.images)

    paths = sorted(p for p in a.images.iterdir() if p.suffix.lower() in EXTS)
    capture = {"capture_id": "bench", "media": [{"type": "photo", "path": str(p)} for p in paths]}
    try:
        import torch
        cuda = torch.cuda.is_available()
    except ImportError:
        cuda = False
    out = None
    for run in range(a.repeat):
        if cuda:
            torch.cuda.reset_peak_memory_stats()
        t = time.perf_counter()
        out = validate("vision", vision.analyse(capture, {"frames_dir": None}))
        wall = time.perf_counter() - t
        stages = " ".join(f"{k}={v:.3f}s" for k, v in vision.TIMINGS.items() if isinstance(v, float))
        mem = f" max_mem={torch.cuda.max_memory_allocated() / 2**20:.0f}MiB" if cuda else ""
        print(f"run {run + 1}: {len(out['frames'])} frames wall={wall:.3f}s {stages}{mem} "
              f"rel={vision.TIMINGS.get('rel_backend')}")

    objs = [o for f in out["frames"] for o in f["objects"]]
    print("objects by source:", dict(Counter(o["source"] for o in objs)))
    print("labels:", dict(Counter(o["label"] for o in objs).most_common(15)))
    print("marker ids:", sorted(o["marker_id"] for o in objs if o["marker_id"] is not None))
    trips = [(f["media_path"], r) for f in out["frames"] for r in f["triplets"]]
    print("triplets:", len(trips), dict(Counter(r["source"] for _, r in trips)))
    for mp, r in trips[:8]:
        lab = {o["obj_id"]: o["label"] for f in out["frames"] for o in f["objects"]}
        print(f"  {Path(mp).name}: {lab[r['s']]} --{r['rel']} [{r['score']:.2f}]--> {lab[r['o']]}")
    if a.json:
        a.json.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
