"""Scan 3D "Gesagt": items the speaker names, linked to the 3D objects and the moment they are said."""
from tagwerk.pipeline.mentions import link_mentions


def _obj(oid, label, name_de, first_t=None, last_t=None, element_id=None):
    return {"id": oid, "label": label, "name_de": name_de, "category_de": "x", "position": [0, 0, 0],
            "first_t": first_t, "last_t": last_t, "element_id": element_id, "relations": []}


SFM = {"capture_id": "c1", "ok": True, "objects": [
    _obj("obj-1", "door", "Tür", 2.0, 6.0, "S-DOOR-1"),
    _obj("obj-2", "chair", "Stuhl", 10.0, 14.0),
    _obj("obj-3", "chair", "Stuhl", 40.0, 44.0),
    _obj("obj-4", "tv", "Bildschirm", 20.0, 30.0),
    _obj("obj-5", "clock", "Uhr", 50.0, 51.0),
]}
ELEMENTS = {"S-DOOR-1": {"id": "S-DOOR-1", "name_de": "Tür", "name_en": "door 1", "type": "default",
                         "aliases": ["door", "Tür"]}}


def _seg(start, end, text):
    return {"start": start, "end": end, "text": text}


def test_named_items_link_to_objects_with_time_phrase_and_state():
    tr = {"segments": [_seg(3.0, 5.5, "Hier ist die Tür, die ist eingebaut."),
                       _seg(11.0, 13.0, "Da hinten stehen die Stühle."),
                       _seg(22.0, 25.0, "Und der Bildschirm hängt schon.")]}
    res = link_mentions(SFM, tr, ELEMENTS, activity_of=lambda eid: "A020" if eid == "S-DOOR-1" else None)
    m = res["mentions"]
    assert [x["phrase"] for x in m] == ["Tür", "Stühle", "Bildschirm"]
    door = m[0]
    assert door["object_ids"] == ["obj-1"] and door["t_start"] == 3.0 and door["t_end"] == 5.5
    assert door["text"] == "Hier ist die Tür, die ist eingebaut."
    assert door["state"] == "installed" and door["state_de"] and door["activity_id"] == "A020"
    assert door["element_id"] == "S-DOOR-1"
    # the plural names the chair seen around that moment (10-14 s), not the one at 40 s
    assert m[1]["object_ids"] == ["obj-2"] and m[1]["state"] == "installed"  # "stehen"
    assert m[2]["object_ids"] == ["obj-4"]
    objs = {o["id"]: o for o in res["objects"]}
    assert objs["obj-1"]["mentioned"] is True and objs["obj-1"]["mention_times"] == [door["t"]] and 3.0 <= door["t"] <= 5.5
    assert objs["obj-1"]["spoken_state"] == "installed" and objs["obj-1"]["spoken_phrase"] == "Tür"
    assert objs["obj-3"]["mentioned"] is False and objs["obj-3"]["mention_times"] == []
    assert res["unseen_mentions"] == []


def test_label_named_outside_any_sighting_window_links_the_closest_in_time():
    res = link_mentions(SFM, {"segments": [_seg(70.0, 72.0, "Insgesamt zwölf Stühle im Raum.")]}, {})
    assert res["mentions"][0]["object_ids"] == ["obj-3"]  # seen 40-44 s, the other chair 10-14 s


def test_building_items_said_but_not_seen_are_unseen_mentions():
    tr = {"segments": [_seg(30.0, 33.0, "Die Fenster sind noch nicht eingebaut, die Betonfassade fehlt."),
                       _seg(34.0, 35.0, "Um 10 Uhr kommt der Elektriker.")]}
    res = link_mentions(SFM, tr, {})
    names = [(u["name"], u["phrase"], u["t"]) for u in res["unseen_mentions"]]
    assert any(n == "Fenster" and p == "Fenster" and 30.0 <= t <= 33.0 for n, p, t in names)
    assert any(n == "Betonfassade" for n, _, _ in names)
    # "Uhr" as a time of day is not the detected clock and never an unseen item
    assert res["mentions"] == []
    assert not any(u["name"] == "Uhr" for u in res["unseen_mentions"])


def test_english_speech_and_no_transcript():
    res = link_mentions(SFM, {"segments": [_seg(4.0, 5.0, "This door is installed.")]}, {})
    assert res["mentions"][0]["object_ids"] == ["obj-1"] and res["mentions"][0]["phrase"] == "door"
    empty = link_mentions(SFM, None, {})
    assert empty["mentions"] == [] and empty["unseen_mentions"] == []
    assert all(o["mentioned"] is False for o in empty["objects"])


