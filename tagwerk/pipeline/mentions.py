"""Scan 3D "Gesagt": link what the speaker names in the walkthrough to the 3D objects and the moment it is said.

link_mentions(sfm, transcript, elements, activity_of) -> {"mentions", "unseen_mentions", "objects"} where
  mentions:        per transcript segment and named item {t_start, t_end, text, phrase, label, name_de, object_ids,
                   element_id, state, state_de, activity_id}
  unseen_mentions: building items named but not detected in the clip {name, phrase, t, text, state, state_de}
  objects:         the sfm objects with mentioned / mention_times / spoken_state / spoken_phrase added
Names are matched like the structuring rules (tagwerk.pipeline.structure): German and English catalogue names,
the project elements' names and aliases, German plurals; building stems inside compounds ("Betonfassade") come from
scan.SPEECH_STEMS. Computed at read time, so older and replayed captures get it from their cached speech.json.
"""
from __future__ import annotations

import re
from collections.abc import Callable

from tagwerk.labels import STATE_DE
from tagwerk.pipeline.scan import CATALOG, NOT_ELEMENTS, SPEECH_STEMS
from tagwerk.pipeline.sfm import COCO_DE
from tagwerk.pipeline.structure import _WORD, _name_hit, _norm, _plural_forms, _state_for

WINDOW_S = 4.0  # an object counts as "the one meant" if it was seen within this many seconds of the phrase
NOT_ITEMS = {"person", "hard hat", "safety vest"}  # labour, not items (structure.py handles crews and absences)
_TIME_UHR = re.compile(r"\d\s*uhr\b")


def _names(label: str, name_de: str | None, element: dict | None) -> list[str]:
    names = [label, CATALOG.get(label, (None, None, COCO_DE.get(label, ""), ""))[2], name_de or ""]
    if element:
        names += [element.get("name_de", "").rstrip(" 0123456789"), *element.get("aliases", [])]
    return list(dict.fromkeys(n for n in names if n and len(n) > 2))


def _phrase(text: str, names: list[str]) -> str | None:
    """The words of `text` that name the item (as spoken, e.g. "Stühle"), else None."""
    t = _norm(text)
    tokens = set(_WORD.findall(t))
    for n in sorted(names, key=len, reverse=True):
        if not _name_hit(t, tokens, n):
            continue
        nn = _norm(n)
        if _WORD.fullmatch(nn):
            forms = set(_plural_forms(nn))
            m = next((m for m in _WORD.finditer(text) if m.group(0).lower() in forms), None)
        else:
            m = re.search(re.escape(nn), text, re.I)
        if m and not (nn == "uhr" and _TIME_UHR.search(t)):
            return m.group(0)
    return None


def _state(text: str, el_type: str) -> tuple[str | None, str | None]:
    st = _state_for(text, el_type or "default")
    return st, (STATE_DE.get(st, st) if st else None)


def link_mentions(sfm: dict, transcript: dict | None, elements: dict[str, dict] | None = None,
                  activity_of: Callable[[str], str | None] | None = None) -> dict:
    elements = elements or {}
    objs = [dict(o) for o in sfm.get("objects") or []]
    by_label: dict[str, list[dict]] = {}
    for o in objs:
        o.update(mentioned=False, mention_times=[], spoken_state=None, spoken_phrase=None)
        if o.get("label") not in NOT_ITEMS:
            by_label.setdefault(o["label"], []).append(o)
    # vocabulary: every detected label (with its element's names) + the building catalogue for unseen items
    vocab: dict[str, dict] = {}
    for label, inst in by_label.items():
        el = next((elements.get(o.get("element_id")) for o in inst if o.get("element_id") in elements), None)
        vocab[label] = {"names": _names(label, inst[0].get("name_de"), el), "name_de": inst[0].get("name_de"),
                        "type": (el or {}).get("type") or CATALOG.get(label, ("", "", "", "default"))[3] or "default"}
    for label, (cat, ifc, name_de, etype) in CATALOG.items():
        if label not in vocab and ifc and cat not in ("people", "equipment"):
            vocab[label] = {"names": _names(label, name_de, None), "name_de": name_de, "type": etype or "default"}
    mentions, unseen = [], []
    for seg in (transcript or {}).get("segments", []):
        text, t0, t1 = seg.get("text", "").strip(), seg.get("start"), seg.get("end")
        if not text:
            continue
        hit_names: list[str] = []
        for label, v in vocab.items():
            phrase = _phrase(text, v["names"])
            if not phrase:
                continue
            hit_names.append(phrase.lower())
            state, state_de = _state(text, v["type"])
            inst = by_label.get(label)
            if not inst:
                unseen.append({"name": v["name_de"], "label": label, "phrase": phrase, "t": t0, "text": text,
                               "state": state, "state_de": state_de})
                continue
            near = [o for o in inst if o.get("first_t") is not None and t1 is not None and t0 is not None
                    and o["first_t"] - WINDOW_S <= t1 and t0 <= (o.get("last_t") or o["first_t"]) + WINDOW_S]
            chosen = near or inst
            eid = next((o["element_id"] for o in chosen if o.get("element_id")), None)
            mentions.append({"t_start": t0, "t_end": t1, "text": text, "phrase": phrase, "label": label,
                             "name_de": v["name_de"], "object_ids": [o["id"] for o in chosen], "element_id": eid,
                             "state": state, "state_de": state_de,
                             "activity_id": activity_of(eid) if (eid and activity_of) else None})
            for o in chosen:
                o["mentioned"] = True
                o["mention_times"].append(t0)
                o["spoken_phrase"] = o["spoken_phrase"] or phrase
                o["spoken_state"] = o["spoken_state"] or state
        # compounds with a building stem that no catalogue name covers ("Betonfassade", "Holzrahmen")
        for m in re.finditer(r"\b([A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ]?[a-zäöüß]+)*)\b", text):
            word, low = m.group(1), m.group(1).lower().replace("-", "")
            if len(low) < 5 or low in NOT_ELEMENTS or any(h in low or low in h for h in hit_names):
                continue
            stem = next((s for s in SPEECH_STEMS if s[0] in low), None)
            if stem:
                hit_names.append(low)
                state, state_de = _state(text, stem[3])
                unseen.append({"name": word, "label": None, "phrase": word, "t": t0, "text": text,
                               "state": state, "state_de": state_de})
    mentions.sort(key=lambda x: (x["t_start"] is None, x["t_start"] or 0))
    return {"mentions": mentions, "unseen_mentions": unseen, "objects": objs}
