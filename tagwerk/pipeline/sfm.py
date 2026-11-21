"""Scan 3D: structure from motion + objects lifted into the model (docs/UI-V2-CONTRACT.md, "Scan 3D").

analyse(capture, workdir) -> the sfm.json dict (cache/<cid>/sfm.json):
  1. ffmpeg: 40-80 frames (2.5 fps, fewer for long clips), longest side 1280 px
  2. pycolmap in a SUBPROCESS (tagwerk.pipeline.sfm_colmap): SIFT + sequential matching + incremental mapping, the
     largest model wins; the whole stage has a 150 s limit and never raises (ok false + German reason instead)
  3. YOLO / YOLO-World / RelateAnything run on the SfM keyframes themselves (same images as the model, so every box
     maps exactly onto the triangulated points; the 1 fps / 20-frame vision stage would cover far less)
  4. a detection becomes a 3D observation from the points whose keypoint falls inside its box (median position, 10-90 %
     extent); observations of the same label that are close relative to the scene size are one instance
  5. relations (RelateAnything triplets) are aggregated per instance pair with German predicate labels
When the reconstruction fails the objects and relations are still listed from the 2D detections (position null).
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from tagwerk.pipeline.scan import CATALOG, CATEGORY_DE

log = logging.getLogger(__name__)

TIME_LIMIT_S = 150
DETECT_RESERVE_S = 30  # kept free for the detection pass after the reconstruction
MAX_FRAMES, FPS, LONG_SIDE, MAX_POINTS = 80, 2.5, 1280, 20000
MERGE_FACTOR = 0.08  # same label and closer than 8 % of the scene size = one instance
MAX_RELATIONS = 8
UNITS = "relative (SfM scale is arbitrary)"

REL_DE = {"on": "auf", "standing on": "steht auf", "in front of": "vor", "behind": "hinter", "next to": "neben",
          "beside": "neben", "above": "über", "below": "unter", "under": "unter", "mounted on": "montiert an",
          "attached to": "an", "holding": "hält", "using": "benutzt", "blocking": "blockiert", "inside": "in",
          "in": "in", "near": "neben"}


def rel_de(rel: str) -> str:
    return REL_DE.get(rel.lower(), rel)


# ---------------------------------------------------------------- pure logic (unit tested without pycolmap)

def frame_plan(duration_s: float) -> float:
    """Frames per second: 2.5 for clips up to ~32 s, fewer for longer ones so at most 80 frames are used."""
    return FPS if not duration_s or duration_s * FPS <= MAX_FRAMES else MAX_FRAMES / duration_s


def lift_box(bbox, kp_xy: np.ndarray, kp_xyz: np.ndarray, grow=(1.0, 1.3), min_pts: int = 3) -> dict | None:
    """3D position/extent of a 2D box from the triangulated keypoints inside it (box grown once if too sparse)."""
    if len(kp_xy) == 0:
        return None
    x1, y1, x2, y2 = bbox
    cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
    for g in grow:
        inside = ((np.abs(kp_xy[:, 0] - cx) <= w * g / 2) & (np.abs(kp_xy[:, 1] - cy) <= h * g / 2))
        if inside.sum() >= min_pts:
            p = kp_xyz[inside]
            lo, hi = np.percentile(p, 10, axis=0), np.percentile(p, 90, axis=0)
            return {"pos": np.median(p, axis=0).tolist(), "ext": (hi - lo).tolist(), "n": int(inside.sum())}
    return None


def scene_scale(points: np.ndarray) -> float:
    """Size of the scene: diagonal of the 5-95 % box of the points (robust against stray points)."""
    if len(points) == 0:
        return 1.0
    p = np.asarray(points)[:, :3]
    return float(np.linalg.norm(np.percentile(p, 95, axis=0) - np.percentile(p, 5, axis=0))) or 1.0


def merge_instances(dets: list[dict], scale: float, factor: float = MERGE_FACTOR) -> list[list[dict]]:
    """Greedy clustering per label: a detection joins the nearest cluster centroid within factor * scale."""
    clusters: list[tuple[list[dict], np.ndarray]] = []
    for d in sorted(dets, key=lambda d: -d["conf"]):
        pos = np.asarray(d["pos"], float)
        best, best_dist = None, factor * scale
        for i, (members, cen) in enumerate(clusters):
            if members[0]["label"] != d["label"]:
                continue
            dist = float(np.linalg.norm(cen - pos))
            if dist <= best_dist:
                best, best_dist = i, dist
        if best is None:
            clusters.append(([d], pos))
        else:
            members = clusters[best][0] + [d]
            clusters[best] = (members, np.median([m["pos"] for m in members], axis=0))
    return [m for m, _ in clusters]


# COCO classes that are not in the scan catalogue but show up on site and in rooms
COCO_DE = {"motorcycle": "Motorrad", "bicycle": "Fahrrad", "bus": "Bus", "boat": "Boot", "laptop": "Laptop",
           "cell phone": "Handy", "bottle": "Flasche", "cup": "Becher", "book": "Buch", "backpack": "Rucksack",
           "handbag": "Tasche", "suitcase": "Koffer", "clock": "Uhr", "vase": "Vase", "keyboard": "Tastatur",
           "mouse": "Maus", "oven": "Ofen", "microwave": "Mikrowelle", "umbrella": "Schirm", "scissors": "Schere",
           "dog": "Hund", "cat": "Katze", "bird": "Vogel", "traffic light": "Ampel", "stop sign": "Stoppschild"}


def _info(label: str) -> tuple[str, str]:
    cat, _ifc, name_de, _t = CATALOG.get(label, ("other", None, COCO_DE.get(label, label.capitalize()), ""))
    return name_de, CATEGORY_DE[cat]


def match_element(label: str, elements: list[dict], used: set[str]) -> str | None:
    """First unused project element that is this label (alias) or has the catalogue's German name."""
    name_de = _info(label)[0].lower()
    for e in elements or []:
        if e["id"] in used:
            continue
        al = {a.lower() for a in e.get("aliases", [])}
        if label.lower() in al or name_de in al or e["name_de"].lower().rstrip(" 0123456789") == name_de:
            used.add(e["id"])
            return e["id"]
    return None


