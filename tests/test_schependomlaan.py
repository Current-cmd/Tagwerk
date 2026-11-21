"""Real-data test: the imported Schependomlaan project (skipped when the generated seed is absent)."""
import pytest

from tagwerk.project import SEED_DIR, Project

SP = SEED_DIR / "projects" / "schependomlaan"
pytestmark = pytest.mark.skipif(not (SP / "elements.csv").exists(), reason="run scripts/import_schependomlaan.py")


@pytest.fixture(scope="module")
def sp():
    p = Project.from_seed(SP)
    p.load_history()
    return p


def test_import_shape(sp):
    assert len(sp.elements) > 1500 and len(sp.activities) >= 90
    assert {"Z-BG", "Z-1", "Z-2", "Z-DAK"} <= set(sp.zones)
    assert not [ch for c in sp.captures.values() for ch in c["changes"] if ch["action"] == "invalid"]


def test_forecast_and_overview_scale(sp):
    import time
    from datetime import date

    today = date.fromisoformat(sp.meta["data_date"])
    t = time.time()
    ov = sp.overview(today)
    assert time.time() - t < 2.0
    assert ov["kpi"]["priced"] is False and 0 < ov["kpi"]["pct_actual"] <= 100
    from tagwerk.contracts import validate

    validate("dashboard", sp.dashboard(today))


def test_dutch_note_targets_named_storey(sp, tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    import tagwerk.pipeline.context as context
    from tagwerk.config import get_settings
    from tagwerk.pipeline import structure

    get_settings.cache_clear()
    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": None, "precipMm": None, "windKmh": None,
                                                              "source": "test"})
    cap = {"capture_id": "sp-t", "zone_id": "Z-BG", "note": "Buitenblad tweede verdieping gemetseld. Twee metselaars ziek."}
    tr = {"capture_id": "sp-t", "lang": "nl", "segments": []}
    vis = {"capture_id": "sp-t", "frames": []}
    ctx = context.build_context(cap, vis, sp)
    s = structure.structure(cap, tr, vis, ctx, sp)
    els = {e for w in s["work_done"] for e in w["element_ids"]}
    assert els and all(sp.elements[e]["zone"] == "Z-2" for e in els)
    assert all(w["state_proposed"] == "installed" for w in s["work_done"])
    assert s["absences"] == [{"trade": "Metselaar", "count": 2, "reason": "abwesend"}]
