"""Tagesbericht / Bautagebuch (docs/UI-V2-CONTRACT.md): the day snapshot of tagwerk.v2 reshaped into the report, plus
the print-ready German A4 page. Everything the page says comes from the day's recordings, scans and forecast."""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

from tagwerk import v2
from tagwerk.config import get_settings
from tagwerk.state import get_project

STATE_DE = v2.STATE_DE


def load_scan(cid: str) -> dict | None:
    """cache/<cid>/sfm.json or None."""
    try:
        return json.loads((Path(get_settings().cache_dir) / cid / "sfm.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def has_3d(cid: str) -> bool:
    return (Path(get_settings().cache_dir) / cid / "sfm.json").is_file()


def _inventory(recordings: list[dict], scans: dict[str, dict]) -> list[dict]:
    rows: dict[str, dict] = {}
    for rec in recordings:
        scan = scans.get(rec["capture_id"])
        for o in (scan or {}).get("objects", []):
            r = rows.setdefault(o["name_de"], {"name_de": o["name_de"], "count": 0, "relations": [],
                                               "thumb": o.get("thumb"), "capture_id": rec["capture_id"]})
            r["count"] += 1
            for rel in o.get("relations", [])[:3]:
                text = f"{rel['rel_de']} {rel['target_name']}"
                if text not in r["relations"] and len(r["relations"]) < 4:
                    r["relations"].append(text)
    return sorted(rows.values(), key=lambda r: (-r["count"], r["name_de"]))


def assemble(d: dict, meta: dict, scans: dict[str, dict]) -> dict:
    """Report from a v2 day snapshot `d`, the project meta and {capture_id: sfm.json} (pure, unit tested)."""
    recs = sorted(d["recordings"], key=lambda r: r["time"])
    work, present, absent = [], {}, {}
    for r in recs:
        for c in r["changes"]:
            if c["action"] == "confirmed":
                work.append({"activity_id": c["activity_id"], "activity_name": c["activity_name"],
                             "element_name": c["element_name"], "state_de": STATE_DE.get(c["state"], c["state"]),
                             "quote": c["quote"], "capture_id": r["capture_id"]})
        for lp in r["labour"]:
            present[lp["trade"]] = max(present.get(lp["trade"], 0), lp["count"])
        for a in r["absences"]:
            cur = absent.get(a["trade"])
            if cur is None or a["count"] > cur["count"]:
                absent[a["trade"]] = {"trade": a["trade"], "count": a["count"], "reason": a.get("reason")}
    iso = d["date"]
    events = [{"type": e["type"], "text": e["text"], "severity": e["severity"]} for e in d["events"] if e["date"] == iso]
    seen = {(e["type"], e["text"]) for e in events}
    for r in recs:
        for e in r["events"]:
            if (e["type"], e["text"]) not in seen:
                seen.add((e["type"], e["text"]))
                events.append({"type": e["type"], "text": e["text"], "severity": e["severity"]})
    return {
        "date": iso,
        "project": {"name": meta.get("name"), "site": meta.get("site"), "client": meta.get("client")},
        "weather": d.get("weather"),
        "recordings": [{"capture_id": r["capture_id"], "time": r["time"], "zone_name": r["zone_name"], "kind": r["kind"],
                        "has_3d": bool(r.get("has_3d"))} for r in recs],
        "work_done": work,
        "workforce": {"present": [{"trade": t, "count": n} for t, n in present.items()], "absent": list(absent.values())},
        "inventory": _inventory(recs, scans),
        "events": events,
        "photos": [u for r in recs for u in r["photos"]],
        "delays": [{"activity_id": a["id"], "activity_name": a["name"], "delay_d": a["delay_d"], "cause": a["cause"]}
                   for a in d["activities"] if a["delay_d"] > 0],
        "lookahead": [{"date": x["date"], "activities": [a["name"] for a in x["activities"]]} for x in d["lookahead"]],
    }


def report(day: date) -> dict:
    d = v2.day(day)
    scans = {r["capture_id"]: s for r in d["recordings"] if (s := load_scan(r["capture_id"]))}
    return assemble(d, get_project().meta, scans)


# ---------------------------------------------------------------- print page

CSS = """
@page { size: A4; margin: 14mm 13mm; }
* { box-sizing: border-box; }
body { font: 10.5pt/1.35 "Helvetica Neue", Arial, sans-serif; color: #111; margin: 0; }
.page { max-width: 184mm; margin: 0 auto; padding: 8mm 0; }
h1 { font-size: 17pt; margin: 0 0 2mm; }
h2 { font-size: 11.5pt; margin: 5mm 0 1.5mm; border-bottom: 1px solid #444; padding-bottom: 0.6mm; }
.head { display: flex; justify-content: space-between; gap: 8mm; border-bottom: 2px solid #111; padding-bottom: 3mm; }
.head div small { display: block; color: #555; font-size: 8.5pt; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; }
td, th { border: 1px solid #bbb; padding: 1mm 1.8mm; text-align: left; vertical-align: top; }
th { background: #eee; } .muted { color: #666; } .sev-high { color: #b00020; font-weight: 600; }
.photos { display: flex; flex-wrap: wrap; gap: 2mm; } .photos img { height: 30mm; border: 1px solid #bbb; }
.sign { margin-top: 14mm; display: flex; gap: 12mm; }
.sign div { flex: 1; border-top: 1px solid #111; padding-top: 1mm; font-size: 9pt; color: #444; }
.noprint { background: #f3f3f3; padding: 3mm 5mm; font-size: 9.5pt; } @media print { .noprint { display: none; } }
"""


def _e(v) -> str:
    return html.escape("" if v is None else str(v))


def _table(head: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f'<p class="muted">{_e(empty)}</p>'
    return ("<table><tr>" + "".join(f"<th>{_e(h)}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def _de_date(iso: str) -> str:
    y, m, dd = iso.split("-")
    return f"{dd}.{m}.{y}"


def render_html(rep: dict) -> str:
    w, pr, wf = rep.get("weather"), rep["project"], rep["workforce"]
    wtxt = "keine Wetterdaten" if not w else ", ".join(
        x for x in (f"{w['tempC']:.0f} °C".replace(".", ",") if w.get("tempC") is not None else "",
                    f"Niederschlag {w['precipMm']:g} mm".replace(".", ",") if w.get("precipMm") is not None else "",
                    f"Wind {w['windKmh']:.0f} km/h" if w.get("windKmh") is not None else "") if x) or "keine Wetterdaten"
    sections = [
        "<h2>Arbeiten</h2>" + _table(["Vorgang", "Bauteil", "Stand", "Beleg"], [
            [_e(x["activity_name"] or "–"), _e(x["element_name"]), _e(x["state_de"]),
             f'<span class="muted">„{_e(x["quote"])}“</span>']
            for x in rep["work_done"]], "Keine Fortschrittsmeldungen an diesem Tag."),
        "<h2>Personal</h2>" + _table(["Gewerk", "Anwesend", "Abwesend"], _staff_rows(wf), "Keine Angaben zum Personal."),
        "<h2>Inventar aus dem Scan</h2>" + _table(["Objekt", "Anzahl", "Lage zueinander"], [
            [_e(i["name_de"]), str(i["count"]), _e(", ".join(i["relations"]) or "–")] for i in rep["inventory"]],
            "Kein 3D-Scan an diesem Tag."),
        "<h2>Ereignisse und Mängel</h2>" + _table(["Art", "Beschreibung", "Schwere"], [
            [_e(e["type"]), _e(e["text"]), f'<span class="sev-{_e(e["severity"])}">{_e(e["severity"])}</span>']
            for e in rep["events"]], "Keine besonderen Vorkommnisse."),
        "<h2>Verzüge</h2>" + _table(["Vorgang", "Verzug", "Ursache"], [
            [_e(x["activity_name"]), f'{x["delay_d"]} AT', _e(x["cause"] or "–")] for x in rep["delays"]],
            "Kein Verzug gegenüber dem Plan."),
        "<h2>Vorschau: nächste Arbeitstage</h2>" + _table(["Datum", "Geplante Vorgänge"], [
            [_de_date(x["date"]), _e(", ".join(x["activities"]) or "–")] for x in rep["lookahead"]], "Keine Vorschau."),
        "<h2>Aufnahmen</h2>" + _table(["Zeit", "Ort", "Art", "3D"], [
            [_e(r["time"]), _e(r["zone_name"] or "–"), _e(r["kind"]), "ja" if r["has_3d"] else "–"] for r in rep["recordings"]],
            "Keine Aufnahmen."),
    ]
    imgs = "".join(f'<img src="{_e(u)}" alt="Foto">' for u in rep["photos"][:12])
    photos = f'<h2>Fotos</h2><div class="photos">{imgs}</div>' if rep["photos"] else ""
    return (f'<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Bautagebuch {_de_date(rep["date"])}</title>'
            f"<style>{CSS}</style></head><body><div class=\"page\">"
            '<div class="noprint">Zum Speichern als PDF: Drucken (Strg+P) und „Als PDF speichern“ wählen.</div>'
            f'<div class="head"><div><h1>Bautagebuch / Tagesbericht</h1><small>{_e(pr.get("name"))}'
            f'{" · " + _e(pr["site"]) if pr.get("site") else ""}</small>'
            f'{"<small>Auftraggeber: " + _e(pr["client"]) + "</small>" if pr.get("client") else ""}</div>'
            f'<div><b>{_de_date(rep["date"])}</b><small>Wetter: {_e(wtxt)}</small></div></div>'
            + "".join(sections) + photos
            + '<div class="sign"><div>Ort, Datum</div><div>Unterschrift Bauleiter</div></div></div></body></html>')


def _staff_rows(wf: dict) -> list[list[str]]:
    trades = sorted({p["trade"] for p in wf["present"]} | {a["trade"] for a in wf["absent"]})
    pres = {p["trade"]: p["count"] for p in wf["present"]}
    ab = {a["trade"]: a for a in wf["absent"]}
    return [[_e(t), str(pres.get(t, "–")),
             _e(f"{ab[t]['count']}" + (f" ({ab[t]['reason']})" if ab[t].get("reason") else "")) if t in ab else "–"]
            for t in trades]