def _relations_for(objs: list[dict], triplets: list[dict], det_inst: dict[str, str]) -> None:
    """Attach aggregated, German relations to each object (in place)."""
    by_id = {o["id"]: o for o in objs}
    agg: dict[tuple, dict] = {}
    for t in triplets:
        a, b = det_inst.get(t["s"]), det_inst.get(t["o"])
        if not a or not b or a == b:
            continue
        r = agg.setdefault((a, t["rel"], b), {"count": 0, "score": 0.0, "source": t.get("source", "model")})
        r["count"] += 1
        if t["score"] >= r["score"]:
            r["score"], r["source"] = t["score"], t.get("source", "model")
    for (a, rel, b), r in agg.items():
        by_id[a]["relations"].append({"rel": rel, "rel_de": rel_de(rel), "target": b, "target_name": by_id[b]["name_de"],
                                      "score": round(r["score"], 3), "count": r["count"], "source": r["source"]})
    for o in objs:
        o["relations"] = sorted(o["relations"], key=lambda r: -(r["count"] * r["score"]))[:MAX_RELATIONS]


def build_objects(dets: list[dict], triplets: list[dict], scale: float, cid: str,
                  elements: list[dict] | None = None) -> list[dict]:
    """Merge 3D detections into object instances (contract `objects`)."""
    objs, det_inst, used = [], {}, set()
    groups = merge_instances(dets, scale)
    groups.sort(key=lambda g: (-len(g), g[0]["label"]))
    for n, g in enumerate(groups, 1):
        label = g[0]["label"]
        name_de, cat_de = _info(label)
        best = max(g, key=lambda d: d["conf"])
        pos = np.median([d["pos"] for d in g], axis=0)
        ext = np.median([d["ext"] for d in g], axis=0)
        ts = [d["t"] for d in g if d["t"] is not None]
        oid = f"obj-{n}"
        for d in g:
            det_inst[d["obj_id"]] = oid
        objs.append({"id": oid, "label": label, "name_de": name_de, "category_de": cat_de,
                     "position": [round(float(v), 4) for v in pos], "extent": [round(float(v), 4) for v in ext],
                     "detections": len(g), "first_t": min(ts) if ts else None, "last_t": max(ts) if ts else None,
                     "conf": round(float(np.mean([d["conf"] for d in g])), 3),
                     "thumb": f"/media/{cid}/sfm/{best['frame']}",
                     "bbox_in_thumb": [round(float(v), 1) for v in best["bbox"]],
                     "element_id": match_element(label, elements or [], used), "relations": []})
    _relations_for(objs, triplets, det_inst)
    return objs


