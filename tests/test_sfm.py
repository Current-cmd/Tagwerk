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
