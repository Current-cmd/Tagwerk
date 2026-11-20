"""Vision stage: stub path, geometry, NMS and frame sampling run on CPU without models."""
import pytest

from tagwerk.contracts import validate
from tagwerk.pipeline import vision


def _obj(oid, bbox, label="x", conf=0.9):
    return {"obj_id": oid, "label": label, "bbox": bbox, "conf": conf, "marker_id": None, "source": "coco"}


def test_stub_when_ml_missing(monkeypatch):
    monkeypatch.setattr(vision, "ml_available", lambda: False)
    out = vision.analyse({"capture_id": "cap-x", "media": []}, {"frames_dir": "/nonexistent"})
    assert out["capture_id"] == "cap-x"
    validate("vision", out)


def test_geometric_relations():
    table = _obj("table", [100, 300, 500, 500])
    cup = _obj("cup", [250, 240, 300, 310])        # bottom edge on the table top
    lamp = _obj("lamp", [200, 0, 300, 100])        # well above the table
    chair = _obj("chair", [520, 320, 650, 500])    # beside the table
    rels = {(r["s"], r["rel"], r["o"]) for r in vision.geometric_relations([table, cup, lamp, chair], topk=50)}
    assert ("cup", "on", "table") in rels
    assert ("lamp", "above", "table") in rels
    assert ("table", "below", "lamp") in rels
    assert ("chair", "next to", "table") in rels
    assert all(r["source"] == "geometry" for r in vision.geometric_relations([table, cup]))
    frame = {"t": None, "media_path": "p.jpg", "objects": [table, cup],
             "triplets": vision.geometric_relations([table, cup])}
    validate("vision", {"capture_id": "c", "frames": [frame]})


def test_class_aware_nms():
    dets = [
        {"label": "person", "bbox": [0, 0, 100, 100], "conf": 0.9, "source": "coco"},
        {"label": "person", "bbox": [5, 5, 100, 100], "conf": 0.8, "source": "coco"},   # suppressed
        {"label": "door", "bbox": [5, 5, 100, 100], "conf": 0.5, "source": "world"},    # other class kept
        {"label": "person", "bbox": [300, 300, 400, 400], "conf": 0.7, "source": "coco"},
    ]
    kept = vision.class_aware_nms(dets)
    assert [(d["label"], d["conf"]) for d in kept] == [("person", 0.9), ("person", 0.7), ("door", 0.5)]


def test_collect_frames_sampling(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    for i in range(1, 31):
        (frames / f"{i:04d}.jpg").write_bytes(b"")
    cap = {"capture_id": "c", "media": [{"type": "photo", "path": "/p/a.jpg"}, {"type": "video", "path": "v.mp4"}]}
    items = vision.collect_frames(cap, {"frames_dir": str(frames)})
    assert len(items) == vision.MAX_FRAMES
    assert items[0] == {"t": 0.0, "path": str(frames / "0001.jpg"), "media_path": "frames/0001.jpg"}
    assert items[-1]["t"] is None and items[-1]["media_path"] == "/p/a.jpg"


def test_aruco_markers(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    img = np.full((400, 600, 3), 255, np.uint8)
    img[100:300, 100:300] = cv2.cvtColor(cv2.aruco.generateImageMarker(d, 3, 200), cv2.COLOR_GRAY2BGR)
    det = cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters())
    found = vision._detect_markers(img, det)
    assert [(m["marker_id"], m["source"], m["conf"]) for m in found] == [(3, "marker", 1.0)]