def objects_2d(frames: list[dict], triplets: list[dict], cid: str, elements: list[dict] | None = None) -> list[dict]:
    """Fallback without a reconstruction: per label as many instances as were seen at once, position null."""
    seen: dict[str, dict] = {}
    for f in frames:
        per: dict[str, list[dict]] = {}
        for d in f["dets"]:
            per.setdefault(d["label"], []).append({**d, "frame": f["name"], "t": f["t"]})
        for label, ds in per.items():
            rec = seen.setdefault(label, {"max": 0, "dets": [], "ids": []})
            rec["max"] = max(rec["max"], len(ds))
            rec["dets"] += ds
    objs, det_inst, used, n = [], {}, set(), 0
    for label, rec in sorted(seen.items(), key=lambda kv: -len(kv[1]["dets"])):
        name_de, cat_de = _info(label)
        best = max(rec["dets"], key=lambda d: d["conf"])
        ts = [d["t"] for d in rec["dets"] if d["t"] is not None]
        for k in range(rec["max"]):
            n += 1
            oid = f"obj-{n}"
            if k == 0:  # the relations of a label are attached to its first instance
                for d in rec["dets"]:
                    det_inst[d["obj_id"]] = oid
            objs.append({"id": oid, "label": label, "name_de": name_de, "category_de": cat_de, "position": None,
                         "extent": None, "detections": len(rec["dets"]) if k == 0 else 0,
                         "first_t": min(ts) if ts else None, "last_t": max(ts) if ts else None,
                         "conf": round(float(np.mean([d["conf"] for d in rec["dets"]])), 3),
                         "thumb": f"/media/{cid}/sfm/{best['frame']}",
                         "bbox_in_thumb": [round(float(v), 1) for v in best["bbox"]],
                         "element_id": match_element(label, elements or [], used), "relations": []})
    _relations_for(objs, triplets, det_inst)
    return objs


def downsample_points(points: np.ndarray, limit: int = MAX_POINTS) -> list[list[float]]:
    pts = np.asarray(points, float)
    if len(pts) > limit:
        pts = pts[np.linspace(0, len(pts) - 1, limit).astype(int)]
    return [[round(float(x), 4) for x in p[:3]] + [int(c) for c in p[3:6]] for p in pts]


def frame_index(name: str) -> int:
    return int(Path(name).stem)


def cameras_json(names, pos, look, fps: float, cid: str) -> list[dict]:
    return [{"t": round((frame_index(n) - 1) / fps, 2), "position": [round(float(v), 4) for v in p],
             "look": [round(float(v), 4) for v in lk], "frame": f"/media/{cid}/sfm/{n}"}
            for n, p, lk in zip(names, pos, look, strict=True)]


# ---------------------------------------------------------------- frames, subprocess, detection

def _empty(cid: str, reason: str, seconds: float = 0.0, **extra) -> dict:
    return {"capture_id": cid, "ok": False, "reason": reason, "seconds": round(seconds, 1), "frames_used": 0,
            "frames_registered": 0, "points": [], "cameras": [], "objects": [], "units": UNITS, **extra}


def probe_duration(video: Path) -> float:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                           capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip() or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


def extract_frames(video: Path, out: Path, fps: float, limit: int = MAX_FRAMES) -> int:
    """0001.jpg ... at `fps` (frame n is at (n-1)/fps seconds), longest side 1280. Returns how many were written."""
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    vf = f"fps={fps:.4f},scale='if(gt(iw,ih),{LONG_SIDE},-2)':'if(gt(iw,ih),-2,{LONG_SIDE})'"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", vf, "-frames:v", str(limit), "-q:v", "3",
                    str(out / "%04d.jpg")], capture_output=True, timeout=120, check=True)
    return len(list(out.glob("*.jpg")))


def run_colmap(frames: Path, work: Path, timeout_s: float) -> tuple[dict | None, str | None]:
    """Reconstruction in a subprocess; (arrays, None) or (None, German reason)."""
    out = work / "model.npz"
    out.unlink(missing_ok=True)
    try:
        r = subprocess.run([sys.executable, "-m", "tagwerk.pipeline.sfm_colmap", str(frames), str(work / "colmap"), str(out)],
                           capture_output=True, text=True, timeout=max(10.0, timeout_s))
    except subprocess.TimeoutExpired:
        return None, f"Zeitlimit von {TIME_LIMIT_S} s überschritten"
    except OSError as exc:
        return None, f"pycolmap konnte nicht gestartet werden ({exc})"
    if r.returncode == 3 or (r.returncode == 0 and not out.exists()):
        return None, "zu wenige zusammenpassende Bilder: Kamera langsamer führen, mehr Textur und Licht"
    if r.returncode != 0:
        log.warning("sfm_colmap exit %s: %s", r.returncode, r.stderr[-400:])
        return None, "pycolmap ist nicht verfügbar oder abgestürzt"
    with np.load(out) as d:
        return {k: d[k] for k in d.files}, None


