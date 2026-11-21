"""Weather + candidate list from the project state -> context contract.

Candidates (max 80, so a Claude enum schema stays small): elements in the capture's zone, elements
whose ArUco marker was seen, and elements of activities active on DATA_DATE (planned window or
started and unfinished).
"""
import logging
import time
from datetime import date

import httpx

from tagwerk.config import get_settings

log = logging.getLogger(__name__)
MAX_CANDIDATES = 80
_weather_cache: dict[tuple, tuple[float, dict]] = {}


def weather(lat: float, lon: float) -> dict:
    """Current weather from Open-Meteo, cached 30 min; never raises."""
    key = (round(lat, 2), round(lon, 2))
    hit = _weather_cache.get(key)
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    try:
        r = httpx.get("https://api.open-meteo.com/v1/forecast",
                      params={"latitude": lat, "longitude": lon,
                              "current": "temperature_2m,precipitation,wind_speed_10m"}, timeout=3)
        r.raise_for_status()
        cur = r.json()["current"]
        w = {"tempC": cur.get("temperature_2m"), "precipMm": cur.get("precipitation"),
             "windKmh": cur.get("wind_speed_10m"), "source": "open-meteo"}
    except Exception as exc:  # noqa: BLE001 - weather is decoration, never block a capture
        log.warning("weather unavailable: %s", exc)
        w = {"tempC": None, "precipMm": None, "windKmh": None, "source": "unavailable"}
    _weather_cache[key] = (time.time(), w)
    return w


def build_context(capture: dict, vision: dict, project=None) -> dict:
    s = get_settings()
    gps = capture.get("gps") or {}
    lat = (project.meta.get("lat") if project is not None and get_settings().project not in ("", "hoersaal")
           else None) or s.site_lat
    lon = (project.meta.get("lon") if project is not None and get_settings().project not in ("", "hoersaal")
           else None) or s.site_lon
    w = weather(gps.get("lat", lat), gps.get("lon", lon))
    if project is None:
        from tagwerk.pipeline import stub

        ctx = stub("context", capture["capture_id"])
        ctx["zone_id"], ctx["weather"] = capture["zone_id"], w
        return ctx

    from tagwerk.state import today as data_today

    today = data_today()
    markers = project.marker_map()
    seen = [markers[o["marker_id"]] for f in vision.get("frames", []) for o in f["objects"]
            if o.get("marker_id") in markers]
    active = [a for a in project.activities.values()
              if (a["planned_start"] <= today <= a["planned_finish"])
              or (0 < project.activity_pct(a["id"]) < 100)]
    ordered: list[str] = []
    for eid in seen + [e for e, el in project.elements.items() if el["zone"] == capture["zone_id"]]:
        if eid not in ordered:
            ordered.append(eid)
    for a in active:
        for eid in project.elements_of(a["id"]):
            if eid not in ordered:
                ordered.append(eid)
    for eid in project.elements:  # fill up so speech about other zones still matches
        if eid not in ordered:
            ordered.append(eid)
    ordered = ordered[:MAX_CANDIDATES]
    return {
        "capture_id": capture["capture_id"],
        "zone_id": capture["zone_id"],
        "weather": w,
        "candidates": {
            "elements": [{"id": e, "name_de": project.elements[e]["name_de"],
                          "name_en": project.elements[e]["name_en"], "aliases": project.elements[e]["aliases"]}
                         for e in ordered],
            "activities": [{"id": a["id"], "name": a["name"]} for a in project.activities.values()],
        },
    }
