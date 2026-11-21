"""Scan: turn what the vision models saw in a video into an inventory and, optionally, a new project.

inventory(vision) groups detections by label, estimates instance counts (max simultaneous boxes per frame),
and sorts each label into a category: structure, openings, finishes, building services (MEP), furniture,
equipment, people/safety. Building elements become project elements; equipment and people do not
(people give a labour estimate instead).

seed_from_scan(...) writes seed/projects/<name>/ (zones, elements, trades, activities, BoQ, mapping, project.json)
so the API can run on it with PROJECT=<name>. Elements carry the detection label as an alias, so later
captures propose progress from detections (vision proposes; voice confirms).
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

# label -> (category, IFC class, German name, element type for the state table)
CATALOG: dict[str, tuple[str, str | None, str, str]] = {
    "wall": ("structure", "IfcWall", "Wand", "wall"),
    "brick wall": ("structure", "IfcWall", "Mauerwerkswand", "wall"),
    "concrete column": ("structure", "IfcColumn", "Betonstütze", "default"),
    "steel beam": ("structure", "IfcBeam", "Stahlträger", "default"),
    "formwork": ("structure", "IfcElementAssembly", "Schalung", "default"),
    "rebar": ("structure", "IfcReinforcingBar", "Bewehrung", "default"),
    "stairs": ("structure", "IfcStair", "Treppe", "default"),
    "door": ("openings", "IfcDoor", "Tür", "default"),
    "window": ("openings", "IfcWindow", "Fenster", "default"),
    "ceiling": ("finishes", "IfcCovering", "Decke", "default"),
    "floor": ("finishes", "IfcCovering", "Boden", "floor"),
    "drywall panel": ("finishes", "IfcCovering", "Trockenbauplatte", "wall"),
    "insulation": ("finishes", "IfcCovering", "Dämmung", "default"),
    "pipe": ("services", "IfcFlowSegment", "Rohrleitung", "default"),
    "cable": ("services", "IfcCableSegment", "Kabel", "default"),
    "cable tray": ("services", "IfcCableCarrierSegment", "Kabeltrasse", "default"),
    "radiator": ("services", "IfcSpaceHeater", "Heizkörper", "default"),
    "socket": ("services", "IfcOutlet", "Steckdose", "default"),
    "light fixture": ("services", "IfcLightFixture", "Leuchte", "lighting"),
    "lighting truss": ("services", "IfcBeam", "Licht-Traverse", "lighting"),
    "speaker": ("services", "IfcFlowTerminal", "Lautsprecher", "av"),
    "projector": ("services", "IfcFlowTerminal", "Beamer", "av"),
    "projection screen": ("services", "IfcFlowTerminal", "Leinwand", "av"),
    "tv": ("services", "IfcFlowTerminal", "Bildschirm", "av"),
    "stage": ("structure", "IfcSlab", "Bühne", "stage"),
    "lectern": ("furniture", "IfcFurniture", "Rednerpult", "default"),
    "chair": ("furniture", "IfcFurniture", "Stuhl", "default"),
    "couch": ("furniture", "IfcFurniture", "Sofa", "default"),
    "bed": ("furniture", "IfcFurniture", "Bett", "default"),
    "dining table": ("furniture", "IfcFurniture", "Tisch", "default"),
    "bench": ("furniture", "IfcFurniture", "Bank", "default"),
    "potted plant": ("furniture", "IfcFurniture", "Pflanze", "default"),
    "refrigerator": ("furniture", "IfcFurniture", "Kühlschrank", "default"),
    "sink": ("services", "IfcSanitaryTerminal", "Waschbecken", "default"),
    "toilet": ("services", "IfcSanitaryTerminal", "WC", "default"),
    "scaffolding": ("equipment", None, "Gerüst", ""),
    "construction scaffolding": ("equipment", None, "Gerüst", ""),
    "robot": ("equipment", None, "Roboter", ""),
    "concrete pump": ("equipment", None, "Betonpumpe", ""),
    "gypsum board": ("finishes", "IfcCovering", "Gipskartonplatte", "wall"),
    "plywood board": ("finishes", "IfcCovering", "Holzplatte", "default"),
    "wooden frame": ("structure", "IfcMember", "Holzständerwerk", "default"),
    "ladder": ("equipment", None, "Leiter", ""),
    "crane": ("equipment", None, "Kran", ""),
    "excavator": ("equipment", None, "Bagger", ""),
    "concrete mixer": ("equipment", None, "Betonmischer", ""),
    "wheelbarrow": ("equipment", None, "Schubkarre", ""),
    "power tool": ("equipment", None, "Elektrowerkzeug", ""),
    "pallet": ("equipment", None, "Palette", ""),
    "truck": ("equipment", None, "Lkw", ""),
    "car": ("equipment", None, "Pkw", ""),
    "person": ("people", None, "Person", ""),
    "hard hat": ("people", None, "Schutzhelm", ""),
    "safety vest": ("people", None, "Warnweste", ""),
}
CATEGORY_DE = {"structure": "Rohbau", "openings": "Öffnungen", "finishes": "Ausbau", "services": "Technik (TGA)",
               "furniture": "Ausstattung", "equipment": "Geräte", "people": "Personen", "other": "Sonstiges"}
ACTIVITY_ORDER = ["structure", "openings", "services", "finishes", "furniture"]
MAX_INSTANCES = 12  # per label, so one busy frame cannot flood the project

# German building stems found inside compound nouns ("Betonfassade", "Leibungsblech", "Holzrahmen-Elemente")
# -> (category, IFC class, element type). Order matters: first matching stem wins.
SPEECH_STEMS: list[tuple[str, str, str, str]] = [
    ("fassade", "finishes", "IfcCovering", "wall"), ("dämmung", "finishes", "IfcCovering", "default"),
    ("schaum", "finishes", "IfcCovering", "default"), ("putz", "finishes", "IfcCovering", "wall"),
    ("estrich", "finishes", "IfcCovering", "floor"), ("belag", "finishes", "IfcCovering", "floor"),
    ("fliese", "finishes", "IfcCovering", "default"), ("blech", "finishes", "IfcCovering", "default"),
    ("beschichtung", "finishes", "IfcCovering", "default"), ("verkleidung", "finishes", "IfcCovering", "default"),
    ("fenster", "openings", "IfcWindow", "default"), ("tür", "openings", "IfcDoor", "default"),
    ("leibung", "openings", "IfcCovering", "default"), ("laibung", "openings", "IfcCovering", "default"),
    ("wand", "structure", "IfcWall", "wall"), ("wände", "structure", "IfcWall", "wall"),
    ("decke", "structure", "IfcSlab", "default"), ("dach", "structure", "IfcRoof", "default"),
    ("stütze", "structure", "IfcColumn", "default"), ("träger", "structure", "IfcBeam", "default"),
    ("fundament", "structure", "IfcFooting", "default"), ("treppe", "structure", "IfcStair", "default"),
    ("balkon", "structure", "IfcSlab", "default"), ("brüstung", "structure", "IfcWall", "wall"),
    ("rahmen", "structure", "IfcMember", "default"), ("element", "structure", "IfcElementAssembly", "default"),
    ("schalung", "structure", "IfcElementAssembly", "default"), ("bewehrung", "structure", "IfcReinforcingBar", "default"),
    ("leitung", "services", "IfcFlowSegment", "default"), ("rohr", "services", "IfcFlowSegment", "default"),
    ("kabel", "services", "IfcCableSegment", "default"), ("heizung", "services", "IfcSpaceHeater", "default"),
    ("lüftung", "services", "IfcFlowSegment", "default"), ("boden", "finishes", "IfcCovering", "floor"),
]
NOT_ELEMENTS = {"zustand", "endzustand", "bestand", "stockwerk", "zeit", "seite", "oberfläche"}


def speech_terms(transcript: dict | None) -> list[dict]:
    """Building terms named in the transcript, one item per distinct term (first mention wins)."""
    import re

    out: dict[str, dict] = {}
    for seg in (transcript or {}).get("segments", []):
        for m in re.finditer(r"\b([A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ]?[a-zäöüß]+)*)\b", seg["text"]):
            word = m.group(1)
            low = word.lower().replace("-", "")
            if len(low) < 5 or low in NOT_ELEMENTS:
                continue
            stem = next((s for s in SPEECH_STEMS if s[0] in low), None)
            if not stem:
                continue
            key = low.rstrip("n").rstrip("e") if low.endswith(("en", "e")) and len(low) > 7 else low
            if key in out:
                out[key]["mentions"] += 1
                continue
            cat, ifc, etype = stem[1], stem[2], stem[3]
            out[key] = {"label": word.lower(), "category": cat, "category_de": CATEGORY_DE[cat], "ifc_class": ifc,
                        "name_de": word, "type": etype, "frames": 0, "instances": 1, "first_t": seg["start"],
                        "last_t": seg["end"], "best_conf": 1.0, "best": None, "sources": ["speech"],
                        "mentions": 1, "quote": seg["text"].strip()[:160]}
    return list(out.values())


def inventory(vision: dict, min_conf: float = 0.3, min_frames: int = 2, transcript: dict | None = None) -> dict:
    """Group detections by label. A label must be seen in >= min_frames frames (or be a marker) to count."""
    per_label: dict[str, dict] = defaultdict(lambda: {"frames": 0, "max_per_frame": 0, "first_t": None,
                                                      "last_t": None, "best_conf": 0.0, "best": None,
                                                      "sources": set()})
    n_frames = len(vision.get("frames", []))
    for f in vision.get("frames", []):
        counts: dict[str, int] = defaultdict(int)
        for o in f["objects"]:
            if o["conf"] < min_conf or o["source"] == "marker":
                continue
            counts[o["label"]] += 1
            rec = per_label[o["label"]]
            rec["sources"].add(o["source"])
            if o["conf"] > rec["best_conf"]:
                rec["best_conf"], rec["best"] = o["conf"], {"media_path": f["media_path"], "t": f["t"],
                                                            "bbox": o["bbox"]}
        for label, c in counts.items():
            rec = per_label[label]
            rec["frames"] += 1
            rec["max_per_frame"] = max(rec["max_per_frame"], c)
            if f["t"] is not None:
                rec["first_t"] = f["t"] if rec["first_t"] is None else min(rec["first_t"], f["t"])
                rec["last_t"] = f["t"] if rec["last_t"] is None else max(rec["last_t"], f["t"])
    items = []
    for label, rec in per_label.items():
        if rec["frames"] < min(min_frames, max(1, n_frames)):
            continue
        cat, ifc, name_de, etype = CATALOG.get(label, ("other", None, label.capitalize(), ""))
        items.append({"label": label, "category": cat, "category_de": CATEGORY_DE[cat], "ifc_class": ifc,
                      "name_de": name_de, "type": etype, "frames": rec["frames"],
                      "instances": min(rec["max_per_frame"], MAX_INSTANCES), "first_t": rec["first_t"],
                      "last_t": rec["last_t"], "best_conf": round(rec["best_conf"], 3), "best": rec["best"],
                      "sources": sorted(rec["sources"])})
    seen_labels = {i["label"] for i in items}
    items += [t for t in speech_terms(transcript) if t["label"] not in seen_labels]
    items.sort(key=lambda i: (list(CATEGORY_DE).index(i["category"]), -i["frames"]))
    people = next((i["instances"] for i in items if i["label"] == "person"), 0)
    by_cat: dict[str, list[str]] = defaultdict(list)
    for i in items:
        by_cat[i["category_de"]].append(f"{i['instances']}× {i['name_de']}")
    return {"capture_id": vision.get("capture_id"), "frames": n_frames, "items": items,
            "transcript": " ".join(s["text"] for s in (transcript or {}).get("segments", [])) or None,
            "summary": dict(by_cat), "people_max": people,
            "element_count": sum(i["instances"] for i in items if i["ifc_class"])}


def seed_from_scan(inv: dict, out: Path, name: str, start: date, zone_name: str = "Baustelle",
                   lat: float = 48.137, lon: float = 11.575) -> dict:
    """Write a minimal Tagwerk project from an inventory. Activities = one per element category present,
    finish-to-start in a typical order, 5 working days each from `start`."""
    out.mkdir(parents=True, exist_ok=True)
    zid = "Z-SITE"
    elems = []
    for item in inv["items"]:
        if not item["ifc_class"]:
            continue
        for k in range(1, item["instances"] + 1):
            slug = item["label"].upper().replace(" ", "-")
            label = item["name_de"] if item["instances"] == 1 else f"{item['name_de']} {k}"
            slug = re.sub(r"[^A-Z0-9-]", "", slug.replace("Ä", "AE").replace("Ö", "OE").replace("Ü", "UE")
                          .replace("ß", "SS"))
            elems.append({"element_id": f"S-{slug}-{k}", "ifc_class": item["ifc_class"],
                          "name_de": label, "name_en": f"{item['label']} {k}",
                          "type": item["type"] or "default", "category": item["category"],
                          "aliases": [item["label"], item["name_de"]]})
    with (out / "zones.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["zone_id", "name_de", "name_en", "kind", "storey", "aliases"])
        w.writerow([zid, zone_name, "Site", "site", "", ""])
    with (out / "elements.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["element_id", "global_id", "ifc_class", "name_de", "name_en", "zone", "x", "y", "z", "dx", "dy",
                    "dz", "qty", "unit", "din276", "marker_id", "type", "aliases"])
        for e in elems:
            w.writerow([e["element_id"], "", e["ifc_class"], e["name_de"], e["name_en"], zid, 0, 0, 0, 0, 0, 0, 1,
                        "Stk", "", "", e["type"], "|".join(e["aliases"])])
    cats = [c for c in ACTIVITY_ORDER if any(e["category"] == c for e in elems)]
    trades = {"structure": ("T-ROH", "Rohbau"), "openings": ("T-FEN", "Fenster/Türen"),
              "services": ("T-TGA", "TGA"), "finishes": ("T-AUS", "Ausbau"), "furniture": ("T-AUSST", "Ausstattung")}
    with (out / "trades.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["trade_id", "name", "rate_eur_h"])
        for c in cats:
            w.writerow([*trades[c], 0])
    with (out / "wbs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["wbs", "name"])
        w.writerow(["1", "Scan"])
    acts, d = [], start
    for i, c in enumerate(cats):
        days = []
        while len(days) < 5:
            if d.weekday() < 5:
                days.append(d)
            d += timedelta(days=1)
        acts.append({"id": f"A{(i + 1) * 10:03d}", "cat": c, "start": days[0], "finish": days[-1],
                     "pred": acts[-1]["id"] if acts else ""})
    with (out / "activities.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["activity_id", "wbs", "name", "trade_id", "planned_start", "planned_finish", "crew_planned",
                    "predecessors"])
        for a in acts:
            w.writerow([a["id"], "1", CATEGORY_DE[a["cat"]], trades[a["cat"]][0], a["start"].isoformat(),
                        a["finish"].isoformat(), 2, a["pred"]])
    with (out / "boq.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["oz", "lot", "short_text", "qty", "unit", "unit_price", "din276"])
        for a in acts:
            w.writerow([f"S.{a['id']}", "Scan", CATEGORY_DE[a["cat"]],
                        sum(1 for e in elems if e["category"] == a["cat"]), "Stk", 0, ""])
    with (out / "mapping.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["oz", "activity_id", "element_id", "share", "from_state", "to_state"])
        for a in acts:
            mine = [e for e in elems if e["category"] == a["cat"]]
            for e in mine:
                w.writerow([f"S.{a['id']}", a["id"], e["element_id"], round(1 / len(mine), 6), "", ""])
    meta = {"id": f"P-{name.upper()[:6]}", "name": f"Scan: {name}", "data_date": start.isoformat(), "lat": lat,
            "lon": lon, "source": f"generated from scan of capture {inv.get('capture_id')}",
            "scan_summary": inv["summary"], "people_max": inv["people_max"]}
    (out / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "inventory.json").write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"elements": len(elems), "activities": len(acts), "dir": str(out)}
