from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.main import app
from app.models import Customer, InteractionLog, ProcessedMessage, SalesProfile


def _user_with_permissions(*permission_slugs: str):
    return SimpleNamespace(
        id=91,
        username="monitoring-user",
        email="monitoring@example.com",
        is_active=True,
        is_superuser=False,
        role=SimpleNamespace(
            permissions=[SimpleNamespace(slug=slug) for slug in permission_slugs]
        ),
    )


def _override_active_user(user):
    previous = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: user
    return previous


def _restore_active_user(previous) -> None:
    if previous is None:
        app.dependency_overrides.pop(get_current_active_user, None)
    else:
        app.dependency_overrides[get_current_active_user] = previous


def _add_sensitive_channel_audit_data(db_session: Session) -> SalesProfile:
    profile = SalesProfile(
        name="Private AI Profile",
        slug="private-ai-profile",
        tipo="bot_ia",
        canales='["whatsapp"]',
        active=True,
        configuracion="{}",
    )
    customer = Customer(
        phone_number="50499998888",
        name="Private Customer",
    )
    db_session.add_all([profile, customer])
    db_session.flush()

    db_session.add(
        InteractionLog(
            customer_id=customer.id,
            sales_profile_id=profile.id,
            role="user",
            content="Necesito información privada sobre mi pedido",
            tokens_used=12,
        )
    )
    db_session.add(
        ProcessedMessage(
            message_id="wamid.private-monitoring-audit",
            channel="whatsapp",
            customer_phone=customer.phone_number,
            sales_profile_id=profile.id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            delivery_status="delivered",
        )
    )
    db_session.commit()
    return profile


def test_reports_only_user_keeps_aggregate_status_but_cannot_read_channel_audit(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = _add_sensitive_channel_audit_data(db_session)
    previous = _override_active_user(_user_with_permissions("reports:view"))

    try:
        status_response = client.get("/api/channels/monitoring/status")
        audit_response = client.get(
            f"/api/channels/monitoring/audit/{profile.slug}"
        )
    finally:
        _restore_active_user(previous)

    assert status_response.status_code == 200, status_response.text
    assert audit_response.status_code == 403, audit_response.text
    assert "ai:manage" in audit_response.json()["detail"]
    assert "50499998888" not in audit_response.text
    assert "información privada" not in audit_response.text


def test_channel_audit_requires_reports_and_ai_management_permissions(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = _add_sensitive_channel_audit_data(db_session)

    ai_only_previous = _override_active_user(_user_with_permissions("ai:manage"))
    try:
        ai_only_response = client.get(
            f"/api/channels/monitoring/audit/{profile.slug}"
        )
    finally:
        _restore_active_user(ai_only_previous)

    assert ai_only_response.status_code == 403, ai_only_response.text
    assert "reports:view" in ai_only_response.json()["detail"]

    authorized_previous = _override_active_user(
        _user_with_permissions("reports:view", "ai:manage")
    )
    try:
        authorized_response = client.get(
            f"/api/channels/monitoring/audit/{profile.slug}"
        )
    finally:
        _restore_active_user(authorized_previous)

    assert authorized_response.status_code == 200, authorized_response.text
    payload = authorized_response.json()
    assert payload["interaction_count"] == 1
    assert payload["recent_interactions"][0]["content"].startswith(
        "Necesito información privada"
    )
    recent_messages = payload["processed_messages_by_channel"]["whatsapp"]["recent"]
    assert recent_messages[0]["customer_phone"] == "50499998888"
