from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.middleware.production_guards import ProductionGuardMiddleware, _secure_match


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(ProductionGuardMiddleware)

    @app.post("/api/auth/setup")
    def setup():
        return {"ok": True}

    @app.post("/api/super-admin/products/{product_id}/purge")
    def purge(product_id: int):
        return {"ok": True, "product_id": product_id}

    @app.get("/health")
    def health():
        return {"ok": True}

    return TestClient(app)


def _production(monkeypatch, *, setup_token="s" * 32, destructive_token="d" * 32):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "setup_token", setup_token)
    monkeypatch.setattr(settings, "destructive_operation_token", destructive_token)


def test_secure_match_fails_closed_for_missing_values():
    assert _secure_match(None, "expected") is False
    assert _secure_match("provided", None) is False
    assert _secure_match("", "expected") is False
    assert _secure_match("expected", "expected") is True
    assert _secure_match("wrong", "expected") is False


def test_non_production_requests_are_not_guarded(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.delenv("ENABLE_DESTRUCTIVE_PURGE", raising=False)

    client = _client()
    assert client.post("/api/auth/setup").status_code == 200
    assert client.post("/api/super-admin/products/7/purge").status_code == 200


def test_production_setup_requires_configured_token(monkeypatch):
    _production(monkeypatch, setup_token=None)
    client = _client()

    response = client.post("/api/auth/setup")

    assert response.status_code == 503
    assert "SETUP_TOKEN" in response.json()["detail"]


def test_production_setup_rejects_wrong_token_and_accepts_exact_token(monkeypatch):
    token = "setup-token-" + "x" * 32
    _production(monkeypatch, setup_token=token)
    client = _client()

    rejected = client.post("/api/auth/setup", headers={"X-Setup-Token": "wrong"})
    accepted = client.post("/api/auth/setup", headers={"X-Setup-Token": token})

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json() == {"ok": True}


def test_production_purge_is_disabled_by_default(monkeypatch):
    _production(monkeypatch)
    monkeypatch.delenv("ENABLE_DESTRUCTIVE_PURGE", raising=False)
    client = _client()

    response = client.post("/api/super-admin/products/9/purge")

    assert response.status_code == 403
    assert "deshabilitada" in response.json()["detail"]


def test_production_purge_requires_both_confirmation_and_separate_token(monkeypatch):
    destructive_token = "destructive-token-" + "y" * 32
    _production(monkeypatch, destructive_token=destructive_token)
    monkeypatch.setenv("ENABLE_DESTRUCTIVE_PURGE", "true")
    client = _client()

    missing_confirmation = client.post(
        "/api/super-admin/products/9/purge",
        headers={"X-Destructive-Operation-Token": destructive_token},
    )
    missing_token = client.post(
        "/api/super-admin/products/9/purge",
        headers={"X-Confirm-Destructive-Operation": "PURGE_PRODUCT"},
    )
    wrong_confirmation = client.post(
        "/api/super-admin/products/9/purge",
        headers={
            "X-Confirm-Destructive-Operation": "YES",
            "X-Destructive-Operation-Token": destructive_token,
        },
    )

    assert missing_confirmation.status_code == 403
    assert missing_token.status_code == 403
    assert wrong_confirmation.status_code == 403


def test_production_purge_passes_only_with_explicit_confirmation_and_token(monkeypatch):
    destructive_token = "destructive-token-" + "z" * 32
    _production(monkeypatch, destructive_token=destructive_token)
    monkeypatch.setenv("ENABLE_DESTRUCTIVE_PURGE", "true")
    client = _client()

    response = client.post(
        "/api/super-admin/products/11/purge",
        headers={
            "X-Confirm-Destructive-Operation": "PURGE_PRODUCT",
            "X-Destructive-Operation-Token": destructive_token,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "product_id": 11}
