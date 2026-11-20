"""python scripts/validate_fixtures.py — every fixture must match its contract."""
import sys

from tagwerk.contracts import NAMES, ContractError, fixture, validate

bad = 0
for name in NAMES:
    try:
        validate(name, fixture(name))
        print(f"[ok]   {name}")
    except ContractError as exc:
        bad += 1
        print(f"[FAIL] {exc}")
sys.exit(1 if bad else 0)
