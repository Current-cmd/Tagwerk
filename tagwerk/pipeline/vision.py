"""Detection + relations -> vision contract.

Per capture: up to MAX_FRAMES images (1 fps video frames from normalize, t = index - 1 s, plus
photos with t = null), each run through
- ArUco DICT_4X4_50 -> objects with source="marker", marker_id = the ArUco id
- YOLO11s (COCO, conf >= 0.35) + YOLO-World (WORLD_CLASSES, conf >= 0.25), class-aware NMS 0.5
- RelateAnything restricted to RELATIONS (score >= 0.3); fallback: geometric relations
  (on / above / below / next to from box positions) with source="geometry"

Models load once into a module-level singleton (fp32, cuda:0 if available). A model that is
missing locally is skipped with a warning; nothing is ever downloaded. Without torch/ultralytics
(CPU-only API machine) analyse() returns the fixture stub.

Env overrides: TAGWERK_YOLO_WEIGHTS, TAGWERK_WORLD_WEIGHTS, TAGWERK_RELSGG_DIR.
"""
import importlib.util
import logging
import os
import time
from pathlib import Path

import numpy as np

from tagwerk.pipeline import stub

log = logging.getLogger(__name__)

RELATIONS = ["on", "standing on", "in front of", "behind", "next to", "above", "below",
             "mounted on", "attached to", "holding", "using", "blocking"]
# open-vocabulary classes: auditorium elements + general construction-site vocabulary
WORLD_CLASSES = ["stage", "lectern", "projection screen", "projector", "speaker", "lighting truss", "cable", "door",
                 "stairs", "wall", "window", "ceiling", "floor", "scaffolding", "ladder", "formwork", "rebar",
                 "brick wall", "drywall panel", "concrete column", "steel beam", "pipe", "cable tray", "crane",
                 "excavator", "concrete mixer", "wheelbarrow", "hard hat", "safety vest", "power tool", "pallet",
                 "insulation", "radiator", "socket", "light fixture", "robot", "concrete pump",
                 "construction scaffolding", "gypsum board", "plywood board", "wooden frame"]

MAX_FRAMES = 20
COCO_CONF = 0.35
WORLD_CONF = 0.25
NMS_IOU = 0.5
REL_MIN_SCORE = 0.3
REL_TOPK = 10
IMGSZ = 640

ROOT = Path(__file__).resolve().parents[2]
RELSGG_DIR = Path(os.getenv("TAGWERK_RELSGG_DIR",
                            Path.home() / "Developer/perception/RelateAnything/deploy/dist/relsgg-vits16plus"))

_MODELS = None
TIMINGS: dict = {}  # per-stage seconds of the last analyse() call (read by scripts/bench_vision.py)


def ml_available() -> bool:
    return all(importlib.util.find_spec(m) is not None for m in ("torch", "ultralytics", "cv2"))


# ---------------------------------------------------------------- frames

def collect_frames(capture: dict, derived: dict, limit: int = MAX_FRAMES) -> list[dict]:
    """[{t, path, media_path}] for 1 fps video frames and photos, evenly sampled down to `limit`."""
    items = []
    frames_dir = Path(derived.get("frames_dir") or "")
    if derived.get("frames_dir") and frames_dir.is_dir():
        for p in sorted(frames_dir.glob("*.jpg")):
            if p.stem.isdigit():
                t = float(int(p.stem) - 1)
            elif p.stem.startswith("photo_"):
                t = None  # normalize already copied the photo here
            else:
                continue
            items.append({"t": t, "path": str(p), "media_path": f"{frames_dir.name}/{p.name}"})
    if "photos" not in derived:  # normalize did not handle photos: read them from the capture
        for m in capture.get("media", []):
            if m.get("type") == "photo":
                items.append({"t": None, "path": m["path"], "media_path": m["path"]})
    if len(items) > limit:
        idx = np.linspace(0, len(items) - 1, limit).round().astype(int)
        items = [items[i] for i in sorted(set(idx))]
    return items


# ---------------------------------------------------------------- geometry

