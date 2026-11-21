"""Scan 3D: structure from motion + objects lifted into the model (docs/UI-V2-CONTRACT.md, "Scan 3D").

analyse(capture, workdir) -> the sfm.json dict (cache/<cid>/sfm.json):
  1. ffmpeg: clips up to 90 s 2.5 fps (<= 80 frames, 1280 px); long walks 3 fps, the sharpest of 2 per slot, 1024 px,
     <= MAX_FRAMES_LONG frames (0.66 fps left a 2-minute venue walk with 0 registered images)
  2. pycolmap in a SUBPROCESS (tagwerk.pipeline.sfm_colmap): SIFT + sequential matching + incremental mapping, the
     largest model wins; the whole stage has a 150 s limit and never raises (ok false + German reason instead)
  3. YOLO / YOLO-World / RelateAnything run on the SfM keyframes themselves (same images as the model, so every box
     maps exactly onto the triangulated points; the 1 fps / 20-frame vision stage would cover far less)
  4. a detection becomes a 3D observation from the points whose keypoint falls inside its box (median position, 10-90 %
     extent); observations of the same label that are close relative to the scene size are one instance
  5. relations (RelateAnything triplets) are aggregated per instance pair with German predicate labels
  6. sections: a long walk splits into several pieces (doors, fast turns, blur break the tracks). Every piece is
     kept, levelled with gravity (cameras' up axis -> +y, floor at y = 0, scale so the camera is ~1.5 m above the
     floor), split again where a camera pose jumps; the largest is also the top-level points/cameras.
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

TIME_LIMIT_S = 150  # short clips; long clips get up to MAX_TIME_LIMIT_S (time_limit_for)
MAX_TIME_LIMIT_S = 240
MAX_FRAMES_LONG, FPS_LONG, LONG_SIDE_LONG = 380, 3.0, 1024  # 1024 = SIFT's working size (portrait: 576 x 1024)
LONG_CLIP_S = 90  # above this the 80-frame plan is too sparse (< 0.9 fps) and the dense plan is used
DETECT_RESERVE_S = 30  # kept free for the detection pass after the reconstruction
MAX_FRAMES, FPS, LONG_SIDE, MAX_POINTS = 80, 2.5, 1280, 20000
MERGE_FACTOR = 0.08  # same label and closer than 8 % of the scene size = one instance
MAX_RELATIONS = 8
UNITS = "relative (SfM scale is arbitrary)"
UNITS_ALIGNED = "≈ m (Kamerahöhe 1,5 m angenommen)"
CAMERA_HEIGHT_M = 1.5
JUMP_FACTOR = 6.0  # a camera step > 6x the median step is a wrong registration (spike) or a break (split)
MIN_SECTION_FRAMES, MIN_SECTION_POINTS, MAX_SECTIONS = 4, 30, 12
DETECT_BUDGET = 60  # keyframes the detectors see in total, spread over all sections (time limit)

REL_DE = {"on": "auf", "standing on": "steht auf", "in front of": "vor", "behind": "hinter", "next to": "neben",
          "beside": "neben", "above": "über", "below": "unter", "under": "unter", "mounted on": "montiert an",
          "attached to": "an", "holding": "hält", "using": "benutzt", "blocking": "blockiert", "inside": "in",
          "in": "in", "near": "neben"}


def rel_de(rel: str) -> str:
    return REL_DE.get(rel.lower(), rel)


# ---------------------------------------------------------------- pure logic (unit tested without pycolmap)

def frame_plan(duration_s: float) -> dict:
    """Clips up to LONG_CLIP_S: 2.5 fps, fewer above 32 s so at most 80 frames, 1280 px (the rehearsed demo clips).
    Longer walks need dense, sharp frames to overlap ("dense": also the phone focal prior and relaxed mapper):
    3 fps where each frame is the sharpest of `pick` candidates, 1024 px, at most MAX_FRAMES_LONG frames."""
    if not duration_s or duration_s * FPS <= MAX_FRAMES:
        return {"fps": FPS, "pick": 1, "long_side": LONG_SIDE, "max_frames": MAX_FRAMES, "dense": False}
    if duration_s <= LONG_CLIP_S:
        return {"fps": MAX_FRAMES / duration_s, "pick": 1, "long_side": LONG_SIDE, "max_frames": MAX_FRAMES,
                "dense": False}
    return {"fps": min(FPS_LONG, MAX_FRAMES_LONG / duration_s), "pick": 2, "long_side": LONG_SIDE_LONG,
            "max_frames": MAX_FRAMES_LONG, "dense": True}


def time_limit_for(duration_s: float) -> float:
    """150 s up to LONG_CLIP_S, then 3 s more per video second (the dense plan), at most 240 s."""
    return float(min(MAX_TIME_LIMIT_S, TIME_LIMIT_S + 3 * max(0.0, (duration_s or 0) - LONG_CLIP_S)))


def camera_prior(width: int, height: int) -> str:
    """SIMPLE_RADIAL "f,cx,cy,k" for a phone main camera (~26 mm equivalent: f = 0.6 x image diagonal). COLMAP's
    default guess (1.2 x long side) is a narrow lens and makes initialisation on wide phone footage fragile."""
    return f"{0.6 * float(np.hypot(width, height)):.1f},{width / 2:g},{height / 2:g},0"


def sharpness(path: Path) -> float:
    import cv2

    g = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if g is None:
        return -1.0
    scale = 480 / max(g.shape)
    if scale < 1:
        g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def pick_sharpest(src: Path, out: Path, k: int) -> int:
    """Keep the sharpest (Laplacian variance) of every k consecutive frames of src as out/0001.jpg ... (frame n
    belongs to the slot starting at (n-1)/fps). Deterministic, so the cache can rebuild the same keyframes."""
    names = sorted(Path(src).glob("*.jpg"))
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in range(0, len(names), k):
        n += 1
        shutil.copyfile(max(names[i:i + k], key=sharpness), out / f"{n:04d}.jpg")
    return n


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


def person_pair(a: dict, b: dict) -> bool:
    """Person <-> person relations ("Person hinter Person") are most of the RelateAnything noise on walkthroughs."""
    return a.get("label") == "person" and b.get("label") == "person"


def drop_person_pairs(objs: list[dict]) -> list[dict]:
    """Remove person <-> person relations from finished objects (also for sfm.json files written before the filter)."""
    by_id = {o["id"]: o for o in objs}
    for o in objs:
        o["relations"] = [r for r in o.get("relations", []) if not person_pair(o, by_id.get(r.get("target"), {}))]
    return objs


def _relations_for(objs: list[dict], triplets: list[dict], det_inst: dict[str, str]) -> None:
    """Attach aggregated, German relations to each object (in place); person <-> person pairs are dropped."""
    by_id = {o["id"]: o for o in objs}
    agg: dict[tuple, dict] = {}
    for t in triplets:
        a, b = det_inst.get(t["s"]), det_inst.get(t["o"])
        if not a or not b or a == b or person_pair(by_id[a], by_id[b]):
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
                  elements: list[dict] | None = None, id_offset: int = 0, used: set[str] | None = None) -> list[dict]:
    """Merge 3D detections into object instances (contract `objects`); ids obj-<id_offset + n>."""
    objs, det_inst = [], {}
    used = set() if used is None else used
    groups = merge_instances(dets, scale)
    groups.sort(key=lambda g: (-len(g), g[0]["label"]))
    for n, g in enumerate(groups, 1):
        label = g[0]["label"]
        name_de, cat_de = _info(label)
        best = max(g, key=lambda d: d["conf"])
        pos = np.median([d["pos"] for d in g], axis=0)
        ext = np.median([d["ext"] for d in g], axis=0)
        ts = [d["t"] for d in g if d["t"] is not None]
        oid = f"obj-{id_offset + n}"
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


def extract_frames(video: Path, out: Path, fps: float, limit: int = MAX_FRAMES, pick: int = 1,
                   long_side: int = LONG_SIDE) -> int:
    """0001.jpg ... at `fps` (frame n is at (n-1)/fps seconds), longest side `long_side`; with pick > 1 each frame is
    the sharpest of `pick` frames decoded at pick x fps. Returns how many were written."""
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    scale = f"scale='if(gt(iw,ih),{long_side},-2)':'if(gt(iw,ih),-2,{long_side})'"
    if pick <= 1:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", f"fps={fps:.4f},{scale}",
                        "-frames:v", str(limit), "-q:v", "3", str(out / "%04d.jpg")],
                       capture_output=True, timeout=120, check=True)
        return len(list(out.glob("*.jpg")))
    cand = out.parent / f"{out.name}_candidates"
    shutil.rmtree(cand, ignore_errors=True)
    cand.mkdir(parents=True)
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", f"fps={fps * pick:.4f},{scale}",
                        "-frames:v", str(limit * pick), "-q:v", "3", str(cand / "%05d.jpg")],
                       capture_output=True, timeout=180, check=True)
        return pick_sharpest(cand, out, pick)
    finally:
        shutil.rmtree(cand, ignore_errors=True)


def run_colmap(frames: Path, work: Path, timeout_s: float, limit_s: float = TIME_LIMIT_S, dense: bool = False
               ) -> tuple[dict | None, str | None]:
    """Reconstruction in a subprocess; (arrays, None) or (None, German reason)."""
    out = work / "model.npz"
    out.unlink(missing_ok=True)
    args = [sys.executable, "-m", "tagwerk.pipeline.sfm_colmap", str(frames), str(work / "colmap"), str(out)]
    first = next(iter(sorted(Path(frames).glob("*.jpg"))), None) if dense else None
    if first is not None:
        import cv2

        img = cv2.imread(str(first))
        if img is not None:
            args.append(camera_prior(img.shape[1], img.shape[0]))
    try:
        r = subprocess.run(args,
                           capture_output=True, text=True, timeout=max(10.0, timeout_s))
    except subprocess.TimeoutExpired:
        return None, f"Zeitlimit von {limit_s:.0f} s überschritten"
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


def analyse(capture: dict, workdir: Path, elements: list[dict] | None = None, time_limit: float | None = None) -> dict:
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
        duration = probe_duration(video)
        plan = frame_plan(duration)
        fps = plan["fps"]
        time_limit = time_limit or time_limit_for(duration)
        n = extract_frames(video, frames, fps, plan["max_frames"], plan["pick"], plan["long_side"])
        if n < 8:
            return _empty(cid, "Das Video ist zu kurz oder nicht lesbar (weniger als 8 Bilder).", time.perf_counter() - t0,
                          fps=fps)
        names = sorted(p.name for p in frames.glob("*.jpg"))
        model, reason = run_colmap(frames, workdir, time_limit - DETECT_RESERVE_S - (time.perf_counter() - t0), time_limit,
                                   plan["dense"])
        sections = make_sections(model) if model else []
        if model and not sections:  # nothing passed the section filters: the largest piece as it is
            sections = split_models(model)[:1]
        det_names = detection_frames(sections) if sections else names[:: max(1, len(names) // 40)]
        det_frames, triplets = detect_frames(frames, det_names)
        res = _empty(cid, reason or "", time.perf_counter() - t0, fps=round(fps, 4), pick=plan["pick"],
                     long_side=plan["long_side"], time_limit=time_limit)
        res["frames_used"] = n
        if model is None:
            fr = [{"name": f["name"], "t": round((frame_index(f["name"]) - 1) / fps, 2), "dets": f["objects"]}
                  for f in det_frames]
            res["objects"] = objects_2d(fr, triplets, cid, elements)
            res["reason"] = reason
        else:
            res.update(build_sections(sections, det_frames, triplets, fps, cid, elements))
            res["reason"] = None
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


def ensure_frames(video: Path, dest: Path, fps: float, count: int, pick: int = 1, long_side: int = LONG_SIDE) -> None:
    """Make cache/<cid>/media/sfm/ hold the same keyframes as the worker used (same fps, same numbering), so /media can
    serve thumbs and camera images even when the reconstruction ran in another process."""
    if re.search(r"\d{4}\.jpg", " ".join(p.name for p in dest.glob("*.jpg"))) and len(list(dest.glob("*.jpg"))) >= count:
        return
    extract_frames(video, dest, fps, count, pick, long_side)


def attach_elements(res: dict, elements: list[dict]) -> dict:
    """Fill element_id of every object from the project's elements (same catalogue label / alias), in place."""
    used: set[str] = set()
    for o in res.get("objects", []):
        o["element_id"] = match_element(o["label"], elements, used)
    return res


