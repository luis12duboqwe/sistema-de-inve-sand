"""No live integration permitted from demo scripts by default."""
from pathlib import Path
import importlib.util
import sys
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import n8n_sandbox_probe as probe


@pytest.mark.parametrize("url", [
    "https://example.com/api",
    "http://example.com/api",
    "http://192.168.1.10:8000/api",
    "http://localhost:8000/not-an-api",
    "http://user:password@localhost:8000/api",
])
def test_disallows_non_isolated_or_malformed_target(url):
    with pytest.raises(ValueError):
        probe.validate_target(url, "testing", True, "synthetic-jwt")


def test_requires_explicit_test_mode_and_bearer():
    with pytest.raises(ValueError):
        probe.validate_target("http://127.0.0.1:8001/api", "production", True, "synthetic")
    with pytest.raises(ValueError):
        probe.validate_target("http://127.0.0.1:8001/api", "testing", False, "synthetic")
    with pytest.raises(ValueError):
        probe.validate_target("http://127.0.0.1:8001/api", "testing", True, "")


def test_default_script_does_not_call_network(monkeypatch):
    monkeypatch.delenv("SOFTMOBILE_TEST_JWT", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "testing")
    with patch.object(probe, "urlopen", side_effect=AssertionError("Network attempted")):
        with pytest.raises(SystemExit) as exc:
            probe.main(["--api-url", "http://127.0.0.1:8001/api"])
    assert exc.value.code == 2


def test_discovery_authenticates_and_checks_real_response_shape():
    class Reply:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def read(self):
            return b'{"items":[{"id":1,"tipo":"bot_ia"},{"id":2,"tipo":"vendedor_humano"}]}'

    def fake_open(request, timeout=0):
        assert timeout > 0
        assert request.get_header("Authorization") == "Bearer synthetic-jwt"
        assert request.full_url == "http://127.0.0.1:8001/api/sales-profiles"
        assert request.get_method() == "GET"
        return Reply()

    with patch.object(probe, "urlopen", side_effect=fake_open):
        assert probe.probe_discovery("http://127.0.0.1:8001/api", "synthetic-jwt") == 0