def test_one_item_once_per_segment_and_unrelated_words_ignored():
    tr = {"segments": [_seg(3.0, 4.0, "Tür, Tür, nochmal die Tür."), _seg(5.0, 6.0, "Wir sind im Hackathon-Raum.")]}
    res = link_mentions(SFM, tr, {})
    assert len(res["mentions"]) == 1
    assert len({o["id"]: o for o in res["objects"]}["obj-1"]["mention_times"]) == 1


# ---------------------------------------------------------------- API + Tagesbericht

def _api_scan(c, cid, segments, objs):
    import json

    from tests.test_followups import _cache_dir

    d = _cache_dir() / cid
    d.mkdir(parents=True, exist_ok=True)
    (d / "sfm.json").write_text(json.dumps({"capture_id": cid, "ok": True, "objects": objs}), encoding="utf-8")
    (d / "speech.json").write_text(json.dumps({"capture_id": cid, "lang": "de", "segments": segments}), encoding="utf-8")


def test_scan3d_endpoint_carries_mentions_from_the_cached_transcript(tmp_path, monkeypatch):
    from tests.test_v2 import _client

    with _client(tmp_path, monkeypatch) as c:
        _api_scan(c, "talk-1", [_seg(3.0, 5.0, "Die Leinwand ist montiert."), _seg(8.0, 9.0, "Die Fenster fehlen.")],
                  [_obj("obj-1", "projection screen", "Leinwand", 2.0, 6.0, "E-SCREEN"),
                   _obj("obj-2", "chair", "Stuhl", 7.0, 8.0)])
        body = c.get("/api/v2/scan3d/talk-1").json()
    m = body["mentions"]
    assert len(m) == 1 and m[0]["object_ids"] == ["obj-1"] and m[0]["state"]
    assert m[0]["activity_id"] == "A1060" and m[0]["element_id"] == "E-SCREEN"
    assert [u["name"] for u in body["unseen_mentions"]] == ["Fenster"]
    objs = {o["id"]: o for o in body["objects"]}
    assert objs["obj-1"]["mentioned"] and objs["obj-1"]["mention_times"] == [m[0]["t"]] and not objs["obj-2"]["mentioned"]


def test_scan3d_without_transcript_has_empty_mentions(tmp_path, monkeypatch):
    import json

    from tests.test_followups import _cache_dir
    from tests.test_v2 import _client

    with _client(tmp_path, monkeypatch) as c:
        d = _cache_dir() / "mute-1"
        d.mkdir(parents=True)
        (d / "sfm.json").write_text(json.dumps({"capture_id": "mute-1", "ok": True,
                                                "objects": [_obj("obj-1", "door", "Tür")]}), encoding="utf-8")
        body = c.get("/api/v2/scan3d/mute-1").json()
    assert body["mentions"] == [] and body["unseen_mentions"] == [] and body["objects"][0]["mentioned"] is False


def test_report_inventory_marks_items_the_speaker_named(tmp_path, monkeypatch):
    from tests.test_v2 import _client

    with _client(tmp_path, monkeypatch) as c:
        r = c.post("/captures", data={"zone_id": "Z-AUDIENCE", "capture_id": "rep-talk", "note": "Rundgang"})
        assert r.status_code == 200, r.text
        _api_scan(c, "rep-talk", [_seg(3.0, 5.0, "Die Tür ist eingebaut.")],
                  [{**_obj("obj-1", "door", "Tür", 2.0, 6.0), "thumb": None},
                   {**_obj("obj-2", "chair", "Stuhl", 7.0, 8.0), "thumb": None}])
        inv = {x["name_de"]: x for x in c.get("/api/v2/report").json()["inventory"]}
        html = c.get("/export/report.html").text
    assert inv["Tür"]["mentioned"] is True and inv["Tür"]["spoken"] == "Tür" and inv["Tür"]["spoken_state_de"]
    assert inv["Stuhl"]["mentioned"] is False
    assert "gesagt" in html.lower()


