"""Import the Schependomlaan open BIM dataset as a second Tagwerk project (real data test).

    python scripts/import_schependomlaan.py --data ~/Developer/datasets/schependomlaan \
        --out seed/projects/schependomlaan

Sources (github.com/openBIMstandards/Archive-DataSetSchependomlaan, CC BY 4.0, academic use):
- Design model IFC (ArchiCAD, IFC2X3): storeys, GlobalIds, names, layers
- "IFC Schependomlaan incl planningsdata.ifc" (Synchro export): IfcTask + IfcScheduleTimeControl (planned
  dates), IfcRelSequence (links), IfcRelAssignsToProcess (task -> elements)
- MS Project XML: section headers (UITVOERING, GEVEL, DAK, AFBOUW, OPLEVEREN) as WBS, UIDs for traceability
- Weekly as-planned IFCs (weeks 26-30): which elements exist at each date. The dataset has no as-built data,
  so these 4D planning snapshots stand in as progress evidence (labelled as such in every capture).

Join key between the files is the ArchiCAD Unique ID in `Tag` (Synchro regenerates GlobalIds on export).
The Synchro catch-all task "Afbouw" (linked to every element) is dropped.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue

SKIP_CLASSES = {"IfcOpeningElement", "IfcVirtualElement", "IfcSpace"}
CATCH_ALL = {"afbouw"}
STOREYS = [  # design storey name -> zone
    ("-1 fundering", "Z-FUND", "Fundering", "Foundation", ["fundering", "foundation", "kelder"]),
    ("00 begane grond", "Z-BG", "Begane grond", "Ground floor", ["begane grond", "bg", "ground floor"]),
    ("01 eerste verdieping", "Z-1", "Eerste verdieping", "First floor", ["eerste verdieping", "1e verdieping",
                                                                         "first floor"]),
    ("02 tweede verdieping", "Z-2", "Tweede verdieping", "Second floor", ["tweede verdieping", "2e verdieping",
                                                                          "second floor"]),
    ("03 derde verdieping", "Z-3", "Derde verdieping", "Third floor", ["derde verdieping", "3e verdieping",
                                                                       "third floor"]),
    ("04 dak", "Z-DAK", "Dak", "Roof", ["dak", "roof", "zolder"]),
]
WEEKS = [(26, "2015-06-26"), (27, "2015-07-03"), (28, "2015-07-10"), (29, "2015-07-17"), (30, "2015-07-24")]
DATA_DATE = "2015-07-24"  # forecast "today" = the week-30 snapshot
CLASS_EN = {"IfcWall": "Wall", "IfcWallStandardCase": "Wall", "IfcSlab": "Slab", "IfcCovering": "Covering",
            "IfcWindow": "Window", "IfcDoor": "Door", "IfcBeam": "Beam", "IfcColumn": "Column",
            "IfcRailing": "Railing", "IfcStair": "Stair", "IfcMember": "Member", "IfcBuildingElementPart": "Part",
            "IfcFlowSegment": "Pipe/duct", "IfcBuildingElementProxy": "Object", "IfcDistributionElement": "Installation"}
TRADES = [  # (trade id, Dutch name, keywords in task names)
    ("T-METSEL", "Metselaar", ["metselwerk", "lijmwerk", "stelwerk", "kalkzandsteen", "gevel"]),
    ("T-BETON", "Betonwerker", ["stort", "wapening", "bekist", "fundering", "werkvloer", "opstort", "randkist",
                                "afstorten", "poeren", "bodemafsluiting"]),
    ("T-MONTAGE", "Montage", ["breedplaat", "kanaalplaat", "prefab", "trappen", "stalen", "staal", "kolommen",
                              "balken", "opstellen", "bruggetjes"]),
    ("T-TIMMER", "Timmerman", ["kozijn", "scharnierkap", "hsb", "dakkapel", "houtskelet", "kap"]),
    ("T-DAK", "Dakdekker", ["dakpannen", "zink", "goot", "dakbedekking", "dakrand"]),
    ("T-INSTALL", "Installateur", ["installat", "nuts", "elektra", "riolering", "leiding"]),
    ("T-GROND", "Grondwerk", ["grondwerk", "uitzetten", "maatvoering", "bouwketen", "keet"]),
    ("T-ALG", "Algemeen", []),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def clean_name(name: str | None) -> str:
    return re.sub(r"_\(#\d+\)$", "", (name or "").strip()) or "element"


def ifc_date(v) -> date | None:
    """IFC2X3 IfcDateTimeSelect (IfcDateAndTime / IfcCalendarDate) or ISO string -> date."""
    if v is None:
        return None
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    if v.is_a("IfcDateAndTime"):
        v = v.DateComponent
    if v.is_a("IfcCalendarDate"):
        return date(v.YearComponent, v.MonthComponent, v.DayComponent)
    return None


def trade_for(task_name: str) -> str:
    n = task_name.lower()
    for tid, _, words in TRADES:
        if any(w in n for w in words):
            return tid
    return "T-ALG"


# ---------------------------------------------------------------- readers

def read_design(path: Path) -> dict[str, dict]:
    log(f"design IFC {path.name}")
    f = ifcopenshell.open(str(path))
    zone_of = {s[0]: s[1] for s in STOREYS}
    out = {}
    for el in f.by_type("IfcElement"):
        if el.is_a() in SKIP_CLASSES or not el.Tag:
            continue
        cont = ue.get_container(el)
        zone = zone_of.get(cont.Name if cont else "")
        if not zone:
            continue  # ArchiCAD artefact containers ("6.06", "A0.00", ...)
        props = ue.get_psets(el).get("ArchiCADProperties", {})
        out[el.Tag] = {"global_id": el.GlobalId, "ifc_class": el.is_a(), "name": clean_name(el.Name), "zone": zone,
                       "layer": props.get("Layer") or "",
                       "material": props.get("Building Material / Composite / Profile / Fill") or ""}
    log(f"  {len(out)} tagged elements on the 6 storeys")
    return out


def read_schedule(path: Path) -> tuple[dict, dict, list]:
    """-> tasks {task_id: {...}}, task_elements {task_id: [tags]}, sequences [(pred, succ, type)]"""
    log(f"Synchro IFC {path.name}")
    f = ifcopenshell.open(str(path))
    times = {}
    for rel in f.by_type("IfcRelAssignsTasks"):
        tc = rel.TimeForTask
        for t in rel.RelatedObjects:
            times[t.id()] = (ifc_date(tc.ScheduleStart), ifc_date(tc.ScheduleFinish))
    tasks = {}
    for t in f.by_type("IfcTask"):
        start, finish = times.get(t.id(), (None, None))
        if not start or not finish:
            continue
        tasks[t.TaskId] = {"task_id": t.TaskId, "name": (t.Name or "").strip(), "start": start, "finish": finish,
                           "_eid": t.id()}
    by_eid = {v["_eid"]: k for k, v in tasks.items()}
    task_elements: dict[str, list[str]] = defaultdict(list)
    for rel in f.by_type("IfcRelAssignsToProcess"):
        tid = by_eid.get(rel.RelatingProcess.id())
        if not tid:
            continue
        for o in rel.RelatedObjects:
            if o.is_a("IfcElement") and o.Tag:
                task_elements[tid].append(o.Tag)
    seq = []
    for rel in f.by_type("IfcRelSequence"):
        a, b = by_eid.get(rel.RelatingProcess.id()), by_eid.get(rel.RelatedProcess.id())
        if a and b:
            seq.append((a, b, "SS" if (rel.SequenceType or "").upper() == "START_START" else "FS"))
    log(f"  {len(tasks)} tasks, {sum(len(v) for v in task_elements.values())} task-element links, {len(seq)} links")
    return tasks, task_elements, seq


def read_msp(path: Path) -> list[dict]:
    ns = {"p": "http://schemas.microsoft.com/project"}
    root = ET.parse(path).getroot()
    out, section = [], "UITVOERING"
    for t in root.findall("p:Tasks/p:Task", ns):
        name = (t.findtext("p:Name", "", ns) or "").strip()
        start = (t.findtext("p:Start", "", ns) or "")[:10]
        dur = t.findtext("p:Duration", "", ns) or ""
        if name.isupper() and name in ("UITVOERING", "GEVEL", "DAK", "AFBOUW", "OPLEVEREN"):
            section = name
            continue
        if not name or dur in ("PT0H0M0S", ""):
            continue
        out.append({"uid": t.findtext("p:UID", "", ns), "name": name, "start": start, "section": section,
                    "wbs": t.findtext("p:WBS", "", ns)})
    log(f"MS Project: {len(out)} real tasks")
    return out


def tags_in(path: Path) -> set[str]:
    log(f"week IFC {path.name}")
    f = ifcopenshell.open(str(path))
    return {e.Tag for e in f.by_type("IfcElement") if e.Tag and e.is_a() not in SKIP_CLASSES}


def find(folder: Path, pattern: str) -> Path:
    hits = sorted(folder.glob(pattern))
    if not hits:
        sys.exit(f"missing {folder}/{pattern}")
    return hits[0]


# ---------------------------------------------------------------- build

def build(data: Path, out: Path) -> dict:
    design = read_design(find(data / "Design model IFC", "*.ifc"))
    tasks, task_elements, seq = read_schedule(data / "As Planned models" / "IFC Schependomlaan incl planningsdata.ifc")
    msp = read_msp(find(data / "Planning" / "XML", "*.xml"))

    # drop the catch-all and tasks without a name AND without elements
    for tid in [t for t, v in tasks.items() if v["name"].lower() in CATCH_ALL]:
        log(f"  dropping catch-all task {tid} {tasks[tid]['name']} ({len(task_elements.get(tid, []))} elements)")
        tasks.pop(tid)
        task_elements.pop(tid, None)
    for tid in [t for t, v in tasks.items() if not v["name"] and not task_elements.get(t)]:
        tasks.pop(tid)

    # MS Project match: name + start date, else name only
    by_name_start = {(m["name"].lower(), m["start"]): m for m in msp}
    by_name = defaultdict(list)
    for m in msp:
        by_name[m["name"].lower()].append(m)
    matched = 0
    for t in tasks.values():
        m = by_name_start.get((t["name"].lower(), t["start"].isoformat()))
        if not m and by_name.get(t["name"].lower()):
            m = min(by_name[t["name"].lower()], key=lambda x: abs((date.fromisoformat(x["start"]) - t["start"]).days))
        t["msp_uid"], t["section"] = (m["uid"], m["section"]) if m else ("", "UITVOERING")
        matched += bool(m)
        if not t["name"]:
            t["name"] = f"Taak {t['task_id']}"
    log(f"  {matched}/{len(tasks)} tasks matched to MS Project")

    # elements: tagged, in the design model, linked to at least one kept task
    linked = {tag for tid in tasks for tag in task_elements.get(tid, [])}
    tags = sorted(tag for tag in linked if tag in design)
    ids: dict[str, str] = {}
    for tag in tags:
        short = "SP-" + tag.replace("-", "")[:8]
        while short in ids.values():
            short += "x"
        ids[tag] = short
    storey_label = {s[1]: s[2] for s in STOREYS}
    name_count = Counter((design[t]["name"], design[t]["zone"]) for t in tags)
    seen = Counter()

    out.mkdir(parents=True, exist_ok=True)
    with (out / "zones.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["zone_id", "name_de", "name_en", "kind", "storey", "aliases"])
        for _, zid, nl, en, aliases in STOREYS:
            w.writerow([zid, nl, en, "storey", f"ST-{zid}", "|".join(aliases)])
    with (out / "elements.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["element_id", "global_id", "ifc_class", "name_de", "name_en", "zone", "x", "y", "z", "dx", "dy",
                    "dz", "qty", "unit", "din276", "marker_id", "type", "aliases"])
        for tag in tags:
            d = design[tag]
            key = (d["name"], d["zone"])
            seen[key] += 1
            nr = f" {seen[key]}" if name_count[key] > 1 else ""
            label = f"{d['name']}{nr} ({storey_label[d['zone']]})"
            en = f"{CLASS_EN.get(d['ifc_class'], d['ifc_class'][3:])} {d['name']}{nr} ({d['zone']})"
            layer = re.sub(r"^\d+[_ ]*", "", d["layer"]).split(" - ")[0].strip()
            aliases = sorted({d["name"], layer} - {""})
            w.writerow([ids[tag], d["global_id"], d["ifc_class"], label, en, d["zone"], 0, 0, 0, 0, 0, 0, 1, "Stk",
                        "", "", "default", "|".join(aliases)])
    with (out / "trades.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["trade_id", "name", "rate_eur_h"])
        for tid, name, _ in TRADES:
            w.writerow([tid, name, 0])
    sections = ["UITVOERING", "GEVEL", "DAK", "AFBOUW", "OPLEVEREN"]
    with (out / "wbs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["wbs", "name"])
        for i, s in enumerate(sections, 1):
            w.writerow([str(i), s.capitalize()])
    preds = defaultdict(list)
    for a, b, typ in seq:
        if a in tasks and b in tasks:
            preds[b].append(a if typ == "FS" else f"{a}:SS")
    with (out / "activities.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["activity_id", "wbs", "name", "trade_id", "planned_start", "planned_finish", "crew_planned",
                    "predecessors", "msp_uid"])
        for tid in sorted(tasks):
            t = tasks[tid]
            w.writerow([tid, str(sections.index(t["section"]) + 1), t["name"], trade_for(t["name"]),
                        t["start"].isoformat(), t["finish"].isoformat(), 2, ";".join(preds.get(tid, [])),
                        t["msp_uid"]])
    # no prices in the dataset: one unpriced pseudo position per task keeps the BoQ -> activity -> element chain
    with (out / "boq.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["oz", "lot", "short_text", "qty", "unit", "unit_price", "din276"])
        for tid in sorted(tasks):
            w.writerow([f"SP.{tid}", tasks[tid]["section"].capitalize(), tasks[tid]["name"],
                        len([x for x in task_elements.get(tid, []) if x in ids]) or 1, "Stk", 0, ""])
    with (out / "mapping.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["oz", "activity_id", "element_id", "share", "from_state", "to_state"])
        for tid in sorted(tasks):
            els = sorted({ids[x] for x in task_elements.get(tid, []) if x in ids})
            if not els:
                w.writerow([f"SP.{tid}", tid, "", 1, "", ""])
            for e in els:
                w.writerow([f"SP.{tid}", tid, e, round(1 / len(els), 6), "", "installed"])

    # history from the weekly 4D snapshots
    elem_tasks = defaultdict(list)
    for tid in tasks:
        for tag in task_elements.get(tid, []):
            if tag in ids:
                elem_tasks[ids[tag]].append(tid)
    week_sets = {}
    for wk, _ in WEEKS:
        week_sets[wk] = {ids[t] for t in tags_in(find(data / "As Planned models", f"Week {wk} *.ifc")) if t in ids}
    first_wk, first_date = WEEKS[0]
    hist = {"initial": {"date": first_date, "states": {e: "installed" for e in sorted(week_sets[first_wk])},
                        "manual_pct": {}},
            "days": [], "source": "Synchro 4D as-planned snapshots (no as-built data in the dataset)"}
    prev = week_sets[first_wk]
    for wk, d in WEEKS[1:]:
        new = sorted(week_sets[wk] - prev)
        prev = week_sets[wk]
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        dd = date.fromisoformat(d)
        for e in new:
            started = [t for t in elem_tasks[e] if tasks[t]["start"] <= dd] or elem_tasks[e]
            tid = max(started, key=lambda t: tasks[t]["start"])
            groups[(tid, "installed")].append(e)
        captures = []
        for i, ((tid, state), els) in enumerate(sorted(groups.items())):
            captures.append({
                "capture_id": f"sp-w{wk}-{i:02d}", "zone_id": _zone_of(els, out), "ts": f"{d}T15:00:00Z",
                "note": f"4D-Planungsstand Woche {wk} (Synchro): {tasks[tid]['name']}",
                "structured": {"labour_present": [], "absences": [], "material_delivered": [], "special_events": [],
                               "unmatched": [],
                               "work_done": [{"element_ids": els, "activity_id": tid, "state_proposed": state,
                                              "evidence": "voice",
                                              "quote": f"Synchro week {wk}: {len(els)} elements of {tasks[tid]['name']}",
                                              "t": None}]}})
        hist["days"].append({"date": d, "captures": captures})
        log(f"  week {wk}: {len(new)} new elements in {len(captures)} task groups")
    (out / "history.json").write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")

    meta = {"id": "P-SP", "name": "Schependomlaan Nijmegen (10 Appartementen)", "client": "Hendriks Bouw en Ontwikkeling",
            "site": "Schependomlaan, Nijmegen", "building": "10 Appartementen Schependomlaan",
            "lat": 51.8426, "lon": 5.8378, "data_date": DATA_DATE, "lang": "nl",
            "storeys": [{"id": f"ST-{zid}", "name": nl, "elevation": elev}
                        for (_, zid, nl, _, _), elev in zip(STOREYS, [-1.0, 0.0, 3.0, 6.0, 9.0, 12.0])],
            "source": "github.com/openBIMstandards/Archive-DataSetSchependomlaan (CC BY 4.0, (C) original owners; "
                      "academic use)",
            "progress_evidence": hist["source"],
            "demo_replays": [{"id": "sp-demo-roof",
                              "label": "Notiz: Sporenkap derde verdieping geplaatst, 2× Timmerman ziek"}]}
    (out / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "ATTRIBUTION.md").write_text(
        "Data: Schependomlaan open BIM dataset, github.com/openBIMstandards/Archive-DataSetSchependomlaan.\n"
        "(C) original owners (Hendriks Bouw en Ontwikkeling, ROOT, TNO, RAAMAC; thesis S. van Schaijk, TU Eindhoven),\n"
        "licensed CC BY 4.0; the owners permit scientific and academic use. Derived files in this folder were generated\n"
        "by scripts/import_schependomlaan.py. Progress history = Synchro 4D as-planned snapshots, not as-built data.\n",
        encoding="utf-8")
    stats = {"elements": len(tags), "tasks": len(tasks), "links": sum(len(v) for v in task_elements.values()),
             "sequences": len(seq), "msp_matched": matched, "weeks": {wk: len(s) for wk, s in week_sets.items()}}
    log(f"done: {stats}")
    return stats


def _zone_of(element_ids: list[str], out: Path) -> str:
    """Most common zone among the elements (read back from the elements.csv just written)."""
    global _ZONES
    try:
        _ZONES  # noqa: B018 - existence check for the module cache
    except NameError:
        with (out / "elements.csv").open(encoding="utf-8") as fh:
            _ZONES = {r["element_id"]: r["zone"] for r in csv.DictReader(fh)}
    return Counter(_ZONES[e] for e in element_ids).most_common(1)[0][0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path.home() / "Developer/datasets/schependomlaan")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "seed/projects/schependomlaan")
    a = ap.parse_args()
    t0 = datetime.now()
    print(json.dumps(build(a.data.expanduser(), a.out), indent=1))
    log(f"elapsed {(datetime.now() - t0).total_seconds():.0f} s")
