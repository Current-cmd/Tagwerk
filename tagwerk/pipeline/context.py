"""Weather + candidate list from the graph -> context contract.

TODO(feat/context):
- Open-Meteo for (gps or SITE_LAT/SITE_LON) at ts_device; source="open-meteo"
- candidates: elements in capture zone + elements whose marker was seen + activities active on DATA_DATE
  (cap at 80; fixed during the demo so Claude's schema compiles once)
"""
from tagwerk.pipeline import stub


def build_context(capture: dict, vision: dict) -> dict:
    ctx = stub("context", capture["capture_id"])
    ctx["zone_id"] = capture["zone_id"]
    return ctx
