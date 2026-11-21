"""BIM viewer API: /api/v2/bim (element states by IFC GlobalId as of day D) and the tessellated model files."""
import json
from array import array

import pytest

from tests.test_v2 import SP, _client


def _write_model(d, gids):
    pos, idx, els = array("f"), array("I"), []
    for n, gid in enumerate(gids):
        first_v, first_i = len(pos) // 3, len(idx)
        pos.extend([n, 0, 0, n + 1, 0, 0, n, 1, 0])
        idx.extend([0, 1, 2])
        els.append({"gid": gid, "cls": "IfcWall", "name": gid, "v": [first_v, 3], "i": [first_i, 3]})
    with (d / "bim.bin").open("wb") as fh:
        pos.tofile(fh)
        idx.tofile(fh)
    (d / "bim.json").write_text(json.dumps({"source": "test.ifc", "elements": els, "bbox": [[0, 0, 0], [3, 1, 0]],
                                            "vertices": len(pos) // 3, "triangles": len(idx) // 3}), encoding="utf-8")


def test_project_without_model(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as c:
        b = c.get("/api/v2/bim").json()
        assert b["available"] is False and b["elements"] == []
        assert c.get("/api/v2/bim/model.json").status_code == 404
        assert c.get("/api/v2/bim/model.bin").status_code == 404


def test_bim_states_follow_the_day(tmp_path, monkeypatch):
    import tagwerk.bim as bim

    model = tmp_path / "model"
    model.mkdir()
    monkeypatch.setattr(bim, "model_dir", lambda: model)
    with _client(tmp_path, monkeypatch) as c:
        import tagwerk.state as state

        p = state.get_project()
        p.elements["E-ROW-A"]["global_id"] = "GID-ROW-A"  # the Hörsaal seed has no IFC: give two elements ids
        p.elements["E-ROW-H"]["global_id"] = "GID-ROW-H"
        monkeypatch.setattr(bim, "_global_ids", lambda: {"GID-ROW-A": "E-ROW-A", "GID-ROW-H": "E-ROW-H"})
        _write_model(model, ["GID-ROW-A", "GID-ROW-H", "GID-OTHER"])
        b = c.get("/api/v2/bim", params={"date": "2026-11-25"}).json()
        assert b["available"] is True and b["source"] == "test.ifc"
        by = {e["gid"]: e for e in b["elements"]}
        assert set(by) == {"GID-ROW-A", "GID-ROW-H"}  # geometry without a project element stays grey in the viewer
        assert by["GID-ROW-A"]["element_id"] == "E-ROW-A" and by["GID-ROW-A"]["name"] == "Stuhlreihe A"
        assert by["GID-ROW-A"]["activity_id"] in ("A1020", "A1080")
        before = by["GID-ROW-A"]["pct"]
        r = c.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "bim-1", "note": "Stuhlreihe A ist montiert."})
        assert r.status_code == 200
        after = {e["gid"]: e for e in c.get("/api/v2/bim").json()["elements"]}["GID-ROW-A"]
        assert after["pct"] > before and after["state_de"] == "montiert"
        assert c.get("/api/v2/bim/model.json").json()["elements"][2]["gid"] == "GID-OTHER"
        assert len(c.get("/api/v2/bim/model.bin").content) == (9 * 3 + 3 * 3) * 4
        assert c.get("/api/v2/bim", params={"date": "bad"}).status_code == 400


@pytest.mark.skipif(not (SP / "elements.csv").exists(), reason="run scripts/import_schependomlaan.py")
def test_schependomlaan_elements_have_global_ids(tmp_path, monkeypatch):
    import tagwerk.bim as bim

    with _client(tmp_path, monkeypatch, "schependomlaan"):
        ids = bim._global_ids()
        assert len(ids) > 1500 and all(len(g) == 22 for g in list(ids)[:50])
        from datetime import date

        els = bim.states(date(2015, 7, 24))["elements"]
        # the activities only ask for "installed" (70 %): an installed element is done, not "begun"
        done = [e for e in els if e["done"]]
        assert len(done) > 1000 and all(e["pct"] >= 70 for e in done)
        assert not any(e["done"] for e in els if e["pct"] == 0)
