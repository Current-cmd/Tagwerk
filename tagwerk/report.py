"""Tagesbericht / Bautagebuch (docs/UI-V2-CONTRACT.md, "GET /api/v2/report"): the German daily report of day D.

Built on the v2 day snapshot (state as of D, delays with causes, lookahead) plus the cached stage outputs of that day's
recordings (cache/<cid>/sfm.json, vision.json, context.json). No network calls, no cost fields.
"""
from __future__ import annotations

import json
import re
from datetime import date
from html import escape
from pathlib import Path

from tagwerk import v2
from tagwerk.config import get_settings
from tagwerk.pipeline.scan import CATALOG
from tagwerk.project import ABSENCE_WORKDAYS, Project, is_workday, next_workday

# German labels for every element state in tagwerk.pipeline.loop.STATES (Bautagebuch wording)
STATE_DE = {
    "started": "begonnen", "installed": "montiert", "mounted": "montiert", "connected": "angeschlossen",
    "wired": "verkabelt", "tested": "geprüft", "commissioned": "in Betrieb", "checked": "abgenommen",
    "painted": "gestrichen", "primed": "grundiert", "prepared": "vorbereitet", "covered": "verlegt",
    "levelled": "nivelliert", "substructure": "Unterkonstruktion", "framed": "Unterkonstruktion",
    "boarded": "beplankt", "removed": "ausgebaut", "stripped": "entfernt", "done": "fertig", "finished": "fertig",
}
# RelateAnything predicates -> German; unknown predicates stay as they are
PREDICATE_DE = {
    "on": "auf", "under": "unter", "below": "unter", "above": "über", "next to": "neben", "beside": "neben",
    "in front of": "vor", "behind": "hinter", "attached to": "an", "standing on": "steht auf", "holding": "hält",
}
EVENT_TYPES = ("defect", "delay", "safety", "weather", "absence")
NO_INVENTORY = {"people"}  # persons, hard hats, vests: labour, not inventory (nor relation targets)
NO_INVENTORY_NAMES = {name_de for cat, _ifc, name_de, _t in CATALOG.values() if cat in NO_INVENTORY}
MAX_RELATIONS, MAX_PHOTOS = 5, 6
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _cache(cid: str) -> Path:
    return Path(get_settings().cache_dir) / cid


def _sfm(cid: str) -> dict | None:
    return _load(_cache(cid) / "sfm.json")


# ---------- sections ----------

def _weather(snapshot_weather: dict | None, caps: list[dict]) -> dict | None:
    w = snapshot_weather
    if not v2._has_reading(w):  # history captures carry no reading: use a cached context, never the network
        for c in sorted(caps, key=lambda c: c["ts"], reverse=True):
            ctx = _load(_cache(c["capture_id"]) / "context.json") or {}
            if v2._has_reading(ctx.get("weather")):
                w = ctx["weather"]
                break
        else:
            return None
    return {k: w.get(k) for k in ("tempC", "precipMm", "windKmh")}


NUMBERED = re.compile(r"^(?P<base>.*?)\s+\d+(?P<suffix>\s*\(.*\))?$")  # "sporenkap 12 (Derde verdieping)"


def element_label(names: list[str]) -> str:
    """One label for the elements one sentence confirmed: "32× sporenkap (Derde verdieping)", "A, B", "5 Bauteile: …"."""
    names = list(dict.fromkeys(names))
    if len(names) == 1:
        return names[0]
    parts = [NUMBERED.match(n) for n in names]
    if all(parts) and len({(m["base"], m["suffix"]) for m in parts}) == 1:
        return f"{len(names)}× {parts[0]['base']}{parts[0]['suffix'] or ''}"
    if len(names) <= 3:
        return ", ".join(names)
    return f"{len(names)} Bauteile: {', '.join(names[:2])}, …"


