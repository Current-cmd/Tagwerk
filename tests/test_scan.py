import json
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


def test_speech_terms_become_elements():
    from tagwerk.pipeline.scan import speech_terms

    tr = {"segments": [{"start": 3.0, "end": 9.0, "text": "Das ist die dünne Betonfassade, dahinter ist der "
                                                           "Mineralschaum eingefüllt worden."},
                       {"start": 20.0, "end": 25.0, "text": "Die Holzrahmen-Elemente wurden vorgefertigt, das ist "
                                                            "der Endzustand im Stockwerk."}]}
    terms = {t["name_de"]: t for t in speech_terms(tr)}
    assert {"Betonfassade", "Mineralschaum", "Holzrahmen-Elemente"} <= set(terms)
    assert "Endzustand" not in terms and "Stockwerk" not in terms
    assert terms["Betonfassade"]["category"] == "finishes" and terms["Betonfassade"]["sources"] == ["speech"]
    inv = inventory({"capture_id": "x", "frames": []}, transcript=tr)
    assert inv["element_count"] == 3 and inv["transcript"]


def _scan_client(tmp_path, monkeypatch, vision):
    from fastapi.testclient import TestClient

    import tagwerk.graph.store as store
    import tagwerk.pipeline.runner as runner
    import tagwerk.project as project_mod
    import tagwerk.state as state
    from tagwerk.config import get_settings

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("NEO4J_URI", "")
    monkeypatch.setenv("GPU_WORKER_URL", "")
    monkeypatch.setenv("ALLOW_PROJECT_CREATE", "1")  # these tests create projects
    get_settings.cache_clear()
    store._store = None
    state.reset()
    monkeypatch.setattr(project_mod, "SEED_DIR", tmp_path / "seed")
    (tmp_path / "seed").mkdir()

    async def fake_stage(stage, capture, derived, replay=False):
        if stage == "vision":
            return {**vision, "capture_id": capture["capture_id"]}
        return {"capture_id": capture["capture_id"], "lang": "de", "segments": []}

    monkeypatch.setattr(runner, "_gpu_stage", fake_stage)
    from tagwerk.api.app import app

    return TestClient(app)


def test_scan_without_building_elements_creates_no_project(tmp_path, monkeypatch):
    """A scan that only saw people/equipment must not write a project with no activities (its dashboard crashes)."""
    vis = {"frames": [{"t": float(t), "media_path": f"f/{t}.jpg", "triplets": [], "objects": [
        {"obj_id": "o1", "label": "person", "bbox": [0, 0, 5, 5], "conf": 0.9, "marker_id": None, "source": "coco"}]}
        for t in range(3)]}
    with _scan_client(tmp_path, monkeypatch, vis) as c:
        r = c.post("/api/scan", data={"make_project": "leer"}, files={"files": ("a.jpg", b"\x00" * 10, "image/jpeg")})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "project" not in body and "Bauteile" in body["project_error"]
        assert not (tmp_path / "seed" / "projects" / "leer").exists()


def test_scan_project_name_is_slugged_readably(tmp_path, monkeypatch):
    """'Büro Test 1' must become buero-test-1, not 'brotest1' (umlauts and spaces were dropped)."""
    vis = {"frames": [{"t": float(t), "media_path": f"f/{t}.jpg", "triplets": [], "objects": [
        {"obj_id": "o1", "label": "wall", "bbox": [0, 0, 5, 5], "conf": 0.9, "marker_id": None, "source": "world"}]}
        for t in range(3)]}
    with _scan_client(tmp_path, monkeypatch, vis) as c:
        r = c.post("/api/scan", data={"make_project": "Büro Test 1"}, files={"files": ("a.jpg", b"\x00" * 10, "image/jpeg")})
        assert r.status_code == 200, r.text
        assert r.json()["project"]["dir"].endswith("/projects/buero-test-1")
        assert (tmp_path / "seed" / "projects" / "buero-test-1" / "elements.csv").exists()
        meta = json.loads((tmp_path / "seed" / "projects" / "buero-test-1" / "project.json").read_text(encoding="utf-8"))
        assert meta["name"] == "Scan: buero-test-1"  # not a frame file name from the thumbnail loop
