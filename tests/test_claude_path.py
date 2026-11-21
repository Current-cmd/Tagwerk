"""The Claude structuring path with a fake client: schema enums, tool parsing, and fallback to rules on errors."""
import sys
import types

import pytest

from tagwerk.pipeline import structure
from tagwerk.project import Project


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    import tagwerk.pipeline.context as context
    from tagwerk.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": None, "precipMm": None, "windKmh": None,
                                                              "source": "test"})
    p = Project.from_seed()
    p.load_history()
    cap = {"capture_id": "cl1", "zone_id": "Z-AUDIENCE", "note": "Reihe A montiert"}
    tr = {"capture_id": "cl1", "lang": "de", "segments": [{"start": 0.0, "end": 2.0, "text": "Reihe A montiert"}]}
    vis = {"capture_id": "cl1", "frames": []}
    ctx = context.build_context(cap, vis, p)
    yield p, cap, tr, vis, ctx
    get_settings.cache_clear()


def _fake_anthropic(monkeypatch, behaviour):
    calls = {}

    class Messages:
        def create(self, **kw):
            calls.update(kw)
            return behaviour(kw)

    class Client:
        def __init__(self, api_key):
            self.messages = Messages()

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=Client))
    return calls


def test_claude_tool_result_is_used(env, monkeypatch):
    p, cap, tr, vis, ctx = env
    out = {"labour_present": [], "absences": [], "material_delivered": [], "special_events": [], "unmatched": [],
           "work_done": [{"element_ids": ["E-ROW-A"], "activity_id": "A1080", "state_proposed": "installed",
                          "evidence": "voice", "quote": "Reihe A montiert", "t": 0.0}]}
    block = types.SimpleNamespace(type="tool_use", input=out)
    calls = _fake_anthropic(monkeypatch, lambda kw: types.SimpleNamespace(content=[block]))
    s = structure.structure(cap, tr, vis, ctx, p)
    assert s["capture_id"] == "cl1" and s["work_done"][0]["element_ids"] == ["E-ROW-A"]
    schema = calls["tools"][0]["input_schema"]
    enum = schema["properties"]["work_done"]["items"]["properties"]["element_ids"]["items"]["enum"]
    assert "E-ROW-A" in enum and calls["tool_choice"]["name"] == "record_site_log"
    assert "<transcript>" in calls["messages"][0]["content"]


def test_claude_error_falls_back_to_rules(env, monkeypatch):
    p, cap, tr, vis, ctx = env

    def boom(kw):
        raise RuntimeError("API down")

    _fake_anthropic(monkeypatch, boom)
    s = structure.structure(cap, tr, vis, ctx, p)
    assert any(w["element_ids"] == ["E-ROW-A"] for w in s["work_done"])  # rules still found it


def test_claude_cannot_claim_voice_without_speech(env, monkeypatch):
    p, cap, tr, vis, ctx = env
    cap = {**cap, "capture_id": "cl2", "note": None}
    tr = {**tr, "capture_id": "cl2", "segments": []}
    out = {"labour_present": [], "absences": [], "material_delivered": [], "special_events": [], "unmatched": [],
           "work_done": [{"element_ids": ["E-ROW-A"], "activity_id": None, "state_proposed": "installed",
                          "evidence": "both", "quote": "Reihe A montiert", "t": None}]}
    block = types.SimpleNamespace(type="tool_use", input=out)
    _fake_anthropic(monkeypatch, lambda kw: types.SimpleNamespace(content=[block]))
    s = structure.structure(cap, tr, vis, ctx, p)
    assert s["work_done"][0]["evidence"] == "vision"


def test_invalid_claude_output_falls_back(env, monkeypatch):
    p, cap, tr, vis, ctx = env
    cap = {**cap, "capture_id": "cl3"}
    tr = {**tr, "capture_id": "cl3"}
    block = types.SimpleNamespace(type="tool_use", input={"work_done": [{"element_ids": ["E-ROW-A"]}]})
    _fake_anthropic(monkeypatch, lambda kw: types.SimpleNamespace(content=[block]))
    s = structure.structure(cap, tr, vis, ctx, p)
    assert s["work_done"] and s["work_done"][0]["evidence"] in ("voice", "both")  # rules result