# ---------------------------------------------------------------- sections: all pieces, gravity, pose jumps

def split_models(arrays: dict) -> list[dict]:
    """sfm_colmap's npz -> one dict per piece (largest first). Old files hold a single model without n_models."""
    if "n_models" not in arrays:
        return [arrays]
    keys = ("points", "names", "pos", "look", "up", "obs")
    return [{k: arrays[f"{k}_{i}"] for k in keys if f"{k}_{i}" in arrays} for i in range(int(arrays["n_models"]))]


def floor_normal(pts: np.ndarray, pos: np.ndarray, up0: np.ndarray, max_deg: float = 25.0, iters: int = 400) -> np.ndarray:
    """Up refined by the floor: RANSAC plane through the lowest 40 % of the points (along up0, below the cameras)
    whose normal is within max_deg of up0; the cameras' up vector alone is tilted by the phone's pitch."""
    if len(pts) < 30:
        return up0
    h = pts @ up0
    cand = pts[(h <= np.percentile(h, 40)) & (h < np.median(pos @ up0))]
    if len(cand) < 20:
        return up0
    tol = 0.01 * scene_scale(pts)
    rng = np.random.default_rng(0)
    d0 = float(np.median(cand @ up0))
    best, best_d, best_n = up0, d0, int((np.abs(cand @ up0 - d0) < tol).sum())
    cos_max = np.cos(np.radians(max_deg))
    for _ in range(iters):
        a, b, c = cand[rng.choice(len(cand), 3, replace=False)]
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            continue
        n = n / ln
        if n @ up0 < 0:
            n = -n
        if n @ up0 < cos_max:
            continue
        k = int((np.abs((cand - a) @ n) < tol).sum())
        if k > best_n:
            best, best_d, best_n = n, float(a @ n), k
    inl = cand[np.abs(cand @ best - best_d) < tol]
    if len(inl) >= 10:  # least-squares refit on the inliers
        q = inl - inl.mean(0)
        n = np.linalg.svd(q, full_matrices=False)[2][-1]
        best = n if n @ up0 > 0 else -n
    return best


