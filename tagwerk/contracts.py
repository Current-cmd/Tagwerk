"""Load and enforce the JSON contracts in contracts/."""
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = ROOT / "contracts"
FIXTURES_DIR = ROOT / "fixtures"
NAMES = ("capture", "transcript", "vision", "context", "structured", "graph_event", "dashboard")


class ContractError(ValueError):
    pass


@lru_cache
def schema(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / f"{name}.schema.json").read_text())


def validate(name: str, data: dict) -> dict:
    """Raise ContractError if data does not match contracts/<name>.schema.json; return data."""
    validator = Draft202012Validator(schema(name), format_checker=Draft202012Validator.FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        msg = "; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors[:5])
        raise ContractError(f"{name}: {msg}")
    return data


def fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())
