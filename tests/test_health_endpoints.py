import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


READY_CONFIG = {
    "is_production": False,
    "ready": True,
    "warnings": [],
    "config": {
        "database": "SQLite",
        "logging_enabled": True,
        "backups_enabled": False,
        "email_configured": False,
        "ai_enabled": True,
        "maintenance_mode": False,
    },
}


def test_api_health_is_liveness_and_reports_database(monkeypatch):
    monkeypatch.setattr("app.main.check_db_connection", lambda: True)

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "alive"
    assert payload["database"] == "connected"


def test_api_ready_requires_config_and_database(monkeypatch):
    monkeypatch.setattr("app.main.check_db_connection", lambda: True)
    monkeypatch.setattr("app.main.check_production_readiness", lambda: READY_CONFIG)

    with TestClient(app) as client:
        response = client.get("/api/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["database"] == "connected"
    assert payload["status"] == "ready"


def test_api_ready_returns_503_when_database_is_down(monkeypatch):
    monkeypatch.setattr("app.main.check_db_connection", lambda: False)
    monkeypatch.setattr("app.main.check_production_readiness", lambda: READY_CONFIG)

    with TestClient(app) as client:
        response = client.get("/api/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["ready"] is False
    assert payload["database"] == "disconnected"
    assert any("PostgreSQL" in warning for warning in payload["warnings"])