def _iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """IoU of box a [4] against boxes b [N, 4]."""
    x1 = np.maximum(a[0], b[:, 0]); y1 = np.maximum(a[1], b[:, 1])
    x2 = np.minimum(a[2], b[:, 2]); y2 = np.minimum(a[3], b[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = lambda r: (r[..., 2] - r[..., 0]) * (r[..., 3] - r[..., 1])
    return inter / np.maximum(area(a) + area(b) - inter, 1e-9)


def class_aware_nms(dets: list[dict], iou: float = NMS_IOU) -> list[dict]:
    """Greedy NMS within each label; dets are {label, bbox, conf, source}."""
    keep = []
    for label in {d["label"] for d in dets}:
        group = sorted((d for d in dets if d["label"] == label), key=lambda d: -d["conf"])
        boxes = np.array([d["bbox"] for d in group], dtype=np.float64)
        alive = np.ones(len(group), bool)
        for i in range(len(group)):
            if not alive[i]:
                continue
            keep.append(group[i])
            alive[i + 1:] &= _iou(boxes[i], boxes[i + 1:]) < iou
    return sorted(keep, key=lambda d: -d["conf"])


def geometric_relations(objects: list[dict], topk: int = REL_TOPK) -> list[dict]:
    """on / above / below / next to from box positions (image y grows downwards)."""
    out = []
    for s in objects:
        for o in objects:
            if s is o:
                continue
            sx1, sy1, sx2, sy2 = s["bbox"]; ox1, oy1, ox2, oy2 = o["bbox"]
            sw, sh = max(sx2 - sx1, 1e-6), max(sy2 - sy1, 1e-6)
            ow, oh = max(ox2 - ox1, 1e-6), max(oy2 - oy1, 1e-6)
            x_ov = max(0.0, min(sx2, ox2) - max(sx1, ox1)) / min(sw, ow)
            y_ov = max(0.0, min(sy2, oy2) - max(sy1, oy1)) / min(sh, oh)
            rel = None
            if x_ov > 0.3 and oy1 - 0.1 * oh <= sy2 <= oy1 + 0.3 * oh and sy1 < oy1:
                rel, score = "on", 0.6        # s rests on o's top edge
            elif x_ov > 0.3 and sy2 < oy1:
                rel, score = "above", 0.5
            elif x_ov > 0.3 and sy1 > oy2:
                rel, score = "below", 0.5
            elif y_ov > 0.5 and x_ov < 0.2:
                gap = max(ox1 - sx2, sx1 - ox2, 0.0)
                if gap < 0.5 * max(sw, ow):
                    rel, score = "next to", 0.4
            if rel:
                out.append({"s": s["obj_id"], "rel": rel, "o": o["obj_id"], "score": score,
                            "source": "geometry"})
    out.sort(key=lambda r: -r["score"])
    return out[:topk]


# ---------------------------------------------------------------- models

class _OnnxRelations:
    """RelateAnything's ONNX export (same checkpoint) on onnxruntime; needs no transformers."""

    def __init__(self, dist: Path, predicates: list[str]):
        import json

        import onnxruntime as ort
        meta = json.loads((dist / "relateanything.json").read_text())
        self.img_size, self.max_boxes = meta["img_size"], meta["max_boxes"]
        cal = meta.get("calibration") or {}
        self.a, self.b = float(cal.get("a", 1.0)), float(cal.get("b", 0.0))
        bank = np.load(dist / "predicate_bank.npz", allow_pickle=True)
        index = {str(n): i for i, n in enumerate(bank["names"])}
        idx = np.array([index[p] for p in predicates])  # KeyError if a phrase is not in the bank
        self.W = np.ascontiguousarray(bank["W"][idx].astype(np.float32))
        self.alpha = np.ascontiguousarray(bank["alpha"][idx].astype(np.float32))
        self.predicates = list(predicates)
        providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
                     if p in ort.get_available_providers()]
        self.sess = ort.InferenceSession(str(dist / "relateanything.onnx"), providers=providers)

    def predict(self, img_bgr: np.ndarray, boxes: np.ndarray, scores: np.ndarray, topk: int):
        import cv2
        H, W = img_bgr.shape[:2]
        n = min(len(boxes), self.max_boxes)
        order = np.argsort(-scores)[:n]
        b = boxes[order].astype(np.float32).copy()
        b[:, [0, 2]] /= W; b[:, [1, 3]] /= H
        cxcywh = np.stack([(b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2,
                           b[:, 2] - b[:, 0], b[:, 3] - b[:, 1]], -1)
        padded = np.zeros((1, self.max_boxes, 4), np.float32)
        padded[0, :n] = cxcywh
        x = cv2.resize(img_bgr, (self.img_size, self.img_size), interpolation=cv2.INTER_LINEAR)
        x = np.ascontiguousarray(x[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0)
        pred, pair, sub, obj, valid = self.sess.run(None, {
            "image": x, "boxes": padded, "box_counts": np.array([n], np.int64),
            "W": self.W, "alpha": self.alpha})
        z = self.a * (pred[0] + pair[0][:, None]) + self.b
        prob = 1.0 / (1.0 + np.exp(-z))
        best_p, best_s = prob.argmax(-1), prob.max(-1)
        sub, obj, valid = sub[0], obj[0], valid[0].astype(bool)
        keep = valid & (sub < n) & (obj < n) & (sub != obj)
        cand = sorted(((float(best_s[k]), int(order[sub[k]]), int(order[obj[k]]), int(best_p[k]))
                       for k in np.nonzero(keep)[0]), reverse=True)
        return [(si, self.predicates[p], oi, s) for s, si, oi, p in cand[:topk]]


class _TorchRelations:
    def __init__(self, dist: Path, predicates: list[str], device: str):
        from relsgg import RelateAnything
        self.model = RelateAnything.from_checkpoint(str(dist / "model.pth"), predicates=predicates,
                                                    device=device)

    def predict(self, img_bgr, boxes, scores, topk):
        return [(t.subject_idx, t.predicate, t.object_idx, float(t.score))
                for t in self.model.predict(img_bgr, boxes, topk=topk)]


def _weights(env: str, name: str) -> Path | None:
    for p in (os.getenv(env), ROOT / name, Path.cwd() / name):
        if p and Path(p).is_file():
            return Path(p)
    return None


def _load_models() -> dict:
    os.environ.setdefault("YOLO_AUTOINSTALL", "False")  # never pip-install from inside the worker
    os.environ.setdefault("YOLO_OFFLINE", "True")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import torch
    from ultralytics import YOLO

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    m = {"device": device, "coco": None, "world": None, "rel": None, "rel_backend": "geometry"}

    w = _weights("TAGWERK_YOLO_WEIGHTS", "yolo11s.pt")
    if w:
        m["coco"] = YOLO(str(w))
    else:
        log.warning("vision: yolo11s.pt not found locally; COCO detection disabled")

    w = _weights("TAGWERK_WORLD_WEIGHTS", "yolov8s-worldv2.pt")
    if w and importlib.util.find_spec("clip") is not None:
        try:
            world = YOLO(str(w))
            world.set_classes(WORLD_CLASSES)
            m["world"] = world
        except Exception as e:  # noqa: BLE001
            log.warning("vision: YOLO-World failed to load (%s); world classes disabled", e)
    else:
        log.warning("vision: YOLO-World disabled (weights %s, clip %s)",
                    "found" if w else "missing", "ok" if importlib.util.find_spec("clip") else "missing")

    for backend, make in (("model-torch", lambda: _TorchRelations(RELSGG_DIR, RELATIONS, device)),
                          ("model-onnx", lambda: _OnnxRelations(RELSGG_DIR, RELATIONS))):
        try:
            m["rel"], m["rel_backend"] = make(), backend
            break
        except Exception as e:  # noqa: BLE001
            log.warning("vision: RelateAnything %s unavailable (%s: %s)", backend, type(e).__name__, e)
    if m["rel"] is None:
        log.warning("vision: using geometric relations")
    return m


def models() -> dict:
    global _MODELS
    if _MODELS is None:
        _MODELS = _load_models()
    return _MODELS


# ---------------------------------------------------------------- stages

def _detect_markers(img_bgr: np.ndarray, detector) -> list[dict]:
    import cv2
    corners, ids, _ = detector.detectMarkers(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY))
    out = []
    if ids is not None:
        for c, i in zip(corners, ids.flatten()):
            pts = c.reshape(-1, 2)
            out.append({"label": "marker", "bbox": [float(v) for v in (*pts.min(0), *pts.max(0))],
                        "conf": 1.0, "marker_id": int(i), "source": "marker"})
    return out


def _yolo(model, images: list, conf: float, source: str, device: str) -> list[list[dict]]:
    if model is None or not images:
        return [[] for _ in images]
    results = model.predict(images, conf=conf, imgsz=IMGSZ, device=device, verbose=False)
    out = []
    for r in results:
        names = r.names
        out.append([{"label": names[int(c)], "bbox": [round(float(v), 1) for v in b],
                     "conf": round(float(s), 4), "marker_id": None, "source": source}
                    for b, s, c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist())])
    return out


def _relations(m: dict, img_bgr: np.ndarray, objects: list[dict]) -> list[dict]:
    objects = [o for o in objects if o["source"] != "marker"]  # marker-marker relations carry no meaning
    if len(objects) < 2:
        return []
    if m["rel"] is not None:
        try:
            boxes = np.array([o["bbox"] for o in objects], np.float32)
            scores = np.array([o["conf"] for o in objects], np.float32)
            return [{"s": objects[si]["obj_id"], "rel": rel, "o": objects[oi]["obj_id"],
                     "score": round(score, 4), "source": "model"}
                    for si, rel, oi, score in m["rel"].predict(img_bgr, boxes, scores, REL_TOPK)
                    if score >= REL_MIN_SCORE]
        except Exception as e:  # noqa: BLE001
            log.warning("vision: RelateAnything failed at runtime (%s); geometric fallback", e)
    return geometric_relations(objects)


def analyse(capture: dict, derived: dict) -> dict:
    if not ml_available():
        if os.environ.get("TAGWERK_STUBS") != "1":  # never pass fixture detections off as real ones
            log.error("torch/ultralytics not installed: vision stage returns no frames (install .[gpu])")
            return {"capture_id": capture["capture_id"], "frames": []}
        return stub("vision", capture["capture_id"])
    import cv2

    t0 = time.perf_counter()
    m = models()
    TIMINGS.clear()
    TIMINGS["load"] = time.perf_counter() - t0

    t = time.perf_counter()
    frames, images = [], []
    for f in collect_frames(capture, derived):
        img = cv2.imread(f["path"])
        if img is None:
            log.warning("vision: cannot read %s", f["path"])
            continue
        frames.append(f)
        images.append(img)
    TIMINGS["read"] = time.perf_counter() - t

    t = time.perf_counter()
    aruco = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
                                    cv2.aruco.DetectorParameters())
    markers = [_detect_markers(img, aruco) for img in images]
    TIMINGS["aruco"] = time.perf_counter() - t

    t = time.perf_counter()
    coco = _yolo(m["coco"], images, COCO_CONF, "coco", m["device"])
    TIMINGS["coco"] = time.perf_counter() - t
    t = time.perf_counter()
    world = _yolo(m["world"], images, WORLD_CONF, "world", m["device"])
    TIMINGS["world"] = time.perf_counter() - t

    t = time.perf_counter()
    out_frames = []
    for i, (f, img) in enumerate(zip(frames, images)):
        dets = markers[i] + class_aware_nms(coco[i] + world[i])
        objects = [{"obj_id": f"f{i}_o{n}", **d} for n, d in enumerate(dets, 1)]
        out_frames.append({"t": f["t"], "media_path": f["media_path"], "objects": objects,
                           "triplets": _relations(m, img, objects)})
    TIMINGS["relations"] = time.perf_counter() - t
    TIMINGS["total"] = time.perf_counter() - t0
    TIMINGS["rel_backend"] = m["rel_backend"]
    if not frames:
        log.warning("vision: no frames for %s (frames_dir=%s)", capture["capture_id"], derived.get("frames_dir"))
    return {"capture_id": capture["capture_id"], "frames": out_frames}
