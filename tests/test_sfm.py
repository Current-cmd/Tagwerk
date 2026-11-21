"""Scan 3D: lifting detections into the SfM model, merging instances, relations, report (no pycolmap needed)."""
import numpy as np
import pytest

from tagwerk.pipeline import sfm

CAM = {"t": 0.0, "position": [0, 0, 0], "look": [0, 0, 1], "frame": "/media/c/sfm/0001.jpg"}


def det(label, pos, frame="0001.jpg", t=0.0, conf=0.8, bbox=(10, 10, 50, 50), oid="f0_o1", ext=(0.2, 0.2, 0.2), n=8):
    return {"label": label, "pos": list(pos), "ext": list(ext), "n": n, "frame": frame, "t": t, "conf": conf,
            "bbox": list(bbox), "obj_id": oid}


def test_lift_box_takes_points_inside_the_box_median_and_extent():
    xy = np.array([[20, 20], [30, 30], [40, 40], [45, 25], [200, 200]], float)
    xyz = np.array([[1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4], [90, 90, 90]], float)
    r = sfm.lift_box((10, 10, 50, 50), xy, xyz)
    assert r["n"] == 4 and r["pos"] == pytest.approx([2.5, 2.5, 2.5]) and max(r["ext"]) < 5  # the far point is out


def test_lift_box_grows_once_and_then_gives_up():
    xy = np.array([[52, 30], [53, 31], [54, 32]], float)  # just right of the box: only the grown box catches them
    xyz = np.array([[1, 1, 1], [1, 1, 1.1], [1, 1.1, 1]], float)
    assert sfm.lift_box((10, 10, 50, 50), xy, xyz)["n"] == 3
    assert sfm.lift_box((10, 10, 50, 50), xy[:2], xyz[:2]) is None  # fewer than 3 points
    assert sfm.lift_box((10, 10, 50, 50), np.zeros((0, 2)), np.zeros((0, 3))) is None


def test_scene_scale_ignores_outliers():
    rng = np.random.default_rng(1)
    pts = np.vstack([rng.uniform(0, 10, (500, 3)), [[1000, 1000, 1000]]])
    assert 8 < sfm.scene_scale(pts) < 25


def test_merge_by_label_and_distance_relative_to_scene():
    dets = [det("door", (0, 0, 0)), det("door", (0.2, 0, 0), conf=0.9), det("door", (5, 0, 0)),
            det("wall", (0.1, 0, 0))]
    groups = sfm.merge_instances(dets, scale=10.0)
    assert sorted((g[0]["label"], len(g)) for g in groups) == [("door", 1), ("door", 2), ("wall", 1)]
    assert len(sfm.merge_instances(dets, scale=100.0)) == 2  # larger scene: 5 units is "close": all doors merge


def test_relations_aggregate_with_german_labels_and_skip_self_pairs():
    dets = [det("socket", (0, 0, 0), oid="a"), det("socket", (0.1, 0, 0), oid="b", t=1.0),
            det("wall", (0, 0, 0.5), oid="c")]
    objs = sfm.build_objects(dets, [
        {"s": "a", "rel": "on", "o": "c", "score": 0.5, "source": "model"},
        {"s": "b", "rel": "on", "o": "c", "score": 0.7, "source": "model"},
        {"s": "a", "rel": "next to", "o": "b", "score": 0.9, "source": "geometry"}], scale=10.0, cid="c1")
    sock = next(o for o in objs if o["label"] == "socket")
    rels = {(r["rel"], r["rel_de"], r["target_name"]): r for r in sock["relations"]}
    r = rels[("on", "auf", "Wand")]
    assert r["count"] == 2 and r["score"] == 0.7 and r["source"] == "model" and r["target"].startswith("obj-")
    assert all(x["target"] != sock["id"] for x in sock["relations"])  # merged instance never relates to itself


@pytest.mark.parametrize("rel,de", [("on", "auf"), ("under", "unter"), ("below", "unter"), ("above", "über"),
                                    ("next to", "neben"), ("beside", "neben"), ("in front of", "vor"),
                                    ("behind", "hinter"), ("attached to", "an"), ("holding", "hält"),
                                    ("standing on", "steht auf"), ("odd", "odd")])
def test_german_predicates(rel, de):
    assert sfm.rel_de(rel) == de


