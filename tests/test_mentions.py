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
    assert objs["obj-1"]["mentioned"] is True and objs["obj-1"]["mention_times"] == [3.0]
    assert objs["obj-1"]["spoken_state"] == "installed" and objs["obj-1"]["spoken_phrase"] == "Tür"
    assert objs["obj-3"]["mentioned"] is False and objs["obj-3"]["mention_times"] == []
    assert res["unseen_mentions"] == []


def test_label_named_outside_any_sighting_window_links_all_its_instances():
    res = link_mentions(SFM, {"segments": [_seg(70.0, 72.0, "Insgesamt zwölf Stühle im Raum.")]}, {})
    assert res["mentions"][0]["object_ids"] == ["obj-2", "obj-3"]


def test_building_items_said_but_not_seen_are_unseen_mentions():
    tr = {"segments": [_seg(30.0, 33.0, "Die Fenster sind noch nicht eingebaut, die Betonfassade fehlt."),
                       _seg(34.0, 35.0, "Um 10 Uhr kommt der Elektriker.")]}
    res = link_mentions(SFM, tr, {})
    names = [(u["name"], u["phrase"], u["t"]) for u in res["unseen_mentions"]]
    assert ("Fenster", "Fenster", 30.0) in names
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
    assert {o["id"]: o for o in res["objects"]}["obj-1"]["mention_times"] == [3.0]