def align_model(m: dict, camera_height: float = CAMERA_HEIGHT_M) -> dict:
    """Level a piece with gravity: the cameras' mean up vector becomes +y (a phone is held upright), the floor (3rd
    percentile of point heights) y = 0, the camera path centred, and the scale set so the cameras stand
    `camera_height` above the floor (heights then read roughly in metres). Without up vectors it is returned as is."""
    if "up" not in m or len(m["up"]) == 0:
        return m
    up = np.asarray(m["up"], float).mean(axis=0)
    up /= np.linalg.norm(up) or 1.0
    up = floor_normal(np.asarray(m["points"], float)[:, :3], np.asarray(m["pos"], float), up)
    look = np.asarray(m["look"], float).mean(axis=0)
    x = np.cross(up, look)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross(up, [1.0, 0.0, 0.0]) if abs(up[0]) < 0.9 else np.cross(up, [0.0, 0.0, 1.0])
    x /= np.linalg.norm(x)
    R = np.stack([x, up, np.cross(x, up)])
    c = np.asarray(m["pos"], float).mean(axis=0)
    pts = np.asarray(m["points"], float)
    h = (pts[:, :3] - c) @ R[1] if len(pts) else np.zeros(1)
    floor = float(np.percentile(h, 3))
    cam_h = float(np.median((np.asarray(m["pos"], float) - c) @ R[1])) - floor
    scale = camera_height / cam_h if cam_h > 1e-6 else 1.0
    shift = np.array([0.0, floor, 0.0])

    def tf(p):
        return ((np.asarray(p, float) - c) @ R.T - shift) * scale

    out = dict(m)
    out["points"] = np.hstack([tf(pts[:, :3]), pts[:, 3:]]) if len(pts) else pts
    out["pos"] = tf(m["pos"])
    out["look"] = np.asarray(m["look"], float) @ R.T
    out["up"] = np.tile([0.0, 1.0, 0.0], (len(m["up"]), 1))
    obs = np.asarray(m["obs"], float).copy()
    if len(obs):
        obs[:, 3:6] = tf(obs[:, 3:6])
    out["obs"] = obs
    return out


