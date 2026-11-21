"""pycolmap worker, run as a SUBPROCESS by tagwerk.pipeline.sfm so a hung or crashing reconstruction can be killed
(150 s limit) without touching the GPU worker or the event loop:

    python -m tagwerk.pipeline.sfm_colmap <frames_dir> <workdir> <out.npz> [f,cx,cy,k camera prior]

SIFT (1024 px, CPU) + sequential matching (overlap 10) + incremental mapping. With a camera prior (long walks, the
dense frame plan of sfm.py): overlap 15 and relaxed init/registration thresholds (plain walls, blur: the defaults
split a venue walk into many tiny models). The largest model is written to an npz:
points (N,6: x y z r g b), cams (frame name, position, look vector), obs (per registered image the 2D keypoints that
have a triangulated 3D point: image index, x, y, X, Y, Z). Exit code 3 = no model."""
import sys
import time
from pathlib import Path

import numpy as np


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
    if not recs:
        return 3
    rec = max(recs.values(), key=lambda r: r.num_reg_images())
    if rec.num_reg_images() < 3 or rec.num_points3D() < 30:
        return 3
    pts = np.array([[*p.xyz, *p.color] for p in rec.points3D.values()], np.float32)
    names, pos, look, obs = [], [], [], []
    for img in sorted(rec.images.values(), key=lambda i: i.name):
        if not img.has_pose:
            continue
        k = len(names)
        names.append(img.name)
        pos.append(np.asarray(img.projection_center()))
        look.append(np.asarray(img.cam_from_world().rotation.matrix()).T @ np.array([0.0, 0.0, 1.0]))
        for p2 in img.points2D:
            if p2.has_point3D():
                obs.append([k, *p2.xy, *rec.points3D[p2.point3D_id].xyz])
    np.savez_compressed(out, points=pts, names=np.array(names), pos=np.array(pos, np.float32),
                        look=np.array(look, np.float32), obs=np.array(obs, np.float32).reshape(-1, 6))
    return 0


if __name__ == "__main__":
    t0 = time.time()
    code = main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else None)
    print(f"sfm_colmap done in {time.time() - t0:.1f}s code={code}", flush=True)
    sys.exit(code)
