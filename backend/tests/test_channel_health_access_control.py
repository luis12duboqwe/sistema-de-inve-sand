import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import get_current_user_optional
from app.main import app
from app.models import SalesProfile


def _add_sensitive_profile(db_session: Session) -> SalesProfile:
    profile = SalesProfile(
        name="Secret Sales Profile",
        slug="secret-sales-profile",
        tipo="bot_ia",
        canales=json.dumps(["whatsapp"]),
        active=True,
        configuracion=json.dumps(
            {
                "channel_integrations": {
                    "whatsapp": {
                        "phone_number_id": "123456",
                        "access_token": "secret-token",
                        "verify_token": "secret-verify",
                    }
                }
            }
        ),
    )
    db_session.add(profile)
    db_session.commit()
    return profile


def _override_optional_user(user):
    previous = app.dependency_overrides.get(get_current_user_optional)
    app.dependency_overrides[get_current_user_optional] = lambda: user
    return previous


def _restore_optional_user(previous) -> None:
    if previous is None:
        app.dependency_overrides.pop(get_current_user_optional, None)
    else:
        app.dependency_overrides[get_current_user_optional] = previous


def test_channel_health_anonymous_poll_gets_redacted_summary_without_auth_error(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_sensitive_profile(db_session)
    previous = _override_optional_user(None)

    try:
        response = client.get("/api/channels/health")
    finally:
        _restore_optional_user(previous)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ok"
    assert isinstance(payload["ready"], bool)
    assert payload["diagnostics_restricted"] is True
    assert payload["profiles"] == []
    assert payload["global"]["missing"] == []
    assert payload["channels"]["whatsapp"]["missing"] == []
    assert "secret-sales-profile" not in response.text
    assert "Secret Sales Profile" not in response.text
    assert "secret-token" not in response.text
    assert "phone_number_id" not in response.text


def test_channel_health_user_without_ai_manage_gets_same_redacted_contract(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_sensitive_profile(db_session)
    restricted_user = SimpleNamespace(
        id=77,
        username="restricted",
        email="restricted@example.com",
        is_active=True,
        is_superuser=False,
        role=SimpleNamespace(permissions=[SimpleNamespace(slug="orders:view")]),
    )
    previous = _override_optional_user(restricted_user)

    try:
        response = client.get("/api/channels/health")
    finally:
        _restore_optional_user(previous)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["diagnostics_restricted"] is True
    assert payload["profiles"] == []
    assert "secret-sales-profile" not in response.text
    assert "secret-token" not in response.text


def test_channel_health_ai_manager_receives_detailed_diagnostics(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_sensitive_profile(db_session)
    manager = SimpleNamespace(
        id=88,
        username="ai-manager",
        email="ai-manager@example.com",
        is_active=True,
        is_superuser=False,
        role=SimpleNamespace(permissions=[SimpleNamespace(slug="ai:manage")]),
    )
    previous = _override_optional_user(manager)

    try:
        response = client.get("/api/channels/health")
    finally:
        _restore_optional_user(previous)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "diagnostics_restricted" not in payload
    assert payload["profiles"]
    assert payload["profiles"][0]["sales_profile_slug"] == "secret-sales-profile"
    assert payload["profiles"][0]["sales_profile_name"] == "Secret Sales Profile"


def test_channel_health_superuser_keeps_full_diagnostic_contract(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_sensitive_profile(db_session)

    response = client.get("/api/channels/health")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "diagnostics_restricted" not in payload
    assert "ready" in payload
    assert "global" in payload
    assert "channels" in payload
    assert payload["profiles"]
