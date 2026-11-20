"""Detection + relations -> vision contract.

TODO(feat/vision):
- ArUco DICT_4X4_50 -> marker_id -> Element (seed/elements.csv)
- YOLO11s (COCO) + YOLO-World (fixed classes: stage, lectern, projection screen, projector, speaker,
  lighting truss, cable, door, stairs); class-aware NMS 0.5; conf >= 0.35 (COCO) / 0.25 (World)
- RelateAnything (`from relsgg import RelateAnything`; RelateAnything.from_pretrained("maelic/relsgg-vits16plus");
  install with `pip install --no-deps -e RelateAnything` so torch stays cu126) with the 12-phrase vocabulary;
  keep models loaded; fallback: geometric relations
  (on / next to / above from box positions) with source="geometry"
- frame t = seconds from file start; photos: t = null
"""
from tagwerk.pipeline import stub

RELATIONS = ["on", "standing on", "in front of", "behind", "next to", "above", "below",
             "mounted on", "attached to", "holding", "using", "blocking"]
WORLD_CLASSES = ["stage", "lectern", "projection screen", "projector", "speaker",
                 "lighting truss", "cable", "door", "stairs"]


def analyse(capture: dict, derived: dict) -> dict:
    return stub("vision", capture["capture_id"])
