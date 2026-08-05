import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


def test_api_health_returns_database_and_readiness(monkeypatch):
    monkeypatch.setattr("app.main.check_db_connection", lambda: True)
    monkeypatch.setattr(
        "app.main.check_production_readiness",
        lambda: {
            "is_production": False,
            "ready": True,
            "warnings": [],
            "config": {"database": "SQLite", "logging_enabled": True, "backups_enabled": False, "email_configured": False, "ai_enabled": True, "maintenance_mode": False},
        },
    )

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["database"] == "connected"
    assert payload["readiness"]["ready"] is True


def test_api_ready_reports_readiness(monkeypatch):
    monkeypatch.setattr(
        "app.main.check_production_readiness",
        lambda: {
            "is_production": False,
            "ready": True,
            "warnings": [],
            "config": {"database": "SQLite", "logging_enabled": True, "backups_enabled": False, "email_configured": False, "ai_enabled": True, "maintenance_mode": False},
        },
    )

    with TestClient(app) as client:
        response = client.get("/api/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["status"] == "ready"
