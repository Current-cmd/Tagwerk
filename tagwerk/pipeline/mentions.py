"""Scan 3D "Gesagt": link what the speaker names in the walkthrough to the 3D objects and the moment it is said.

link_mentions(sfm, transcript, elements, activity_of) -> {"mentions", "unseen_mentions", "objects"} where
  mentions:        per transcript segment and named item {t (estimated second of the phrase), t_start, t_end,
                   text, phrase, label, name_de, object_ids, element_id, state, state_de, activity_id}
  unseen_mentions: building items named but not detected in the clip {name, phrase, t, times, text, state, state_de}
  objects:         the sfm objects with mentioned / mention_times / spoken_state(_de) / spoken_phrase added
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
from tagwerk.pipeline.structure import _WORD, FUTURE_WORDS, _has, _name_hit, _norm, _plural_forms, _state_for

WINDOW_S = 4.0  # an object counts as "the one meant" if it was seen within this many seconds of the phrase
NOT_ITEMS = {"person", "hard hat", "safety vest"}  # labour, not items (structure.py handles crews and absences)
_TIME_UHR = re.compile(r"\d\s*uhr\b")
# everyday English names of catalogue labels (walkthroughs in English: "the tables over here", "slab has been placed")
EN_ALIASES = {"dining table": ["table", "desk"], "tv": ["screen", "monitor", "display"], "projection screen": ["screen"],
              "light fixture": ["light", "lamp"], "concrete column": ["column", "pillar"], "potted plant": ["plant"],
              "refrigerator": ["fridge"], "trash can": ["dustbin", "bin", "trash", "garbage can"], "couch": ["sofa"],
              "floor": ["slab", "flooring"], "steel beam": ["beam"], "drywall panel": ["drywall"],
              "cable tray": ["tray"], "lectern": ["podium"], "speaker": ["loudspeaker"], "stairs": ["staircase"]}
# named but never a detection label: (English/German word -> German name) for unseen_mentions
UNSEEN_TERMS = {"storage": "Lager", "lager": "Lager", "lagerfläche": "Lager"}
FUTURE_EN = ["have to", "has to", "need to", "needs to", "must be", "should be", "not yet", "noch nicht"]
_CLAUSE = re.compile(r"[,;.!?]|\s(?:und|aber|and|but)\s")


def _names(label: str, name_de: str | None, element: dict | None) -> list[str]:
    names = [label, CATALOG.get(label, (None, None, COCO_DE.get(label, ""), ""))[2], name_de or "",
             *EN_ALIASES.get(label, [])]
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


def _pos(text: str, phrase: str) -> int:
    i = text.lower().find(phrase.lower())
    return i if i >= 0 else 0


def _span(text: str, pos: int, others: list[int]) -> str:
    """What is said about the item at `pos`: from the start of its clause to the next named item ("Tür, die ist
    eingebaut" / "tables over here, they have to be put," / "slab has been placed")."""
    begin = max([0, *(m.end() for m in _CLAUSE.finditer(text, 0, pos))])
    end = min([len(text), *(o for o in others if o > pos)])
    return text[begin:end]


def _state(span: str, el_type: str) -> tuple[str | None, str | None]:
    """State said in the span; "have to / muss noch / noch nicht" means still to do: no state."""
    if any(_has(_norm(span), w) for w in [*FUTURE_WORDS, *FUTURE_EN]):
        return None, None
    st = _state_for(span, el_type or "default")
    return st, (STATE_DE.get(st, st) if st else None)


def _hits(text: str, vocab: dict[str, dict]) -> list[dict]:
    """Every item named in one segment, once: catalogue/element names, unseen terms, building-stem compounds."""
    hits, said = [], []
    for label, v in vocab.items():
        phrase = _phrase(text, v["names"])
        if phrase:
            said.append(phrase.lower())
            hits.append({"label": label, "name": v["name_de"], "phrase": phrase, "type": v["type"]})
    for m in _WORD.finditer(text):  # named places/things that are never a detection ("storage")
        low = m.group(0).lower()
        if low in UNSEEN_TERMS and low not in said:
            said.append(low)
            hits.append({"label": None, "name": UNSEEN_TERMS[low], "phrase": m.group(0), "type": "default"})
    # compounds with a building stem that no catalogue name covers ("Betonfassade", "Holzrahmen")
    for m in re.finditer(r"\b([A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ]?[a-zäöüß]+)*)\b", text):
        word, low = m.group(1), m.group(1).lower().replace("-", "")
        if len(low) < 5 or low in NOT_ELEMENTS or any(h in low or low in h for h in said):
            continue
        stem = next((st for st in SPEECH_STEMS if st[0] in low), None)
        if stem:
            said.append(low)
            hits.append({"label": None, "name": word, "phrase": word, "type": stem[3]})
    for h in hits:
        h["pos"] = _pos(text, h["phrase"])
    for h in hits:
        h["state"], h["state_de"] = _state(_span(text, h["pos"], [o["pos"] for o in hits]), h["type"])
    return hits


def link_mentions(sfm: dict, transcript: dict | None, elements: dict[str, dict] | None = None,
                  activity_of: Callable[[str], str | None] | None = None) -> dict:
    elements = elements or {}
    objs = [dict(o) for o in sfm.get("objects") or []]
    by_label: dict[str, list[dict]] = {}
    for o in objs:
        o.update(mentioned=False, mention_times=[], spoken_state=None, spoken_state_de=None, spoken_phrase=None)
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
        for h in sorted(_hits(text, vocab), key=lambda h: h["pos"]):
            # Whisper segments can be long (45 s): place the phrase by its position in the text
            t = round(t0 + (t1 - t0) * h["pos"] / len(text), 2) if t0 is not None and t1 is not None else t0
            inst = by_label.get(h["label"]) if h["label"] else None
            if not inst:  # one entry per name, every time it was said
                u = next((x for x in unseen if x["name"] == h["name"]), None)
                if u is None:
                    unseen.append({"name": h["name"], "label": h["label"], "phrase": h["phrase"], "t": t, "times": [t],
                                   "text": text, "state": h["state"], "state_de": h["state_de"]})
                else:
                    u["times"].append(t)
                    if h["state"] and not u["state"]:
                        u["state"], u["state_de"] = h["state"], h["state_de"]
                continue
            near = [o for o in inst if o.get("first_t") is not None and t is not None
                    and o["first_t"] - WINDOW_S <= t <= (o.get("last_t") or o["first_t"]) + WINDOW_S]
            chosen = near or inst
            eid = next((o["element_id"] for o in chosen if o.get("element_id")), None)
            mentions.append({"t": t, "t_start": t0, "t_end": t1, "text": text, "phrase": h["phrase"], "label": h["label"],
                             "name_de": h["name"], "object_ids": [o["id"] for o in chosen], "element_id": eid,
                             "state": h["state"], "state_de": h["state_de"],
                             "activity_id": activity_of(eid) if (eid and activity_of) else None})
            for o in chosen:
                o["mentioned"] = True
                o["mention_times"].append(t)
                o["spoken_phrase"] = o["spoken_phrase"] or h["phrase"]
                if not o["spoken_state"] and h["state"]:
                    o["spoken_state"], o["spoken_state_de"] = h["state"], h["state_de"]
    mentions.sort(key=lambda x: (x["t_start"] is None, x["t_start"] or 0))
    return {"mentions": mentions, "unseen_mentions": unseen, "objects": objs}


def for_capture(sfm: dict, cache_dir, project=None) -> dict:
    """link_mentions with cache/<cid>/speech.json and the project's elements/activities (missing pieces -> empty)."""
    import json
    from pathlib import Path

    try:
        tr = json.loads((Path(cache_dir) / sfm.get("capture_id", "") / "speech.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tr = None
    elements = project.elements if project is not None else {}

    def activity_of(eid: str) -> str | None:
        acts = project.activities_of(eid) if project is not None and eid in elements else []
        return acts[0] if acts else None

    return link_mentions(sfm, tr, elements, activity_of)