def _work_done(p: Project, caps: list[dict]) -> list[dict]:
    """Confirmed changes of the day, one row per capture, activity, state and sentence (not one per element)."""
    rows: dict[tuple, dict] = {}
    for c in caps:
        for ch in c["changes"]:
            if ch["action"] != "confirmed":
                continue
            acts = v2._change_activities(p, ch)
            aid = acts[0] if acts else None
            el = p.elements.get(ch["element_id"]) or {}
            state_de = STATE_DE.get(ch["state"], ch["state"])
            row = rows.setdefault((c["capture_id"], aid, state_de, ch["quote"]), {
                "activity_id": aid, "activity_name": p.activities[aid]["name"] if aid else None, "names": [],
                "state_de": state_de, "quote": ch["quote"], "capture_id": c["capture_id"]})
            row["names"].append(el.get("name_de", ch["element_id"]))
    return [{"activity_id": r["activity_id"], "activity_name": r["activity_name"], "element_name": element_label(r["names"]),
             "state_de": r["state_de"], "quote": r["quote"], "capture_id": r["capture_id"]} for r in rows.values()]


def _covers(reported: str, d: date) -> bool:
    """Same window as Project.absent_on: the report day (next working day on weekends) + following working days."""
    first = date.fromisoformat(reported)
    if not is_workday(first):
        first = next_workday(first)
    last = first
    for _ in range(ABSENCE_WORKDAYS - 1):
        last = next_workday(last)
    return first <= d <= last


def _workforce(p: Project, d: date) -> dict:
    iso = d.isoformat()
    present: dict[str, int] = {}
    for lp in p.labour:
        if lp["date"] == iso:
            present[lp["trade"]] = present.get(lp["trade"], 0) + lp["count"]
    absent: dict[str, dict] = {}  # repeats of one trade keep the highest count, like Project.absent_on
    for e in p.events:
        if e["type"] != "absence" or not _covers(e["date"], d):
            continue
        key = e["trade"].lower()
        reason = e["text"].split(f"{e['trade']} ", 1)[-1].strip() if e.get("text") else None
        if key not in absent or e["count"] > absent[key]["count"]:
            absent[key] = {"trade": e["trade"], "count": e["count"], "reason": reason or None}
    return {"present": [{"trade": t, "count": n} for t, n in sorted(present.items())],
            "absent": sorted(absent.values(), key=lambda x: x["trade"])}


def _name_de(label: str) -> tuple[str, str]:
    cat, _ifc, name_de, _type = CATALOG.get(label, ("other", None, label.capitalize(), ""))
    return name_de, cat


def _frame_url(cid: str, media_path: str | None) -> str | None:
    if not media_path:
        return None
    name = Path(media_path).name
    if (Path(get_settings().data_dir) / "captures" / cid / "derived" / "frames" / name).is_file():
        return f"/media/{cid}/derived/frames/{name}"
    return None


def _inventory_of(cid: str) -> list[dict]:
    """One capture's objects: [{name_de, count, relations, thumb}], from sfm.json, else the vision detections."""
    sfm = _sfm(cid)
    items: dict[str, dict] = {}
    if sfm and sfm.get("objects"):
        for o in sfm["objects"]:
            if CATALOG.get(o.get("label", ""), ("",))[0] in NO_INVENTORY:
                continue
            it = items.setdefault(o["name_de"], {"name_de": o["name_de"], "count": 0, "relations": [], "thumb": None})
            it["count"] += 1
            it["thumb"] = it["thumb"] or o.get("thumb")
            for r in o.get("relations", []):
                if r.get("target_name") in NO_INVENTORY_NAMES:
                    continue
                it["relations"].append(f"{r.get('rel_de') or PREDICATE_DE.get(r['rel'], r['rel'])} {r['target_name']}")
        return list(items.values())
    vis = _load(_cache(cid) / "vision.json") or {}
    per_frame: dict[str, int] = {}
    for f in vis.get("frames", []):
        labels = {o["obj_id"]: o["label"] for o in f["objects"] if o.get("source") != "marker"}
        counts: dict[str, int] = {}
        for label in labels.values():
            name, cat = _name_de(label)
            if cat in NO_INVENTORY:
                continue
            counts[name] = counts.get(name, 0) + 1
            it = items.setdefault(name, {"name_de": name, "count": 0, "relations": [], "thumb": None})
            it["thumb"] = it["thumb"] or _frame_url(cid, f.get("media_path"))
        for name, n in counts.items():
            per_frame[name] = max(per_frame.get(name, 0), n)
        for t in f.get("triplets", []):
            if (t["s"] in labels and t["o"] in labels and _name_de(labels[t["s"]])[0] in items
                    and _name_de(labels[t["o"]])[1] not in NO_INVENTORY):
                rel = PREDICATE_DE.get(t["rel"].lower(), t["rel"])
                items[_name_de(labels[t["s"]])[0]]["relations"].append(f"{rel} {_name_de(labels[t['o']])[0]}")
    for name, it in items.items():
        it["count"] = per_frame.get(name, 0)
    return [it for it in items.values() if it["count"]]