def test_english_walkthrough_words_tables_slab_dustbins_storage():
    """The venue walk (lang en): "The tables over here, they have to be put, slab has been placed, dustbins here,
    storage here". Plurals and everyday English names reach the detected objects; "have to" is not a state."""
    sfm = {"capture_id": "c", "ok": True, "objects": [
        _obj("obj-1", "dining table", "Tisch", 50.0, 60.0), _obj("obj-2", "floor", "Boden", 50.0, 90.0),
        _obj("obj-3", "trash can", "Mülleimer", 55.0, 58.0), _obj("obj-4", "concrete column", "Betonstütze", 51.0, 52.0)]}
    tr = {"segments": [_seg(50.8, 60.0, "The tables over here, they have to be put, slab has been placed,"),
                       _seg(60.0, 70.0, "dustbins here, the pillar, storage here.")]}
    res = link_mentions(sfm, tr, {})
    got = {x["label"]: x for x in res["mentions"]}
    assert got["dining table"]["phrase"] == "tables" and got["dining table"]["object_ids"] == ["obj-1"]
    assert got["dining table"]["state"] is None  # "have to be put": still to do
    assert got["floor"]["phrase"] == "slab" and got["floor"]["state"] == "covered"  # "has been placed" (floor: belegt)
    assert got["trash can"]["phrase"] == "dustbins" and got["concrete column"]["phrase"] == "pillar"
    assert any(u["name"] == "Lager" and u["phrase"] == "storage" for u in res["unseen_mentions"])


def test_trash_can_is_detected_and_catalogued():
    from tagwerk.pipeline.scan import CATALOG
    from tagwerk.pipeline.vision import WORLD_CLASSES

    assert "trash can" in WORLD_CLASSES and CATALOG["trash can"][2] == "Mülleimer"


def test_phrase_time_is_estimated_inside_long_segments():
    """Whisper segments can be 45 s long: `t` places the phrase by its position in the text, for seeking/pulsing."""
    text = "a" * 50 + " the tables here " + "b" * 33  # "tables" at char 55 of 100
    res = link_mentions(SFM | {"objects": [_obj("obj-1", "dining table", "Tisch", 70.0, 80.0)]},
                        {"segments": [_seg(50.0, 150.0, text), _seg(160.0, 161.0, "Die Fenster fehlen.")]}, {})
    assert res["mentions"][0]["t"] == 105.0 and res["mentions"][0]["t_start"] == 50.0
    assert abs(res["unseen_mentions"][0]["t"] - (160.0 + 4 / 19)) < 0.01
    assert res["objects"][0]["spoken_state_de"] is None
    res = link_mentions(SFM, {"segments": [_seg(3.0, 4.0, "Die Tür ist eingebaut.")]}, {})
    assert {o["id"]: o for o in res["objects"]}["obj-1"]["spoken_state_de"] == "montiert"


def test_unseen_items_named_repeatedly_are_one_entry_with_all_times():
    tr = {"segments": [_seg(1.0, 2.0, "Die Betonfassade."), _seg(10.0, 11.0, "Nochmal die Betonfassade, fertig.")]}
    unseen = link_mentions(SFM, tr, {})["unseen_mentions"]
    assert len(unseen) == 1 and unseen[0]["name"] == "Betonfassade" and unseen[0]["t"] < 2.0
    assert len(unseen[0]["times"]) == 2 and unseen[0]["state"] is not None  # state from the later "fertig"


def test_word_timestamps_place_the_phrase_exactly():
    words = [{"start": 50.9, "end": 51.2, "word": "The"}, {"start": 51.2, "end": 51.7, "word": "tables"},
             {"start": 51.7, "end": 52.0, "word": "over"}, {"start": 52.0, "end": 52.4, "word": "here,"},
             {"start": 93.5, "end": 93.9, "word": "dustbins"}]
    sfm = {"capture_id": "c", "ok": True, "objects": [_obj("obj-1", "dining table", "Tisch", 49.0, 55.0)]}
    seg = {"start": 0.8, "end": 93.9, "text": "The tables over here, dustbins", "words": words}
    res = link_mentions(sfm, {"segments": [seg]}, {})
    assert res["mentions"][0]["t"] == 51.2 and res["mentions"][0]["object_ids"] == ["obj-1"]
    assert res["unseen_mentions"][0]["t"] == 93.5


def test_without_a_sighting_near_t_the_closest_section_is_named_not_every_instance():
    """Sections leave gaps (no section covers 89-98 s of the venue walk): 'slab' at 93 s must not light up all 49
    floors of the walk, only the closest-in-time ones of one section."""
    objs = [{**_obj("obj-1", "floor", "Boden", 6.0, 18.0), "section": 0},
            {**_obj("obj-2", "floor", "Boden", 80.0, 89.0), "section": 3},
            {**_obj("obj-3", "floor", "Boden", 81.0, 88.0), "section": 3},
            {**_obj("obj-4", "floor", "Boden", 103.0, 108.0), "section": 8}]
    res = link_mentions({"capture_id": "c", "ok": True, "objects": objs}, {"segments": [_seg(95.0, 96.0, "slab")]}, {})
    assert res["mentions"][0]["object_ids"] == ["obj-2", "obj-3"]
