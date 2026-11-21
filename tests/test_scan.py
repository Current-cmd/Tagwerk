from datetime import date

from tagwerk.pipeline.scan import inventory, seed_from_scan
from tagwerk.project import Project


def _vis():
    def obj(i, label, conf=0.8, src="world"):
        return {"obj_id": f"o{i}", "label": label, "bbox": [0, 0, 10, 10], "conf": conf, "marker_id": None,
                "source": src}
    frames = []
    for t in range(4):
        objs = [obj(1, "wall"), obj(2, "wall"), obj(3, "window"), obj(4, "person", src="coco"),
                obj(5, "scaffolding"), obj(6, "ladder", conf=0.1)]
        if t == 2:
            objs.append(obj(7, "wall"))
        frames.append({"t": float(t), "media_path": f"f/{t}.jpg", "objects": objs, "triplets": []})
    return {"capture_id": "scan-x", "frames": frames}


def test_inventory_categorises_and_counts():
    inv = inventory(_vis())
    by = {i["label"]: i for i in inv["items"]}
    assert by["wall"]["instances"] == 3 and by["wall"]["category"] == "structure"
    assert by["window"]["category"] == "openings" and by["scaffolding"]["category"] == "equipment"
    assert "ladder" not in by  # below confidence
    assert inv["people_max"] == 1 and inv["element_count"] == 4  # 3 walls + 1 window


def test_seed_from_scan_loads_and_detections_propose(tmp_path, monkeypatch):
    out = tmp_path / "site"
    res = seed_from_scan(inventory(_vis()), out, "site", date(2026, 11, 26))
    assert res["elements"] == 4 and res["activities"] == 2
    p = Project.from_seed(out)
    assert len(p.elements) == 4 and p.meta["data_date"] == "2026-11-26"

    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    import tagwerk.pipeline.context as context
    from tagwerk.config import get_settings
    from tagwerk.pipeline import structure

    get_settings.cache_clear()
    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": None, "precipMm": None, "windKmh": None,
                                                              "source": "test"})
    cap = {"capture_id": "c1", "zone_id": "Z-SITE", "note": None}
    tr = {"capture_id": "c1", "lang": "de", "segments": []}
    vis = _vis()
    s = structure.structure(cap, tr, vis, context.build_context(cap, vis, p), p)
    walls = [w for w in s["work_done"] if w["element_ids"][0].startswith("S-WALL")]
    assert len(walls) == 3 and all(w["evidence"] == "vision" for w in walls)
    ch = p.apply_structured({"capture_id": "c1", "zone_id": "Z-SITE", "ts": "2026-11-26T09:00:00Z"}, s)
    assert ch and all(c["action"] == "proposed" for c in ch)
