""".ics for Outlook (UTC, stable UIDs), Primavera P6 XML (baseline/progress) and GAEB DA XML X83/X84."""
from datetime import UTC, datetime, timedelta


def _ics_time(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def captures_to_ics(captures: list[dict], host: str = "tagwerk", daily_reports: list[str] | None = None) -> str:
    """captures: [{capture_id, ts_server (ISO), zone_id, summary, description}] -> iCalendar text.
    daily_reports: ISO dates; each becomes an all-day event with UID report-<date>@host."""
    now = _ics_time(datetime.now(UTC))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Tagwerk//Site log//EN", "CALSCALE:GREGORIAN"]
    for c in captures:
        start = datetime.fromisoformat(c["ts_server"].replace("Z", "+00:00"))
        lines += [
            "BEGIN:VEVENT",
            f"UID:capture-{c['capture_id']}@{host}",
            f"DTSTAMP:{now}",
            f"DTSTART:{_ics_time(start)}",
            f"DTEND:{_ics_time(start + timedelta(minutes=15))}",
            f"SUMMARY:{_esc(c.get('summary') or 'Site capture ' + c['zone_id'])}",
            f"DESCRIPTION:{_esc(c.get('description', ''))}",
            f"LOCATION:{_esc(c['zone_id'])}",
            "END:VEVENT",
        ]
    for d in daily_reports or []:
        day = d.replace("-", "")
        nxt = (datetime.fromisoformat(d) + timedelta(days=1)).strftime("%Y%m%d")
        lines += ["BEGIN:VEVENT", f"UID:report-{d}@{host}", f"DTSTAMP:{now}", f"DTSTART;VALUE=DATE:{day}",
                  f"DTEND;VALUE=DATE:{nxt}", f"SUMMARY:Tagesbericht {d}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------- Primavera P6 XML

P6_NS = "http://xmlns.oracle.com/Primavera/P6/V8.3/API/BusinessObjects"
UDF_OZ, UDF_ELEMENTS = 9001, 9002


def _p6_date(d) -> str:
    return f"{d.isoformat()}T08:00:00"


def _p6_finish(d) -> str:
    return f"{d.isoformat()}T17:00:00"


def activity_object_id(activity_id: str) -> int:
    digits = "".join(ch for ch in activity_id if ch.isdigit())
    return int(digits) if digits else abs(hash(activity_id)) % 10**6


def p6_xml(project, today=None, progress: bool = True) -> str:
    """P6 XML (APIBusinessObjects): WBS, activities, FS relationships, user-defined fields GAEB_OZ and
    ELEMENT_IDS. With progress=True also PhysicalPercentComplete, Status, ActualStart/FinishDate,
    RemainingDuration and the project DataDate (from `today`). ObjectIds are stable, so the file
    re-imports onto the same activities. Field names follow P6 8.x; check against a real export."""
    from xml.etree.ElementTree import Element, SubElement, indent, tostring

    from tagwerk.project import HOURS_PER_DAY, workdays

    fc = project.forecast(today) if (progress and today) else {}
    root = Element("APIBusinessObjects", xmlns=P6_NS)
    for oid, title in ((UDF_OZ, "GAEB_OZ"), (UDF_ELEMENTS, "ELEMENT_IDS")):
        u = SubElement(root, "UDFType")
        for k, v in (("ObjectId", oid), ("Title", title), ("SubjectArea", "Activity"), ("DataType", "Text")):
            SubElement(u, k).text = str(v)
    proj = SubElement(root, "Project")
    start = min(a["planned_start"] for a in project.activities.values())
    finish = max(a["planned_finish"] for a in project.activities.values())
    for k, v in (("ObjectId", 1), ("Id", project.meta.get("id", "P-1")), ("Name", project.meta.get("name", "Tagwerk")),
                 ("PlannedStartDate", _p6_date(start)), ("ScheduledFinishDate", _p6_finish(finish)),
                 ("DataDate", _p6_date(today) if (progress and today) else _p6_date(start)),
                 ("Status", "Active")):
        SubElement(proj, k).text = str(v)
    wbs_ids = {code: 100 + i for i, code in enumerate(sorted(project.wbs))}
    for code in sorted(project.wbs):
        w = SubElement(proj, "WBS")
        parent = code.rsplit(".", 1)[0] if "." in code else None
        for k, v in (("ObjectId", wbs_ids[code]), ("ProjectObjectId", 1),
                     ("ParentObjectId", wbs_ids[parent] if parent else ""), ("Code", code.split(".")[-1]),
                     ("Name", project.wbs[code]["name"])):
            SubElement(w, k).text = str(v)
    for aid in sorted(project.activities):
        a = project.activities[aid]
        days = len(workdays(a["planned_start"], a["planned_finish"])) or 1
        act = SubElement(proj, "Activity")
        fields = [("ObjectId", activity_object_id(aid)), ("Id", aid), ("Name", a["name"]),
                  ("ProjectObjectId", 1), ("WBSObjectId", wbs_ids[a["wbs"]]), ("Type", "Task Dependent"),
                  ("PercentCompleteType", "Physical"), ("PlannedDuration", days * HOURS_PER_DAY),
                  ("PlannedStartDate", _p6_date(a["planned_start"])),
                  ("PlannedFinishDate", _p6_finish(a["planned_finish"]))]
        if progress and today:
            r = fc[aid]
            pct = r["pct"]
            status = "Completed" if pct >= 100 else "In Progress" if pct > 0 else "Not Started"
            remaining = 0 if pct >= 100 else len(workdays(today, r["forecast_finish"])) * HOURS_PER_DAY
            fields += [("PhysicalPercentComplete", f"{pct:.1f}"), ("Status", status),
                       ("RemainingDuration", remaining)]
            if a["actual_start"] and pct > 0:
                fields.append(("ActualStartDate", f"{a['actual_start']}T08:00:00"))
            if pct >= 100:
                fields.append(("ActualFinishDate", _p6_finish(r["forecast_finish"])))
            else:
                fields.append(("RemainingEarlyFinishDate", _p6_finish(r["forecast_finish"])))
        else:
            fields += [("PhysicalPercentComplete", "0"), ("Status", "Not Started"),
                       ("RemainingDuration", days * HOURS_PER_DAY)]
        for k, v in fields:
            SubElement(act, k).text = str(v)
        ozs = sorted({lk["oz"] for lk in project.links if lk["activity_id"] == aid})
        for type_id, value in ((UDF_OZ, ";".join(ozs)), (UDF_ELEMENTS, ";".join(project.elements_of(aid)))):
            u = SubElement(act, "UDF")
            SubElement(u, "TypeObjectId").text = str(type_id)
            SubElement(u, "TextValue").text = value
    rel_id = 5000
    for aid in sorted(project.activities):
        for pred in project.activities[aid]["predecessors"]:
            rel_id += 1
            r = SubElement(proj, "Relationship")
            rel_type = "Start to Start" if pred in project.activities[aid].get("start_to_start", []) else "Finish to Start"
            for k, v in (("ObjectId", rel_id), ("PredecessorActivityObjectId", activity_object_id(pred)),
                         ("SuccessorActivityObjectId", activity_object_id(aid)), ("Type", rel_type),
                         ("Lag", 0)):
                SubElement(r, k).text = str(v)
    indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode") + "\n"


# ---------------------------------------------------------------- GAEB DA XML

def gaeb_xml(project, phase: int = 83) -> str:
    """GAEB DA XML 3.3 bill of quantities: X83 (tender, no prices) or X84 (priced bid).
    Lots are top-level categories (01 Ausbau, 02 TGA, 03 AV), then a second category level and items."""
    from xml.etree.ElementTree import Element, SubElement, indent, tostring

    root = Element("GAEB", xmlns=f"http://www.gaeb.de/GAEB_DA_XML/DA{phase}/3.3")
    info = SubElement(root, "GAEBInfo")
    SubElement(info, "Version").text = "3.3"
    SubElement(info, "ProgSystem").text = "Tagwerk"
    award = SubElement(root, "Award")
    SubElement(award, "DP").text = str(phase)
    boq = SubElement(award, "BoQ")
    binfo = SubElement(boq, "BoQInfo")
    SubElement(binfo, "Name").text = project.meta.get("name", "Tagwerk")
    bkdn = SubElement(binfo, "BoQBkdn")
    for typ, length in (("BoQLevel", 2), ("BoQLevel", 2), ("Item", 4)):
        lvl = SubElement(bkdn, "BoQBkdn")
        SubElement(lvl, "Type").text = typ
        SubElement(lvl, "Length").text = str(length)
    body = SubElement(boq, "BoQBody")
    tree: dict[str, dict[str, list]] = {}
    lots = {lot: f"{i:02d}" for i, lot in enumerate(dict.fromkeys(b["lot"] for b in project.boq.values()), 1)}
    for n, (oz, b) in enumerate(sorted(project.boq.items()), 1):
        parts = oz.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):  # OZ like 01.02.0030
            l1, l2, item = parts
        else:  # foreign numbering (e.g. SP.ST00020): lot -> one group -> running item numbers
            l1, l2, item = lots[b["lot"]], "01", f"{n:04d}"
        tree.setdefault(l1, {}).setdefault(l2, []).append((item, b))
    total = 0.0
    for l1, sub in tree.items():
        c1 = SubElement(body, "BoQCtgy", RNoPart=l1)
        lot = next(iter(sub.values()))[0][1]["lot"]
        SubElement(SubElement(c1, "LblTx"), "p").text = lot
        b1 = SubElement(c1, "BoQBody")
        for l2, items in sub.items():
            c2 = SubElement(b1, "BoQCtgy", RNoPart=l2)
            SubElement(SubElement(c2, "LblTx"), "p").text = items[0][1]["short_text"].split(" ")[0]
            il = SubElement(SubElement(c2, "BoQBody"), "Itemlist")
            for item, b in items:
                it = SubElement(il, "Item", RNoPart=item)
                SubElement(it, "Qty").text = f"{b['qty']:.3f}"
                SubElement(it, "QU").text = b["unit"]
                if phase == 84:
                    line = b["qty"] * b["unit_price"]
                    total += line
                    SubElement(it, "UP").text = f"{b['unit_price']:.2f}"
                    SubElement(it, "IT").text = f"{line:.2f}"
                desc = SubElement(SubElement(it, "Description"), "CompleteText")
                ot = SubElement(SubElement(SubElement(desc, "OutlineText"), "OutlTxt"), "TextOutlTxt")
                SubElement(ot, "span").text = b["short_text"]
                SubElement(SubElement(desc, "DetailTxt"), "Text").text = f"DIN 276: {b['din276']}"
    if phase == 84:
        SubElement(binfo, "Totals").text = f"{total:.2f}"
    indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode") + "\n"
