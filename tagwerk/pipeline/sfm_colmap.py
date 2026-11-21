"""pycolmap worker, run as a SUBPROCESS by tagwerk.pipeline.sfm so a hung or crashing reconstruction can be killed
(150 s limit) without touching the GPU worker or the event loop:

    python -m tagwerk.pipeline.sfm_colmap <frames_dir> <workdir> <out.npz>

SIFT (1024 px, CPU) + sequential matching (overlap 10) + incremental mapping; the largest model is written to an npz:
points (N,6: x y z r g b), cams (frame name, position, look vector), obs (per registered image the 2D keypoints that
have a triangulated 3D point: image index, x, y, X, Y, Z). Exit code 3 = no model."""
import sys
import time
from pathlib import Path

import numpy as np


def main(frames: Path, work: Path, out: Path) -> int:
    import pycolmap

    work.mkdir(parents=True, exist_ok=True)
    db = work / "db.db"
    db.unlink(missing_ok=True)
    fo = pycolmap.FeatureExtractionOptions()
    fo.max_image_size = 1024
    fo.sift.max_num_features = 4000
    pycolmap.extract_features(db, frames, extraction_options=fo, camera_mode=pycolmap.CameraMode.SINGLE)
    pair = pycolmap.SequentialPairingOptions()
    pair.overlap = 10
    pair.loop_detection = False  # vocabulary-free: no vocab tree download, no extra cost
    pycolmap.match_sequential(db, matching_options=pycolmap.FeatureMatchingOptions(), pairing_options=pair)
    models = work / "models"
    models.mkdir(exist_ok=True)
    recs = pycolmap.incremental_mapping(db, frames, models)
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
    code = main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    print(f"sfm_colmap done in {time.time() - t0:.1f}s code={code}", flush=True)
    sys.exit(code)
