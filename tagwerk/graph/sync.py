"""Projects the Python project state into the graph (Neo4j or memory). Every write is an idempotent MERGE."""
from tagwerk.project import Project, states_for


def sync_seed(store, p: Project) -> None:
    store.merge_node("Project", "P-HS", {"name": "Hörsaal Sanierung", "client": "TUM (fictitious renovation)"})
    store.merge_node("Site", "S-1", {"name": "Hörsaal", "lat": 48.137, "lon": 11.575})
    store.merge_node("Building", "B-1", {"name": "Hörsaalgebäude"})
    store.merge_node("Storey", "ST-0", {"name": "EG", "elevation": 0.0})
    store.merge_edge("P-HS", "HAS_SITE", "S-1")
    store.merge_edge("S-1", "HAS_BUILDING", "B-1")
    store.merge_edge("B-1", "HAS_STOREY", "ST-0")
    for z in p.zones.values():
        store.merge_node("Zone", z["id"], {"name": z["name_de"], "name_en": z["name_en"], "kind": z["kind"]})
        store.merge_edge("ST-0", "HAS_SPACE", z["id"])
    for t in p.trades.values():
        store.merge_node("Trade", t["id"], {"name": t["name"], "rate_eur_h": t["rate_eur_h"]})
    for code, w in p.wbs.items():
        store.merge_node("WBS", f"WBS-{code}", {"code": code, "name": w["name"]})
        if "." in code:
            store.merge_edge(f"WBS-{code}", "IN_WBS", f"WBS-{code.rsplit('.', 1)[0]}")
    for e in p.elements.values():
        store.merge_node("Element", e["id"], element_props(e))
        store.merge_edge(e["zone"], "CONTAINS_ELEMENT", e["id"])
        if e["marker_id"] is not None:
            mid = f"M-{e['marker_id']}"
            store.merge_node("Marker", mid, {"dictionary": "DICT_4X4_50", "code": e["marker_id"]})
            store.merge_edge(mid, "TAGS", e["id"])
    for b in p.boq.values():
        store.merge_node("BoQPosition", b["oz"], {**b, "name": f"{b['oz']} {b['short_text']}"})
    for a in p.activities.values():
        store.merge_node("Activity", a["id"], activity_props(p, a["id"]))
        store.merge_edge(a["id"], "IN_WBS", f"WBS-{a['wbs']}")
        for pred in a["predecessors"]:
            store.merge_edge(pred, "PRECEDES", a["id"], {"type": "FS", "lag_d": 0})
    for lk in p.links:
        store.merge_edge(lk["oz"], "SCHEDULED_AS", lk["activity_id"], {"share": 1.0})
        if lk["element_id"]:
            store.merge_edge(lk["oz"], "QUANTIFIES", lk["element_id"], {"share": lk["share"]})
            store.merge_edge(lk["activity_id"], "BUILDS", lk["element_id"])
    actors = [("ACT-SM", "Site manager", "SiteManager"), ("ACT-BL", "Bauleiter", "Bauleiter")]
    for aid, name, role in actors:
        store.merge_node("Actor", aid, {"name": name, "role": role})
    for a in p.activities:
        store.merge_edge("ACT-SM", "RESPONSIBLE_FOR", a)


def element_props(e: dict) -> dict:
    return {"name_de": e["name_de"], "name_en": e["name_en"], "type": e["type"], "ifc_class": e["ifc_class"],
            "global_id": e["global_id"], "din276": e["din276"], "qty": e["qty"], "unit": e["unit"],
            "pct": e["pct"], "state": e["state"] or "", "aliases": e["aliases"], "zone": e["zone"],
            "states": [s for s, _ in states_for(e["type"])]}


def activity_props(p: Project, aid: str) -> dict:
    a = p.activities[aid]
    return {"name": a["name"], "p6_object_id": aid, "wbs": a["wbs"], "planned_start": a["planned_start"].isoformat(),
            "planned_finish": a["planned_finish"].isoformat(), "pct": p.activity_pct(aid),
            "trade": p.trades[a["trade_id"]]["name"]}


def sync_capture(store, p: Project, capture_id: str, vision: dict | None = None) -> None:
    c = p.captures[capture_id]
    store.merge_node("Capture", capture_id, {"zone_id": c["zone_id"], "ts": c["ts"], "date": c["date"],
                                             "name": f"Capture {c['ts'][5:16].replace('T', ' ')}"})
    store.merge_edge("ACT-SM", "CAPTURED", capture_id)
    store.merge_edge(capture_id, "IN_ZONE", c["zone_id"])
    if c.get("note"):
        nid = f"{capture_id}:note"
        store.merge_node("Note", nid, {"text": c["note"], "lang": c.get("lang", "de")})
        store.merge_edge(capture_id, "HAS_NOTE", nid)
    if c.get("weather"):
        wid = f"{capture_id}:weather"
        store.merge_node("WeatherReading", wid, c["weather"])
        store.merge_edge(capture_id, "UNDER", wid)
    for ch in c["changes"]:
        eid = ch["element_id"]
        if ch["action"] in ("confirmed", "unchanged"):
            store.merge_edge(capture_id, "CONFIRMED", eid,
                             {"toState": ch["state"], "fromPct": ch.get("from_pct", 0), "quote": ch["quote"]})
        elif ch["action"] == "proposed":
            pid = f"{capture_id}:proposal:{eid}"
            store.merge_node("Proposal", pid, {"state": ch["state"], "conf": 0.5, "name": f"{eid}? {ch['state']}"})
            store.merge_edge(capture_id, "PROPOSES", pid)
            store.merge_edge(pid, "FOR", eid)
        store.merge_node("Element", eid, {"pct": p.elements[eid]["pct"], "state": p.elements[eid]["state"] or ""})
    for e in p.events:
        if e["capture_id"] == capture_id:
            store.merge_node("Event", e["id"], {k: v for k, v in e.items() if v is not None and k != "id"})
            store.merge_edge(capture_id, "RAISED", e["id"])
            if e.get("activity_id"):
                store.merge_edge(e["id"], "AFFECTS", e["activity_id"])
    for aid in {a for ch in c["changes"] for a in p.activities_of(ch["element_id"])}:
        store.merge_node("Activity", aid, {"pct": p.activity_pct(aid)})
    if vision:
        for frame in vision.get("frames", []):
            for o in frame["objects"]:
                oid = f"{capture_id}:{o['obj_id']}"
                store.merge_node("Observation", oid, {"label": o["label"], "conf": o["conf"], "bbox": o["bbox"],
                                                      "frame_t": frame["t"] if frame["t"] is not None else -1})
                store.merge_edge(capture_id, "DETECTED", oid)
                if o.get("marker_id") is not None:
                    eid = p.marker_map().get(o["marker_id"])
                    if eid:
                        store.merge_edge(oid, "LIKELY_IS", eid, {"conf": 1.0})
            for t in frame["triplets"]:
                store.merge_edge(f"{capture_id}:{t['s']}", "REL", f"{capture_id}:{t['o']}",
                                 {"predicate": t["rel"], "score": t["score"]})
