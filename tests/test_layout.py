"""Room layout from a phone AR / photogrammetry scan (GLB/OBJ/PLY) attached to a scan capture."""
import json

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")


def _room(offset=(10.0, 3.0, -4.0)):
    """A 6 x 3 x 4 m room (box) whose floor sits at y = 3, off-centre: what an app might export."""
    m = trimesh.creation.box(extents=(6.0, 3.0, 4.0))
    m.apply_translation(np.array(offset) + [0, 1.5, 0])
    return m


@pytest.mark.parametrize("ext", ["glb", "obj", "ply"])
def test_import_normalises_any_format_to_a_levelled_centred_glb(tmp_path, ext):
    from tagwerk import layout

    src = tmp_path / f"room.{ext}"
    _room().export(src)
    meta = layout.import_layout(src, tmp_path / "out")
    assert (tmp_path / "out" / "layout.glb").is_file() and meta["faces"] == 12 and meta["units"] == "m"
    got = trimesh.load(tmp_path / "out" / "layout.glb", force="mesh")
    lo, hi = got.bounds
    assert abs(lo[1]) < 1e-6 and abs(hi[1] - 3.0) < 1e-6  # floor at 0, height kept (metric)
    assert np.allclose((lo + hi)[[0, 2]] / 2, 0, atol=1e-6)  # centred
    assert meta["size"] == pytest.approx([6.0, 3.0, 4.0])


def test_import_rejects_files_without_geometry(tmp_path):
    from tagwerk import layout

    bad = tmp_path / "x.glb"
    bad.write_bytes(b"not a mesh")
    with pytest.raises(ValueError):
        layout.import_layout(bad, tmp_path / "out")


def test_api_upload_serve_and_scan3d_summary(tmp_path, monkeypatch):
    from tests.test_followups import _cache_dir
    from tests.test_v2 import _client

    src = tmp_path / "room.glb"
    _room().export(src)
    with _client(tmp_path, monkeypatch) as c:
        d = _cache_dir() / "walk-1"
        d.mkdir(parents=True)
        (d / "sfm.json").write_text(json.dumps({"capture_id": "walk-1", "ok": True, "objects": []}), encoding="utf-8")
        r = c.post("/api/v2/scan3d/walk-1/layout", files={"file": ("room.glb", src.read_bytes())})
        assert r.status_code == 200, r.text
        assert r.json()["faces"] == 12 and r.json()["source"] == "room.glb"
        g = c.get("/api/v2/scan3d/walk-1/layout.glb")
        assert g.status_code == 200 and g.content[:4] == b"glTF"
        body = c.get("/api/v2/scan3d/walk-1").json()
        assert body["layout"]["url"] == "/api/v2/scan3d/walk-1/layout.glb" and body["layout"]["faces"] == 12
        assert c.post("/api/v2/scan3d/walk-1/layout", files={"file": ("x.glb", b"junk")}).status_code == 400
        assert c.post("/api/v2/scan3d/nope/layout", files={"file": ("room.glb", src.read_bytes())}).status_code == 404
        assert c.get("/api/v2/scan3d/nope/layout.glb").status_code == 404


def test_face_coloured_meshes_import_without_scipy(tmp_path):
    """Some apps colour faces; trimesh's face->vertex colour conversion needs scipy (not a dependency)."""
    from tagwerk import layout

    m = _room()
    m.visual.face_colors = [150, 110, 70, 255]
    src = tmp_path / "room.ply"
    m.export(src)  # PLY keeps face colours without the conversion
    meta = layout.import_layout(src, tmp_path / "out")
    assert meta["faces"] == 12
    got = trimesh.load(tmp_path / "out" / "layout.glb", force="mesh")
    assert tuple(got.visual.vertex_colors[0][:3]) == (150, 110, 70)