def test_build_objects_fields_names_thumb_and_elements():
    elements = [{"id": "S-SOCKET-1", "name_de": "Steckdose 1", "aliases": ["socket", "Steckdose"]},
                {"id": "S-SOCKET-2", "name_de": "Steckdose 2", "aliases": ["socket", "Steckdose"]}]
    dets = [det("socket", (0, 0, 0), frame="0004.jpg", t=3.0, conf=0.9, bbox=(1, 2, 3, 4), oid="a"),
            det("socket", (0.1, 0, 0), frame="0005.jpg", t=3.4, oid="b"), det("socket", (9, 0, 0), oid="c"),
            det("socket", (-9, 0, 0), oid="d"), det("tv", (0, 5, 0), oid="e")]
    objs = sfm.build_objects(dets, [], scale=10.0, cid="c1", elements=elements)
    socks = [o for o in objs if o["label"] == "socket"]
    assert len(socks) == 3 and [o["element_id"] for o in socks].count(None) == 1  # 2 elements for 3 instances
    first = max(socks, key=lambda o: o["detections"])
    assert first["detections"] == 2 and first["first_t"] == 3.0 and first["last_t"] == 3.4
    assert first["thumb"] == "/media/c1/sfm/0004.jpg" and first["bbox_in_thumb"] == [1, 2, 3, 4]
    assert first["name_de"] == "Steckdose" and first["category_de"] == "Technik (TGA)" and first["conf"] == 0.85
    tv = next(o for o in objs if o["label"] == "tv")
    assert tv["name_de"] == "Bildschirm" and tv["element_id"] is None and len(tv["position"]) == 3


def test_objects_2d_without_reconstruction():
    frames = [{"name": "0001.jpg", "t": 0.0, "dets": [{"obj_id": "a", "label": "chair", "bbox": [0, 0, 5, 5], "conf": 0.6},
                                                      {"obj_id": "b", "label": "dining table", "bbox": [9, 0, 15, 5],
                                                       "conf": 0.7},
                                                      {"obj_id": "d", "label": "chair", "bbox": [20, 0, 25, 5], "conf": 0.7}]},
              {"name": "0002.jpg", "t": 0.4, "dets": [{"obj_id": "c", "label": "chair", "bbox": [0, 0, 5, 5], "conf": 0.5}]}]
    objs = sfm.objects_2d(frames, [{"s": "a", "rel": "next to", "o": "b", "score": 0.5, "source": "model"}], "c1")
    assert len(objs) == 3 and all(o["position"] is None and o["extent"] is None for o in objs)  # 2 chairs + 1 table
    chair = next(o for o in objs if o["label"] == "chair")
    assert chair["relations"][0]["rel_de"] == "neben" and chair["relations"][0]["target_name"] == "Tisch"


def test_points_downsample_and_cameras():
    pts = np.column_stack([np.arange(50000), np.zeros(50000), np.zeros(50000), np.full((50000, 3), 128)]).astype(float)
    out = sfm.downsample_points(pts, 20000)
    assert len(out) <= 20000 and len(out[0]) == 6 and all(isinstance(v, (int, float)) for v in out[0])
    cams = sfm.cameras_json(["0001.jpg", "0003.jpg"], np.zeros((2, 3)), np.tile([0, 0, 1.0], (2, 1)), fps=2.5, cid="c1")
    assert cams[1] == {"t": 0.8, "position": [0.0, 0.0, 0.0], "look": [0.0, 0.0, 1.0], "frame": "/media/c1/sfm/0003.jpg"}


def test_frame_plan_short_clips_unchanged_long_clips_dense_with_sharp_pick():
    """Short demo clips keep 2.5 fps / 1280 px. A 2-minute venue walk at 0.66 fps (80 frames) left too little overlap
    (0 registered): long clips get 3 fps (sharpest of 2 per slot) at 960 px, capped at MAX_FRAMES_LONG frames."""
    assert sfm.frame_plan(20.0) == {"fps": 2.5, "pick": 1, "long_side": 1280, "max_frames": 80, "dense": False}
    assert sfm.frame_plan(0)["fps"] == 2.5 and sfm.frame_plan(30.0)["pick"] == 1
    # up to LONG_CLIP_S the rehearsed plan (80 frames) stays: user_walk (70 s) registers 30 frames with it and times
    # out with the dense plan
    assert sfm.frame_plan(70.0) == {"fps": pytest.approx(80 / 70), "pick": 1, "long_side": 1280, "max_frames": 80,
                                    "dense": False}
    p = sfm.frame_plan(121.3)
    assert p["fps"] == 3.0 and p["pick"] == 2 and p["long_side"] == 1024 and 121.3 * 3 <= p["max_frames"] and p["dense"]
    p = sfm.frame_plan(600.0)
    assert p["fps"] == pytest.approx(sfm.MAX_FRAMES_LONG / 600.0) and p["max_frames"] == sfm.MAX_FRAMES_LONG


