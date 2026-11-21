"""Follow-ups after the integration: relation and inventory noise, scan project meta, weather off the event loop,
early 409 on /api/scan, replays keep their media, RAISED edges for proposals."""
import json
from pathlib import Path

from tests.test_v2 import _client


def _cache_dir() -> Path:
    from tagwerk.config import get_settings

    return Path(get_settings().cache_dir)


def test_person_person_relations_are_dropped():
    from tagwerk.pipeline.sfm import _relations_for

    objs = [{"id": "obj-1", "label": "person", "name_de": "Person", "relations": []},
            {"id": "obj-2", "label": "person", "name_de": "Person", "relations": []},
            {"id": "obj-3", "label": "wall", "name_de": "Wand", "relations": []},
            {"id": "obj-4", "label": "hard hat", "name_de": "Schutzhelm", "relations": []}]
    det_inst = {"d1": "obj-1", "d2": "obj-2", "d3": "obj-3", "d4": "obj-4"}
    triplets = [{"s": "d1", "rel": "next to", "o": "d2", "score": 0.6, "source": "model"},
                {"s": "d1", "rel": "next to", "o": "d3", "score": 0.5, "source": "model"},
                {"s": "d4", "rel": "on", "o": "d1", "score": 0.34, "source": "model"}]
    _relations_for(objs, triplets, det_inst)
    rels = {o["id"]: [(r["rel_de"], r["target_name"]) for r in o["relations"]] for o in objs}
    assert rels["obj-1"] == [("neben", "Wand")]
    assert rels["obj-4"] == [("auf", "Person")]  # a helmet on a person is kept


def test_scan3d_hides_person_person_relations_of_older_files(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as c:
        d = _cache_dir() / "old-scan"
        d.mkdir(parents=True)
        objs = [{"id": "obj-1", "label": "person", "name_de": "Person",
                 "relations": [{"rel": "behind", "rel_de": "hinter", "target": "obj-2", "target_name": "Person",
                                "score": 0.5, "count": 2, "source": "model"},
                               {"rel": "in front of", "rel_de": "vor", "target": "obj-3", "target_name": "Tür",
                                "score": 0.4, "count": 1, "source": "model"}]},
                {"id": "obj-2", "label": "person", "name_de": "Person", "relations": []},
                {"id": "obj-3", "label": "door", "name_de": "Tür", "relations": []}]
        (d / "sfm.json").write_text(json.dumps({"capture_id": "old-scan", "ok": True, "objects": objs}), encoding="utf-8")
        got = c.get("/api/v2/scan3d/old-scan").json()
        assert [r["target_name"] for r in got["objects"][0]["relations"]] == ["Tür"]


def test_report_inventory_hides_labels_outside_the_catalog(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as c:
        r = c.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "rep-noise", "note": "Kratzer an der Tür"})
        assert r.status_code == 200, r.text
        d = _cache_dir() / "rep-noise"
        objs = [{"id": f"obj-{i}", "label": label, "name_de": name, "relations": [], "thumb": None}
                for i, (label, name) in enumerate([("door", "Tür"), ("broccoli", "Brokkoli"), ("skis", "Skis"),
                                                   ("tie", "Krawatte"), ("chair", "Stuhl")])]
        (d / "sfm.json").write_text(json.dumps({"capture_id": "rep-noise", "ok": True, "objects": objs}), encoding="utf-8")
        names = {x["name_de"] for x in c.get("/api/v2/report").json()["inventory"]}
        assert names == {"Tür", "Stuhl"}


def test_scan_project_has_no_borrowed_client(tmp_path):
    from datetime import date

    from tagwerk.pipeline.scan import inventory, seed_from_scan
    from tagwerk.project import Project
    from tests.test_scan import _vis

    out = tmp_path / "proj"
    seed_from_scan(inventory(_vis()), out, "proj", date(2026, 11, 26), "Raum")
    p = Project.from_seed(out)
    assert p.meta["client"] is None and p.meta["site"] is None and p.meta["name"] == "Scan: proj"


def test_context_is_built_off_the_event_loop(tmp_path, monkeypatch):
    """build_context may fetch the weather (up to 3 s): it must run in a worker thread, not on the event loop."""
    import asyncio

    import tagwerk.pipeline.context as context

    on_loop = []
    real = context.build_context

    def spy(*a, **k):
        try:
            asyncio.get_running_loop()
            on_loop.append(True)
        except RuntimeError:
            on_loop.append(False)
        return real(*a, **k)

    with _client(tmp_path, monkeypatch) as c:
        monkeypatch.setattr(context, "build_context", spy)
        r = c.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "cap-ctx", "note": "Kratzer an der Tür"})
        assert r.status_code == 200, r.text
    assert on_loop == [False]


def test_scan_rejects_a_taken_project_name_before_the_vision_pass(tmp_path, monkeypatch):
    import tagwerk.pipeline.runner as runner

    async def boom(*a, **k):
        raise AssertionError("vision ran before the name check")

    with _client(tmp_path, monkeypatch) as c:
        monkeypatch.setattr(runner, "_gpu_stage", boom)
        r = c.post("/api/scan", data={"make_project": "Hoersaal"}, files={"files": ("a.jpg", b"\x00" * 10, "image/jpeg")})
        assert r.status_code == 409, r.text


def test_replay_keeps_the_media_of_its_source(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as c:
        src = _cache_dir() / "src-cap"
        (src / "media").mkdir(parents=True)
        (src / "media" / "walk.mp4").write_bytes(b"\x00" * 32)
        for name, data in (("speech.json", {"capture_id": "src-cap", "lang": "de", "segments": []}),
                           ("vision.json", {"capture_id": "src-cap", "frames": []}),
                           ("capture.json", {"capture_id": "src-cap", "zone_id": "Z-AUDIENCE"})):
            (src / name).write_text(json.dumps(data), encoding="utf-8")
        r = c.post("/captures", data={"replay_of": "src-cap", "capture_id": "replay-media"})
        assert r.status_code == 200, r.text
        assert (_cache_dir() / "replay-media" / "media" / "walk.mp4").is_file()
        rec = next(x for x in c.get("/api/v2/day").json()["recordings"] if x["capture_id"] == "replay-media")
        assert rec["kind"] == "video" and rec["video"] == "/media/replay-media/walk.mp4"


def test_taskgraph_links_a_recording_to_its_proposal(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as c:
        from tagwerk.state import save_result

        meta = {"capture_id": "cap-prop", "zone_id": "Z-AUDIENCE", "ts": "2026-11-26T09:00:00Z"}
        work = {"element_ids": ["E-ROW-H"], "activity_id": None, "state_proposed": "installed", "evidence": "vision",
                "quote": "", "t": None}
        save_result(meta, {"capture_id": "cap-prop", "work_done": [work], "labour_present": [], "absences": [],
                           "material_delivered": [], "special_events": [], "unmatched": []})
        g = c.get("/api/v2/taskgraph").json()
        assert {"src": "cap-prop", "dst": "prop:cap-prop:E-ROW-H", "type": "RAISED"} in g["edges"]
