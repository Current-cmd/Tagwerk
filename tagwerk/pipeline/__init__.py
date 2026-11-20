"""Pipeline stages. Each stage returns data matching its contract in contracts/.

Until a stage is implemented it returns its fixture (with the right capture_id), so the
whole chain runs end to end from day one. Replace stubs one module at a time.
"""
import copy

from tagwerk.contracts import fixture


def stub(name: str, capture_id: str) -> dict:
    data = copy.deepcopy(fixture(name))
    data["capture_id"] = capture_id
    return data
