import os

# fixture stubs stand in for missing GPU libraries only inside tests
os.environ.setdefault("TAGWERK_STUBS", "1")
# every test app runs in dev mode (no auth) unless the test sets API_TOKEN itself (tests/test_hardening.py)
os.environ["API_TOKEN"] = ""
os.environ["TAGWERK_DEV"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("NEO4J_URI", "")
    monkeypatch.setenv("GPU_WORKER_URL", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("REPLAY_MODE", "false")
    for k in ("ALLOW_PROJECT_CREATE", "MAX_UPLOAD_MB", "MAX_UPLOAD_FILES"):
        monkeypatch.delenv(k, raising=False)
    import tagwerk.graph.store as store
    import tagwerk.pipeline.context as context
    import tagwerk.state as state
    from tagwerk.config import get_settings

    get_settings.cache_clear()
    store._store = None
    state.reset()
    monkeypatch.setattr(context, "weather", lambda lat, lon: {"tempC": 5.0, "precipMm": 0.0, "windKmh": 8.0,
                                                              "source": "test"})
    from tagwerk.api.app import _results, app

    _results.clear()
    with TestClient(app) as c:
        yield c