def test_time_limit_scales_with_clip_length():
    assert sfm.time_limit_for(0) == sfm.TIME_LIMIT_S == 150 and sfm.time_limit_for(70.0) == 150
    assert sfm.time_limit_for(121.3) == sfm.MAX_TIME_LIMIT_S == 240 and 150 < sfm.time_limit_for(100.0) < 240


def test_pick_sharpest_keeps_the_sharper_frame_of_each_slot(tmp_path):
    cv2 = pytest.importorskip("cv2")
    rng = np.random.default_rng(0)
    sharp = (rng.random((90, 160)) * 255).astype(np.uint8)
    blur = cv2.GaussianBlur(sharp, (15, 15), 5)
    src = tmp_path / "all"
    src.mkdir()
    for i, img in enumerate([blur, sharp, sharp, blur, blur], 1):  # slots of 2: (blur, sharp) (sharp, blur) (blur)
        cv2.imwrite(str(src / f"{i:05d}.jpg"), img)
    out = tmp_path / "fr"
    assert sfm.pick_sharpest(src, out, 2) == 3
    got = [cv2.imread(str(out / f"{i:04d}.jpg"), cv2.IMREAD_GRAYSCALE) for i in (1, 2, 3)]
    assert [round(float(cv2.Laplacian(g, cv2.CV_64F).var())) > 1000 for g in got] == [True, True, False]


def test_camera_prior_is_a_phone_main_lens():
    f, cx, cy, k = (float(x) for x in sfm.camera_prior(960, 1706).split(","))
    assert (cx, cy, k) == (480.0, 853.0, 0.0) and 1100 < f < 1250  # ~26 mm equivalent, not COLMAP's 1.2 x long side


def test_analyse_without_video_or_missing_file_is_a_german_failure_not_an_exception(tmp_path):
    r = sfm.analyse({"capture_id": "x", "media": []}, tmp_path)
    assert r["ok"] is False and "Video" in r["reason"] and r["objects"] == [] and r["points"] == []
    r = sfm.analyse({"capture_id": "x", "media": [{"type": "video", "path": str(tmp_path / "nope.mp4")}]}, tmp_path)
    assert r["ok"] is False and r["reason"]


def test_pycolmap_api_we_use_exists():
    pycolmap = pytest.importorskip("pycolmap")
    for name in ("extract_features", "match_sequential", "incremental_mapping", "SequentialPairingOptions",
                 "FeatureExtractionOptions", "FeatureMatchingOptions", "CameraMode", "IncrementalPipelineOptions",
                 "ImageReaderOptions"):
        assert hasattr(pycolmap, name), name
    o = pycolmap.IncrementalPipelineOptions()
    for name in ("min_num_matches", "ba_refine_principal_point"):
        assert hasattr(o, name), name
    for name in ("init_min_num_inliers", "abs_pose_min_num_inliers", "abs_pose_min_inlier_ratio", "init_min_tri_angle"):
        assert hasattr(o.mapper, name), name
    r = pycolmap.ImageReaderOptions()
    assert hasattr(r, "camera_params") and hasattr(r, "camera_model")


# ---------------------------------------------------------------- all pieces, gravity, pose jumps (sections)

