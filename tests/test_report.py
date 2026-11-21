"""Tagesbericht / Bautagebuch: GET /api/v2/report and GET /export/report.html (docs/UI-V2-CONTRACT.md)."""
import json
import re
import time
from pathlib import Path

import pytest

from tests.test_v2 import COST_KEYS, SP, _client, _keys

REPORT_KEYS = {"date", "project", "weather", "recordings", "work_done", "workforce", "inventory", "events", "photos",
               "delays", "lookahead"}
NOTE = "Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind krank."


@pytest.fixture()
def client(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as c:
        yield c


def _post_note(client, cid="rep-1"):
    r = client.post("/captures", data={"zone_id": "Z-AUDIENCE", "lang": "de", "capture_id": cid, "note": NOTE},
                    files={"files": ("walk.jpg", b"\x00" * 10, "image/jpeg")})
    assert r.status_code == 200, r.text


def _cache(cid: str) -> Path:
    from tagwerk.config import get_settings

    d = Path(get_settings().cache_dir) / cid
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_state_labels_cover_every_state():
    from tagwerk.pipeline.loop import STATES
    from tagwerk.report import STATE_DE

    assert {s for states in STATES.values() for s, _ in states} <= set(STATE_DE)
    assert STATE_DE["installed"] == "montiert" and STATE_DE["checked"] == "abgenommen"
    assert STATE_DE["wired"] == "verkabelt" and STATE_DE["commissioned"] == "in Betrieb"


def test_past_day_report_from_history(client):
    from tagwerk.pipeline.loop import STATES

    r = client.get("/api/v2/report", params={"date": "2026-11-25"})
    assert r.status_code == 200, r.text
    rep = r.json()
    assert set(rep) == REPORT_KEYS and rep["date"] == "2026-11-25"
    assert rep["project"] == {"name": "Hörsaal Sanierung", "site": None, "client": "TUM (fictitious renovation)"}
    assert [x["capture_id"] for x in rep["recordings"]] == ["hist-1125-a", "hist-1125-b"]
    assert set(rep["recordings"][0]) == {"capture_id", "time", "zone_name", "kind", "has_3d"}
    assert rep["recordings"][0]["time"] == "08:20" and rep["recordings"][0]["has_3d"] is False
    english = {s for states in STATES.values() for s, _ in states}
    assert rep["work_done"] and all(w["state_de"] not in english for w in rep["work_done"])
    assert set(rep["work_done"][0]) == {"activity_id", "activity_name", "element_name", "state_de", "quote", "capture_id"}
    present = {x["trade"]: x["count"] for x in rep["workforce"]["present"]}
    assert present["Trockenbau"] == 3 and present["Elektro"] == 1
    assert {e["type"] for e in rep["events"]} >= {"delay", "defect"}
    assert all(set(e) == {"type", "text", "severity"} for e in rep["events"])
    assert len(rep["lookahead"]) == 3 and all(isinstance(a, str) for x in rep["lookahead"] for a in x["activities"])
    assert all(d["delay_d"] > 0 and set(d) == {"activity_id", "activity_name", "delay_d", "cause"} for d in rep["delays"])
    assert rep["inventory"] == [] and rep["weather"] is None  # history has no readings: no network call for past days
    assert not set(_keys(rep)) & COST_KEYS


def test_report_after_typed_note(client):
    _post_note(client)
    rep = client.get("/api/v2/report").json()
    assert rep["date"] == "2026-11-26"
    row = next(w for w in rep["work_done"] if w["capture_id"] == "rep-1")
    assert row["element_name"] == "Stuhlreihe A" and row["state_de"] == "montiert" and row["activity_id"] == "A1080"
    assert {"trade": "Trockenbau", "count": 2, "reason": "krank"} in rep["workforce"]["absent"]
    rec = next(x for x in rep["recordings"] if x["capture_id"] == "rep-1")
    assert rec["has_3d"] is False and rec["kind"] == "photo"
    assert rep["weather"] == {"tempC": 5.0, "precipMm": 0.0, "windKmh": 8.0}
    assert "/media/rep-1/00_walk.jpg" in rep["photos"]


def test_inventory_from_sfm_groups_objects_and_relations(client):
    _post_note(client)
    rel = [{"rel": "next to", "rel_de": "neben", "target": "obj-9", "target_name": "Wand", "score": 0.5, "count": 3,
            "source": "model"}]
    objects = [
        {"id": "obj-1", "label": "chair", "name_de": "Stuhl", "category_de": "Ausstattung", "position": [0, 0, 1],
         "extent": [1, 1, 1], "detections": 5, "first_t": 1.0, "last_t": 2.0, "conf": 0.8,
         "thumb": "/media/rep-1/sfm/0002.jpg", "bbox_in_thumb": [1, 2, 3, 4], "element_id": None, "relations": rel},
        {"id": "obj-2", "label": "chair", "name_de": "Stuhl", "category_de": "Ausstattung", "position": [1, 0, 1],
         "extent": [1, 1, 1], "detections": 4, "first_t": 3.0, "last_t": 4.0, "conf": 0.7, "thumb": None,
         "bbox_in_thumb": None, "element_id": None,
         "relations": rel + [{"rel": "under", "rel_de": "unter", "target": "obj-3", "target_name": "Leuchte",
                              "score": 0.4, "count": 1, "source": "geometry"},
                             {"rel": "behind", "rel_de": "hinter", "target": "obj-7", "target_name": "Person",
                              "score": 0.4, "count": 1, "source": "model"}]},
        {"id": "obj-3", "label": "door", "name_de": "Tür", "category_de": "Öffnungen", "position": [2, 0, 1],
         "extent": [1, 2, 0.1], "detections": 9, "first_t": 0.0, "last_t": 9.0, "conf": 0.9, "thumb": None,
         "bbox_in_thumb": None, "element_id": "E-DOOR-1", "relations": []},
    ]
    (_cache("rep-1") / "sfm.json").write_text(json.dumps(
        {"capture_id": "rep-1", "ok": True, "reason": None, "seconds": 70.0, "frames_used": 60, "frames_registered": 50,
         "points": [], "cameras": [], "objects": objects, "units": "relative (SfM scale is arbitrary)"}), encoding="utf-8")
    rep = client.get("/api/v2/report").json()
    inv = {x["name_de"]: x for x in rep["inventory"]}
    assert inv["Stuhl"]["count"] == 2 and inv["Tür"]["count"] == 1
    assert inv["Stuhl"]["relations"] == ["neben Wand", "unter Leuchte"]
    assert inv["Stuhl"]["thumb"] == "/media/rep-1/sfm/0002.jpg" and inv["Stuhl"]["capture_id"] == "rep-1"
    assert next(x for x in rep["recordings"] if x["capture_id"] == "rep-1")["has_3d"] is True


def test_has_3d_false_when_reconstruction_failed(client):
    _post_note(client)
    (_cache("rep-1") / "sfm.json").write_text(json.dumps({"capture_id": "rep-1", "ok": False, "reason": "zu wenig Bilder",
                                                          "objects": []}), encoding="utf-8")
    rep = client.get("/api/v2/report").json()
    assert next(x for x in rep["recordings"] if x["capture_id"] == "rep-1")["has_3d"] is False


def test_inventory_falls_back_to_vision_detections(client):
    _post_note(client)

    def obj(i, label):
        return {"obj_id": i, "label": label, "bbox": [0, 0, 10, 10], "conf": 0.8, "source": "world"}

    frames = [
        {"t": 0.0, "media_path": "frames/0001.jpg", "objects": [obj("a", "chair"), obj("b", "chair"), obj("c", "dining table"),
                                                                 obj("p", "person")],
         "triplets": [{"s": "a", "rel": "next to", "o": "c", "score": 0.6, "source": "model"},
                      {"s": "c", "rel": "on", "o": "b", "score": 0.3, "source": "geometry"},
                      {"s": "a", "rel": "behind", "o": "p", "score": 0.5, "source": "model"}]},
        {"t": 1.0, "media_path": "frames/0002.jpg", "objects": [obj("d", "chair")],
         "triplets": [{"s": "d", "rel": "leaning on", "o": "d", "score": 0.2, "source": "model"}]},
    ]
    (_cache("rep-1") / "vision.json").write_text(json.dumps({"capture_id": "rep-1", "frames": frames}), encoding="utf-8")
    rep = client.get("/api/v2/report").json()
    inv = {x["name_de"]: x for x in rep["inventory"]}
    assert inv["Stuhl"]["count"] == 2  # most seen in one frame
    assert "neben Tisch" in inv["Stuhl"]["relations"] and "leaning on Stuhl" in inv["Stuhl"]["relations"]
    assert inv["Tisch"]["relations"] == ["auf Stuhl"]
    assert "Person" not in inv  # people are no inventory, nor relation targets
    assert not any("Person" in r for x in inv.values() for r in x["relations"])


def test_html_export_is_print_ready_and_self_contained(client):
    _post_note(client)
    r = client.get("/export/report.html", params={"date": "2026-11-26"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    html = r.text
    for s in ("Tagesbericht", "26.11.2026", "Unterschrift", "Stuhlreihe A", "montiert", "Trockenbau", "@media print"):
        assert s in html, s
    assert not re.search(r"https?://", html)
    assert "<script" not in html


def test_html_export_empty_sections_say_keine(client):
    html = client.get("/export/report.html", params={"date": "2026-11-28"}).text  # a Saturday, nothing recorded
    assert html.count("keine") >= 4


def test_bad_date_is_400(client):
    for url in ("/api/v2/report", "/export/report.html"):
        assert client.get(url, params={"date": "26.11.2026"}).status_code == 400
        assert client.get(url, params={"date": "2026-13-01"}).status_code == 400


@pytest.mark.skipif(not (SP / "elements.csv").exists(), reason="run scripts/import_schependomlaan.py")
def test_schependomlaan_report_is_fast(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, "schependomlaan") as c:
        t = time.perf_counter()
        r = c.get("/api/v2/report", params={"date": "2015-07-17"})
        elapsed = time.perf_counter() - t
        assert r.status_code == 200 and elapsed < 1.5, elapsed
        rep = r.json()
        assert rep["project"]["site"] == "Schependomlaan, Nijmegen" and rep["recordings"]
        assert all(len(x["activities"]) == len(set(x["activities"])) for x in rep["lookahead"])  # same-named activities
        assert c.get("/export/report.html", params={"date": "2015-07-17"}).status_code == 200


def test_element_label_groups_numbered_elements():
    from tagwerk.report import element_label

    assert element_label(["Stuhlreihe A"]) == "Stuhlreihe A"
    assert element_label(["Stuhlreihe A", "Stuhlreihe B"]) == "Stuhlreihe A, Stuhlreihe B"
    assert element_label([f"sporenkap {i} (Derde verdieping)" for i in range(1, 33)]) == "32× sporenkap (Derde verdieping)"
    assert element_label(["kozijn 1 (Dak)", "merk K 1 (Dak)", "merk J 2 (Dak)", "merk D (Dak)"]) == \
        "4 Bauteile: kozijn 1 (Dak), merk K 1 (Dak), …"


def test_one_sentence_for_many_elements_is_one_row():
    from tagwerk.project import SEED_DIR, Project
    from tagwerk.report import _work_done

    p = Project.from_seed(SEED_DIR)
    work = {"element_ids": ["E-ROW-A", "E-ROW-B"], "activity_id": None, "state_proposed": "installed",
            "evidence": "voice", "quote": "Reihe A und B montiert.", "t": None}
    p.apply_structured({"capture_id": "rep-2", "zone_id": "Z-AUDIENCE", "ts": "2026-11-26T10:00:00Z"},
                       {"capture_id": "rep-2", "work_done": [work], "labour_present": [], "absences": [],
                        "material_delivered": [], "special_events": [], "unmatched": []})
    rows = _work_done(p, [p.captures["rep-2"]])
    assert len(rows) == 1 and rows[0]["element_name"] == "Stuhlreihe A, Stuhlreihe B", rows