def split_at_jumps(names, pos, factor: float = JUMP_FACTOR) -> list[np.ndarray]:
    """Indices (in frame order) of the consistent stretches of a piece: a single camera far off both neighbours is
    dropped (wrong registration), a jump that stays (everything after it elsewhere) starts a new stretch."""
    order = np.argsort(np.asarray([str(n) for n in names]))
    p = np.asarray(pos, float)[order]
    if len(p) < 3:
        return [order]
    step = np.linalg.norm(np.diff(p, axis=0), axis=1)
    med = float(np.median(step)) or 1e-9
    keep = [0]
    for i in range(1, len(p) - 1):
        spike = step[i - 1] > factor * med and step[i] > factor * med and \
            np.linalg.norm(p[i + 1] - p[i - 1]) <= factor * med
        if not spike:
            keep.append(i)
    keep.append(len(p) - 1)
    parts, cur = [], [keep[0]]
    for a, b in zip(keep, keep[1:], strict=False):
        if np.linalg.norm(p[b] - p[a]) > factor * med:
            parts.append(cur)
            cur = []
        cur.append(b)
    parts.append(cur)
    return [order[np.array(x)] for x in parts]


def subset_model(m: dict, idx) -> dict:
    """The piece restricted to cameras `idx` (indices into m["names"]); points = those its cameras observe."""
    idx = np.asarray(idx, int)
    remap = {int(k): j for j, k in enumerate(idx)}
    obs = np.asarray(m["obs"], float)
    mine = obs[np.isin(obs[:, 0].astype(int), idx)] if len(obs) else obs
    if len(mine):
        mine = mine.copy()
        mine[:, 0] = [remap[int(k)] for k in mine[:, 0]]
    pts = np.asarray(m["points"], float)
    if len(mine) and mine.shape[1] > 6:
        pts = pts[np.unique(mine[:, 6].astype(int))]
    out = {"points": pts, "names": np.asarray(m["names"])[idx], "pos": np.asarray(m["pos"])[idx],
           "look": np.asarray(m["look"])[idx], "obs": mine}
    if "up" in m:
        out["up"] = np.asarray(m["up"])[idx]
    return out


