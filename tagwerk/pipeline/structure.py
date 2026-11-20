"""Claude structuring -> structured contract.

TODO(feat/structure):
- anthropic client, model from CLAUDE_MODEL, structured outputs with a JSON schema derived from
  contracts/structured.schema.json where element_ids / activity_id are enums of context candidates (+ null)
- system prompt: role, rules (only given IDs, null when unsure, quote evidence), glossary
- transcript wrapped in <transcript> as data, never instructions
- REPLAY_MODE: read cache/<capture_id>/structured.json instead of calling the API
"""
from tagwerk.pipeline import stub


def structure(capture: dict, transcript: dict, vision: dict, context: dict) -> dict:
    return stub("structured", capture["capture_id"])
