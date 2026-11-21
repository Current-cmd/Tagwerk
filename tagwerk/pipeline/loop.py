"""Progress loop: element state machines (only go up), voice-confirmed changes, activity roll-up."""

STATES: dict[str, list[tuple[str, int]]] = {
    "seat_row": [("removed", 20), ("substructure", 50), ("installed", 85), ("checked", 100)],
    "wall": [("prepared", 30), ("primed", 60), ("painted", 90), ("done", 100)],
    "stage": [("framed", 35), ("boarded", 70), ("finished", 100)],
    "lighting": [("mounted", 50), ("wired", 80), ("tested", 100)],
    "av": [("mounted", 60), ("connected", 85), ("commissioned", 100)],
    "floor": [("stripped", 25), ("levelled", 50), ("covered", 90), ("done", 100)],
    "default": [("started", 30), ("installed", 70), ("checked", 100)],
}


def weight(element_type: str, state: str) -> int:
    for name, w in STATES.get(element_type, STATES["default"]):
        if name == state:
            return w
    raise KeyError(f"unknown state {state!r} for {element_type!r}")


def apply_work(element: dict, state: str, evidence: str) -> dict:
    """Return {'action': 'confirmed'|'proposed'|'unchanged', 'pct': int}.

    Only voice (or voice+vision) confirms; vision alone proposes. Idempotent: never goes down.
    """
    new = weight(element.get("type", "default"), state)
    current = int(element.get("pct", 0))
    if evidence not in ("voice", "both"):
        return {"action": "proposed", "pct": current, "proposed_pct": new}
    if new <= current:
        return {"action": "unchanged", "pct": current}
    return {"action": "confirmed", "pct": new}