def make_sections(arrays: dict) -> list[dict]:
    """All usable pieces, levelled and cut at pose jumps, largest first (at most MAX_SECTIONS)."""
    out = []
    for m in split_models(arrays):
        for idx in split_at_jumps(m["names"], m["pos"]):
            sub = subset_model(m, idx)
            if len(sub["names"]) >= MIN_SECTION_FRAMES and len(sub["points"]) >= MIN_SECTION_POINTS:
                out.append(align_model(sub))
    out.sort(key=lambda m: -len(m["names"]))
    return out[:MAX_SECTIONS]


def detection_frames(models: list[dict], budget: int = DETECT_BUDGET) -> list[str]:
    """Keyframes for the detectors, spread over all sections in proportion to their size (at least 3 each)."""
    total = sum(len(m["names"]) for m in models) or 1
    out: list[str] = []
    for m in models:
        names = sorted(str(n) for n in m["names"])
        k = min(len(names), max(3, round(budget * len(names) / total)))
        out += [names[int(i)] for i in np.linspace(0, len(names) - 1, k)]
    return list(dict.fromkeys(out))


def build_sections(models: list[dict], det_frames: list[dict], triplets: list[dict], fps: float, cid: str,
                   elements: list[dict] | None = None) -> dict:
    """sfm.json fields for a reconstruction of one or more pieces: `sections` (largest first, each with its own
    points/cameras), all objects with their `section` and unique ids, top-level points/cameras = section 0."""
    models = sorted(models, key=lambda m: -len(m["names"]))
    secs, objs, used = [], [], set()
    for k, m in enumerate(models):
        pts = np.asarray(m["points"], float)
        cams = cameras_json(m["names"], m["pos"], m["look"], fps, cid)
        mine = build_objects(lift_detections(det_frames, m, fps), triplets, scene_scale(pts), cid, elements,
                             id_offset=len(objs), used=used)
        for o in mine:
            o["section"] = k
        objs += mine
        ts = [c["t"] for c in cams]
        secs.append({"id": k, "t_start": min(ts), "t_end": max(ts), "frames_registered": len(cams),
                     "points": downsample_points(pts, MAX_POINTS), "cameras": cams, "objects": len(mine)})
    aligned = all("up" in m for m in models)
    return {"ok": bool(secs), "frames_registered": sum(s["frames_registered"] for s in secs),
            "points": secs[0]["points"] if secs else [], "cameras": secs[0]["cameras"] if secs else [],
            "objects": objs, "sections": secs, "gravity_aligned": aligned, "units": UNITS_ALIGNED if aligned else UNITS}
