"""pycolmap worker, run as a SUBPROCESS by tagwerk.pipeline.sfm so a hung or crashing reconstruction can be killed
(150 s limit) without touching the GPU worker or the event loop:

    python -m tagwerk.pipeline.sfm_colmap <frames_dir> <workdir> <out.npz> [f,cx,cy,k camera prior]

SIFT (1024 px, CPU) + sequential matching (overlap 10) + incremental mapping. With a camera prior (long walks, the
dense frame plan of sfm.py): overlap 15 and relaxed init/registration thresholds (plain walls, blur). Every piece with
>= 3 images and >= 30 points (largest first, at most 16) goes into an npz: n_models and <key>_<i> (the largest also
under the plain keys) with points (N,6: x y z r g b), names, pos, look, up (camera -y in world) and obs (image index,
x, y, X, Y, Z, point index). Exit code 3 = no model."""
import sys
import time
from pathlib import Path

import numpy as np

MAX_MODELS = 16


def _arrays(rec) -> dict:
    """One reconstruction: points (N,6 xyz rgb), names, pos, look, up (camera -y in world: up for an upright phone),
    obs (image index, x, y, X, Y, Z, point index)."""
    ids = list(rec.points3D.keys())
    pidx = {pid: j for j, pid in enumerate(ids)}
    pts = np.array([[*rec.points3D[p].xyz, *rec.points3D[p].color] for p in ids], np.float32)
    names, pos, look, up, obs = [], [], [], [], []
    for img in sorted(rec.images.values(), key=lambda i: i.name):
        if not img.has_pose:
            continue
        k = len(names)
        names.append(img.name)
        pos.append(np.asarray(img.projection_center()))
        rt = np.asarray(img.cam_from_world().rotation.matrix()).T
        look.append(rt @ np.array([0.0, 0.0, 1.0]))
        up.append(rt @ np.array([0.0, -1.0, 0.0]))
        for p2 in img.points2D:
            if p2.has_point3D():
                obs.append([k, *p2.xy, *rec.points3D[p2.point3D_id].xyz, pidx[p2.point3D_id]])
    return {"points": pts, "names": np.array(names), "pos": np.array(pos, np.float32),
            "look": np.array(look, np.float32), "up": np.array(up, np.float32),
            "obs": np.array(obs, np.float32).reshape(-1, 7)}


def main(frames: Path, work: Path, out: Path, prior: str | None = None) -> int:
    import pycolmap

    work.mkdir(parents=True, exist_ok=True)
    db = work / "db.db"
    db.unlink(missing_ok=True)
    fo = pycolmap.FeatureExtractionOptions()
    fo.max_image_size = 1024
    fo.sift.max_num_features = 4000
    ro = pycolmap.ImageReaderOptions()
    ro.camera_model = "SIMPLE_RADIAL"  # COLMAP's default model
    if prior:
        ro.camera_params = prior
    pycolmap.extract_features(db, frames, extraction_options=fo, camera_mode=pycolmap.CameraMode.SINGLE,
                              reader_options=ro)
    pair = pycolmap.SequentialPairingOptions()
    pair.overlap = 15 if prior else 10
    pair.loop_detection = False  # vocabulary-free: no vocab tree download, no extra cost
    pycolmap.match_sequential(db, matching_options=pycolmap.FeatureMatchingOptions(), pairing_options=pair)
    models = work / "models"
    models.mkdir(exist_ok=True)
    mo = pycolmap.IncrementalPipelineOptions()
    if prior:
        mo.min_num_matches = 10
        mo.mapper.init_min_num_inliers = 40
        mo.mapper.abs_pose_min_num_inliers = 15
        mo.mapper.abs_pose_min_inlier_ratio = 0.15
        mo.mapper.init_min_tri_angle = 4
        mo.ba_refine_principal_point = False
    recs = pycolmap.incremental_mapping(db, frames, models, options=mo)
    good = sorted((r for r in recs.values() if r.num_reg_images() >= 3 and r.num_points3D() >= 30),
                  key=lambda r: -r.num_reg_images())[:MAX_MODELS]
    if not good:
        return 3
    arrays = {"n_models": np.array(len(good))}
    for i, rec in enumerate(good):
        for k, v in _arrays(rec).items():
            arrays[f"{k}_{i}"] = v
            if i == 0:
                arrays[k] = v  # the largest also under the old keys (older readers)
    np.savez_compressed(out, **arrays)
    return 0


if __name__ == "__main__":
    t0 = time.time()
    code = main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else None)
    print(f"sfm_colmap done in {time.time() - t0:.1f}s code={code}", flush=True)
    sys.exit(code)