def _rot(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _model(n=10, tilt=35.0, offset=(5.0, -2.0, 3.0), scale=0.37, start=1):
    """A walk along +x at camera height 1.5 above a floor at y=0 (gravity +y), then tilted/shifted/scaled like an
    arbitrary COLMAP frame. obs = [image, x, y, X, Y, Z, point index]."""
    R = _rot("x", tilt) @ _rot("y", 20.0)
    off = np.array(offset)
    tf = lambda p: (np.asarray(p, float) @ R.T) * scale + off  # noqa: E731
    floor = np.array([[x, 0.0, z] for x in np.linspace(0, 9, 30) for z in np.linspace(-2, 2, 10)])
    wall = np.array([[x, y, 2.0] for x in np.linspace(0, 9, 30) for y in np.linspace(0, 2.6, 8)])
    pts_w = np.vstack([floor, wall])
    pos_w = np.array([[i * 0.9, 1.5, 0.0] for i in range(n)])
    up_w, look_w = np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    pts = np.hstack([tf(pts_w), np.full((len(pts_w), 3), 128.0)])
    obs = np.array([[k, 10.0, 10.0, *tf(pts_w[j]), j] for k in range(n) for j in range(0, len(pts_w), 7)])
    return {"points": pts, "names": np.array([f"{start + i:04d}.jpg" for i in range(n)]), "pos": tf(pos_w),
            "look": np.tile(look_w @ R.T, (n, 1)), "up": np.tile(up_w @ R.T, (n, 1)), "obs": obs}


def test_split_models_reads_all_pieces_and_the_old_single_model_format():
    m0, m1 = _model(start=1), _model(n=6, start=40)
    old = {k: v for k, v in m0.items()}
    assert [len(m["names"]) for m in sfm.split_models(old)] == [10]
    new = {"n_models": np.array(2), **{f"{k}_{i}": v for i, m in enumerate((m0, m1)) for k, v in m.items()}}
    got = sfm.split_models(new)
    assert [len(m["names"]) for m in got] == [10, 6] and str(got[1]["names"][0]) == "0040.jpg"


def test_align_puts_the_floor_level_at_zero_and_cameras_at_1_5_m():
    a = sfm.align_model(_model())
    pts, pos = a["points"][:, :3], a["pos"]
    assert abs(np.percentile(pts[:, 1], 3)) < 0.05  # floor at y = 0
    assert np.allclose(pos[:, 1], 1.5, atol=0.05) and np.ptp(pos[:, 1]) < 0.05  # cameras level, at 1.5
    assert np.allclose(a["up"], [0, 1, 0], atol=1e-6) and np.allclose(a["look"][:, 1], 0, atol=1e-6)
    assert abs(np.percentile(pts[:, 1], 97) - 2.6) < 0.15  # the wall top stays ~2.6 m: heights are real
    k = int(a["obs"][0, 6])
    assert np.allclose(a["obs"][0, 3:6], pts[k], atol=1e-6)  # observations moved with their points
    assert np.isclose(np.linalg.norm(pos[1] - pos[0]), 0.9, atol=0.01)  # metric-ish scale from camera height


def test_pose_jumps_split_a_piece_and_single_spikes_are_dropped():
    pos = np.array([[i * 0.1, 0, 0] for i in range(12)], float)
    pos[5] += [3.0, 0, 0]  # one frame registered far away: spike
    pos[8:] += [5.0, 0, 0]  # teleport: everything after frame 8 sits elsewhere
    names = np.array([f"{i + 1:04d}.jpg" for i in range(12)])
    parts = sfm.split_at_jumps(names, pos)
    assert [list(p) for p in parts] == [[0, 1, 2, 3, 4, 6, 7], [8, 9, 10, 11]]


def test_sections_from_all_pieces_unique_object_ids_and_largest_on_top(monkeypatch):
    models = [sfm.align_model(_model(n=6, start=40)), sfm.align_model(_model(n=10, start=1))]
    dets = [{"name": "0003.jpg", "objects": [{"obj_id": "0003_o1", "label": "door", "conf": 0.9, "bbox": [0, 0, 20, 20],
                                              "source": "world"}]},
            {"name": "0042.jpg", "objects": [{"obj_id": "0042_o1", "label": "door", "conf": 0.8, "bbox": [0, 0, 20, 20],
                                              "source": "world"}]}]
    res = sfm.build_sections(models, dets, [], fps=3.0, cid="c1")
    secs = res["sections"]
    assert [s["frames_registered"] for s in secs] == [10, 6]  # largest first
    assert secs[0]["t_start"] == 0.0 and secs[1]["t_start"] == round(39 / 3.0, 2)
    assert res["points"] == secs[0]["points"] and res["cameras"] == secs[0]["cameras"]
    assert res["frames_registered"] == 16 and res["gravity_aligned"] is True
    ids = [o["id"] for o in res["objects"]]
    assert len(ids) == len(set(ids)) == 2 and {o["section"] for o in res["objects"]} == {0, 1}


def test_detection_frames_are_capped_and_spread_over_all_pieces():
    models = [_model(n=40, start=1), _model(n=20, start=100), _model(n=5, start=200)]
    names = sfm.detection_frames(models, budget=30)
    assert len(names) <= 30 + 3 and any(n.startswith("02") for n in names) and any(n.startswith("01") for n in names)


def test_floor_plane_corrects_the_pitch_of_a_phone_held_slightly_down():
    """Walking, the phone points ~12° down: the cameras' up vector is tilted, the floor is not. The floor plane
    (RANSAC on the lowest points near the camera-up estimate) wins, so floor and camera path come out level."""
    m = _model(tilt=0.0)
    pitch = _rot("x", 12.0)
    m["up"] = m["up"] @ pitch.T  # biased up vectors, geometry unchanged
    a = sfm.align_model(m)
    floor = a["points"][:300, 1]  # the first 300 points of _model are the floor
    assert np.ptp(floor) < 0.05 and np.ptp(a["pos"][:, 1]) < 0.05