def _inventory(caps: list[dict]) -> list[dict]:
    out: dict[str, dict] = {}
    for c in caps:
        cid = c["capture_id"]
        for it in _inventory_of(cid):
            row = out.setdefault(it["name_de"], {"name_de": it["name_de"], "count": 0, "relations": [], "thumb": None,
                                                 "capture_id": cid})
            row["count"] += it["count"]
            row["thumb"] = row["thumb"] or it["thumb"]
            row["relations"] += it["relations"]
    for row in out.values():
        row["relations"] = list(dict.fromkeys(row["relations"]))[:MAX_RELATIONS]
    return sorted(out.values(), key=lambda r: (-r["count"], r["name_de"]))


def _photos(caps: list[dict], recordings: list[dict]) -> list[str]:
    """Kept photos first, then video keyframes (cache/<cid>/media/**, data/captures/<cid>/derived/frames)."""
    s = get_settings()
    photos = [u for r in recordings for u in r["photos"]]
    for c in caps:
        cid = c["capture_id"]
        frames: list[str] = []
        media = Path(s.cache_dir) / cid / "media"
        if media.is_dir():
            frames += [f"/media/{cid}/{f.relative_to(media).as_posix()}" for f in sorted(media.rglob("*"))
                       if f.is_file() and f.parent != media and f.suffix.lower() in IMAGE_EXT]
        derived = Path(s.data_dir) / "captures" / cid / "derived" / "frames"
        if derived.is_dir():
            frames += [f"/media/{cid}/derived/frames/{f.name}" for f in sorted(derived.iterdir())
                       if f.suffix.lower() in IMAGE_EXT]
        if frames:  # a few frames spread over the video
            step = max(1, len(frames) // 3)
            photos += frames[::step][:3]
    return list(dict.fromkeys(photos))[:MAX_PHOTOS]


def report(d: date) -> dict:
    snap = v2.day(d)
    p = v2.project_as_of(min(d, v2.today()))
    iso = d.isoformat()
    caps = sorted((c for c in p.captures.values() if c["date"] == iso), key=lambda c: c["ts"])
    recs = sorted(snap["recordings"], key=lambda r: (r["time"], r["capture_id"]))
    recordings = [{"capture_id": r["capture_id"], "time": r["time"], "zone_name": r["zone_name"], "kind": r["kind"],
                   "has_3d": bool((_sfm(r["capture_id"]) or {}).get("ok"))} for r in recs]
    events = [{"type": e["type"], "text": e["text"], "severity": e["severity"]}
              for e in sorted(snap["events"], key=lambda e: e["id"]) if e["date"] == iso and e["type"] in EVENT_TYPES]
    delays = sorted(({"activity_id": a["id"], "activity_name": a["name"], "delay_d": a["delay_d"], "cause": a["cause"]}
                     for a in snap["activities"] if a["delay_d"] > 0), key=lambda x: (-x["delay_d"], x["activity_id"]))
    meta = p.meta
    return {"date": iso, "project": {k: meta.get(k) for k in ("name", "site", "client")},
            "weather": None if snap["is_future"] else _weather(snap["weather"], caps), "recordings": recordings,
            "work_done": _work_done(p, caps), "workforce": _workforce(p, d), "inventory": _inventory(caps),
            "events": events, "photos": _photos(caps, recs), "delays": delays,
            "lookahead": [{"date": x["date"], "activities": list(dict.fromkeys(a["name"] for a in x["activities"]))}
                          for x in snap["lookahead"]]}


# ---------- print page ----------

def report_number(d: date) -> int:
    """Bericht-Nr.: working day number since the project start (first planned start, or the first recorded day)."""
    p = v2.project_as_of(min(d, v2.today()))
    starts = [a["planned_start"] for a in p.activities.values()]
    starts += [date.fromisoformat(c["date"]) for c in p.captures.values()]
    start = min(starts, default=d)
    n, x = 0, start
    while x <= d:
        n += is_workday(x)
        x = date.fromordinal(x.toordinal() + 1)
    return max(n, 1)


def _de_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d.%m.%Y")


WEEKDAY_DE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
EVENT_DE = {"defect": "Mangel", "delay": "Verzug", "safety": "Sicherheit", "weather": "Wetter", "absence": "Abwesenheit"}
SEVERITY_DE = {"low": "gering", "medium": "mittel", "high": "hoch"}
KIND_DE = v2.KIND_DE

CSS = """
@page { size: A4; margin: 14mm 12mm; }
* { box-sizing: border-box; }
body { font: 10pt/1.35 -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #111;
       background: #fff; margin: 0 auto; max-width: 210mm; padding: 10mm; }
h1 { font-size: 16pt; margin: 0; letter-spacing: .02em; }
h2 { font-size: 11pt; margin: 14px 0 4px; padding: 3px 6px; background: #eceff1; border-left: 4px solid #37474f; }
header { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #111;
         padding-bottom: 6px; margin-bottom: 6px; }
.nr { text-align: right; font-size: 9pt; }
table { width: 100%; border-collapse: collapse; page-break-inside: avoid; break-inside: avoid; }
th, td { border: 1px solid #b0bec5; padding: 3px 5px; vertical-align: top; text-align: left; }
th { background: #f5f7f8; font-weight: 600; width: auto; }
table.kopf th { width: 18%; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.none { color: #666; font-style: italic; }
.chip { display: inline-block; border: 1px solid #b0bec5; border-radius: 8px; padding: 0 5px; margin: 1px 2px 1px 0;
        font-size: 8.5pt; }
.sev-high { color: #b71c1c; font-weight: 600; } .sev-medium { color: #e65100; } .sev-low { color: #555; }
.thumb { width: 42px; height: 32px; object-fit: cover; border: 1px solid #ccc; }
.photos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; page-break-inside: avoid; }
.photos img { width: 100%; height: 48mm; object-fit: cover; border: 1px solid #b0bec5; }
.sign { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 28px; page-break-inside: avoid; }
.sign div { border-top: 1px solid #111; padding-top: 3px; font-size: 9pt; }
q { font-style: italic; color: #333; }
@media print {
  body { padding: 0; max-width: none; }
  h2 { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  section, table, tr, .photos, .sign { page-break-inside: avoid; break-inside: avoid; }
  h2 { page-break-after: avoid; break-after: avoid; }
}
"""


def _table(head: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return '<p class="none">keine</p>'
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def _weather_text(w: dict | None) -> str:
    if not w:
        return "keine Angabe"
    parts = []
    if w.get("tempC") is not None:
        parts.append(f"{w['tempC']:.1f} °C".replace(".", ","))
    if w.get("precipMm") is not None:
        parts.append(f"Niederschlag {w['precipMm']:.1f} mm".replace(".", ","))
    if w.get("windKmh") is not None:
        parts.append(f"Wind {w['windKmh']:.0f} km/h")
    return ", ".join(parts) or "keine Angabe"


def render_html(rep: dict, number: int) -> str:
    e = escape
    d = date.fromisoformat(rep["date"])
    pr = rep["project"]

    def val(x) -> str:
        return e(str(x)) if x not in (None, "") else '<span class="none">–</span>'

    kopf = (f'<table class="kopf"><tr><th>Projekt</th><td>{val(pr["name"])}</td><th>Datum</th>'
            f'<td>{WEEKDAY_DE[d.weekday()]}, {_de_date(rep["date"])}</td></tr>'
            f'<tr><th>Bauherr</th><td>{val(pr["client"])}</td><th>Wetter</th><td>{e(_weather_text(rep["weather"]))}</td></tr>'
            f'<tr><th>Ort</th><td>{val(pr["site"])}</td><th>Aufnahmen</th><td>'
            + (", ".join(f'{e(r["time"])} {e(KIND_DE.get(r["kind"], r["kind"]))}'
                         f'{" (" + e(r["zone_name"]) + ")" if r["zone_name"] else ""}{" · 3D" if r["has_3d"] else ""}'
                         for r in rep["recordings"]) or '<span class="none">keine</span>')
            + "</td></tr></table>")
    work = _table(["Vorgang", "Bauteil", "Stand", "Aussage"],
                  [[val(w["activity_name"]), e(w["element_name"]), f'<b>{e(w["state_de"])}</b>',
                    f'<q>{e(w["quote"])}</q>' if w["quote"] else ""] for w in rep["work_done"]])
    wf = rep["workforce"]
    present = _table(["Gewerk", "Anzahl"], [[e(x["trade"]), str(x["count"])] for x in wf["present"]])
    absent = _table(["Gewerk", "Anzahl", "Grund"],
                    [[e(x["trade"]), str(x["count"]), val(x.get("reason"))] for x in wf["absent"]])
    thumbs = any(x["thumb"] for x in rep["inventory"])  # no empty picture column
    inv = _table(([""] if thumbs else []) + ["Objekt", "Anzahl", "Relationen"],
                 [([f'<img class="thumb" src="{e(x["thumb"])}" alt="">' if x["thumb"] else ""] if thumbs else [])
                  + [e(x["name_de"]), str(x["count"]), "".join(f'<span class="chip">{e(r)}</span>' for r in x["relations"])]
                  for x in rep["inventory"]])
    events = _table(["Art", "Beschreibung", "Schwere"],
                    [[e(EVENT_DE.get(x["type"], x["type"])), e(x["text"]),
                      f'<span class="sev-{e(x["severity"])}">{e(SEVERITY_DE.get(x["severity"], x["severity"]))}</span>']
                     for x in rep["events"]])
    delays = _table(["Vorgang", "Verzug", "Ursache"],
                    [[e(x["activity_name"]), f'{x["delay_d"]} AT', val(x["cause"])] for x in rep["delays"]])
    look = _table(["Datum", "Geplante Vorgänge"],
                  [[f'{WEEKDAY_DE[date.fromisoformat(x["date"]).weekday()][:2]}, {_de_date(x["date"])}',
                    e(", ".join(x["activities"])) if x["activities"] else '<span class="none">keine</span>']
                   for x in rep["lookahead"]])
    photos = ('<div class="photos">' + "".join(f'<img src="{e(u)}" alt="Foto">' for u in rep["photos"]) + "</div>"
              if rep["photos"] else '<p class="none">keine</p>')
    title = f"Tagesbericht {_de_date(rep['date'])}"
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · {e(pr["name"] or "Tagwerk")}</title><style>{CSS}</style></head>
<body>
<header><div><h1>Tagesbericht / Bautagebuch</h1><div>{val(pr["name"])}</div></div>
<div class="nr">Bericht-Nr. <b>{number}</b><br>{_de_date(rep["date"])}</div></header>
{kopf}
<section><h2>Ausgeführte Arbeiten</h2>{work}</section>
<section><h2>Personal</h2><div class="cols"><div><b>anwesend</b>{present}</div><div><b>abwesend</b>{absent}</div></div></section>
<section><h2>Inventar aus Scan (mit Relationen)</h2>{inv}</section>
<section><h2>Ereignisse &amp; Mängel</h2>{events}</section>
<section><h2>Verzüge</h2>{delays}</section>
<section><h2>Vorschau (nächste 3 Arbeitstage)</h2>{look}</section>
<section><h2>Fotos</h2>{photos}</section>
<div class="sign"><div>Unterschrift Bauleiter</div><div>Datum</div></div>
</body></html>
"""


def report_html(d: date) -> str:
    return render_html(report(d), report_number(d))