def detect_frames(frames: Path, names: list[str]) -> tuple[list[dict], list[dict]]:
    """YOLO + YOLO-World + RelateAnything on the keyframes -> ([{name, t-less dets}], triplets). The models are the
    ones the vision stage keeps loaded in the worker."""
    import cv2

    from tagwerk.pipeline import vision

    if not vision.ml_available():
        return [], []
    m = vision.models()
    imgs, ok_names = [], []
    for n in names:
        img = cv2.imread(str(frames / n))
        if img is not None:
            imgs.append(img)
            ok_names.append(n)
    coco = vision._yolo(m["coco"], imgs, vision.COCO_CONF, "coco", m["device"])
    world = vision._yolo(m["world"], imgs, vision.WORLD_CONF, "world", m["device"])
    out, triplets = [], []
    for i, (n, img) in enumerate(zip(ok_names, imgs, strict=True)):
        dets = vision.class_aware_nms(coco[i] + world[i])
        objs = [{"obj_id": f"{Path(n).stem}_o{k}", **d} for k, d in enumerate(dets, 1) if d["source"] != "marker"]
        out.append({"name": n, "objects": objs})
        triplets += [{**t} for t in vision._relations(m, img, objs)]
    return out, triplets


def analyse(capture: dict, workdir: Path, elements: list[dict] | None = None, time_limit: float = TIME_LIMIT_S) -> dict:
    """The whole stage; never raises. `workdir` receives frames/ and the colmap files."""
    cid = capture["capture_id"]
    t0 = time.perf_counter()
    video = next((Path(m["path"]) for m in capture.get("media", []) if m.get("type") == "video"), None)
    if video is None:
        return _empty(cid, "Kein Video in dieser Aufnahme.")
    if not video.exists():
        return _empty(cid, "Die Videodatei wurde nicht gefunden.")
    try:
        workdir = Path(workdir)
        frames = workdir / "frames"
        fps = frame_plan(probe_duration(video))
        n = extract_frames(video, frames, fps)
        if n < 8:
            return _empty(cid, "Das Video ist zu kurz oder nicht lesbar (weniger als 8 Bilder).", time.perf_counter() - t0,
                          fps=fps)
        names = sorted(p.name for p in frames.glob("*.jpg"))
        model, reason = run_colmap(frames, workdir, time_limit - DETECT_RESERVE_S - (time.perf_counter() - t0))
        det_names = ([str(x) for x in model["names"]] if model else names[:: max(1, len(names) // 40)])
        det_frames, triplets = detect_frames(frames, det_names)
        res = _empty(cid, reason or "", time.perf_counter() - t0, fps=round(fps, 4))
        res["frames_used"] = n
        if model is None:
            fr = [{"name": f["name"], "t": round((frame_index(f["name"]) - 1) / fps, 2), "dets": f["objects"]}
                  for f in det_frames]
            res["objects"] = objects_2d(fr, triplets, cid, elements)
            res["reason"] = reason
        else:
            pts = model["points"]
            res.update(ok=True, reason=None, frames_registered=len(model["names"]),
                       points=downsample_points(pts, MAX_POINTS),
                       cameras=cameras_json(model["names"], model["pos"], model["look"], fps, cid))
            res["objects"] = build_objects(lift_detections(det_frames, model, fps), triplets, scene_scale(pts), cid, elements)
        res["seconds"] = round(time.perf_counter() - t0, 1)
        return res
    except Exception as exc:  # noqa: BLE001 - this stage must never fail a capture
        log.exception("sfm failed for %s", cid)
        return _empty(cid, f"3D-Rekonstruktion fehlgeschlagen: {type(exc).__name__}", time.perf_counter() - t0)


def lift_detections(det_frames: list[dict], model: dict, fps: float) -> list[dict]:
    """Detections of the registered frames -> 3D observations (see build_objects)."""
    names = [str(x) for x in model["names"]]
    idx = {n: i for i, n in enumerate(names)}
    obs = model["obs"]
    out = []
    for f in det_frames:
        k = idx.get(f["name"])
        if k is None:
            continue
        mine = obs[obs[:, 0] == k]
        for d in f["objects"]:
            lifted = lift_box(d["bbox"], mine[:, 1:3], mine[:, 3:6])
            if lifted:
                out.append({"label": d["label"], "conf": d["conf"], "bbox": d["bbox"], "obj_id": d["obj_id"],
                            "frame": f["name"], "t": round((frame_index(f["name"]) - 1) / fps, 2), **lifted})
    return out


def ensure_frames(video: Path, dest: Path, fps: float, count: int) -> None:
    """Make cache/<cid>/media/sfm/ hold the same keyframes as the worker used (same fps, same numbering), so /media can
    serve thumbs and camera images even when the reconstruction ran in another process."""
    if re.search(r"\d{4}\.jpg", " ".join(p.name for p in dest.glob("*.jpg"))) and len(list(dest.glob("*.jpg"))) >= count:
        return
    extract_frames(video, dest, fps, count)


def attach_elements(res: dict, elements: list[dict]) -> dict:
    """Fill element_id of every object from the project's elements (same catalogue label / alias), in place."""
    used: set[str] = set()
    for o in res.get("objects", []):
        o["element_id"] = match_element(o["label"], elements, used)
    return res
