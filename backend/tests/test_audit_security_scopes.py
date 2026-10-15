from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import get_current_user_optional
from app.config_production import prod_settings
from app.main import app
from app.models import Customer, InteractionLog, Order, ProcessedMessage, SalesProfile, User, UserLocationAccess
from app.routers.ai_intelligence import _create_order_from_ai_payload
from app.schemas import AICreateOrderRequest
from .helpers import seed_location_and_sales_profile


def _limited_ai_user(user_id, *, can_manage_ai):
    permissions = [SimpleNamespace(slug="ai:manage")] if can_manage_ai else []
    return SimpleNamespace(
        id=user_id, username="ai-scoped", is_active=True, is_superuser=False,
        role=SimpleNamespace(permissions=permissions),
    )


def test_ai_context_requires_ai_permission_before_exposing_customers(client, db_session, monkeypatch):
    location, profile = seed_location_and_sales_profile(db_session)
    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", True)
    scoped = UserLocationAccess(user_id=78, location_id=location.id, can_view=True)
    db_session.add(User(id=78, username="ai-scoped", email="ai-scoped@test.local", hashed_password="test"))
    db_session.add(scoped)
    db_session.commit()
    payload = {
        "sales_profile_slug": profile.slug, "customer_phone": "50470009999",
        "customer_name": "Confidencial", "message_content": "hola",
    }

    app.dependency_overrides[get_current_user_optional] = lambda: _limited_ai_user(78, can_manage_ai=False)
    denied = client.post("/api/ai/context", json=payload)
    assert denied.status_code == 403

    app.dependency_overrides[get_current_user_optional] = lambda: _limited_ai_user(78, can_manage_ai=True)
    limited = client.post("/api/ai/context", json=payload)
    assert limited.status_code == 403
    assert db_session.query(Customer).filter(Customer.phone_number == "50470009999").count() == 0


def test_ai_order_creation_requires_orders_create_before_db_mutation(db_session):
    unauthorised = _limited_ai_user(100, can_manage_ai=True)
    payload = SimpleNamespace(items=[object()], source_location_id=1)
    before = db_session.query(Order).count()
    with pytest.raises(HTTPException) as error:
        _create_order_from_ai_payload(payload, db_session, unauthorised)
    assert error.value.status_code == 403
    assert db_session.query(Order).count() == before


def test_duplicate_message_cannot_return_other_customer_reply(client, db_session, monkeypatch):
    _location, profile = seed_location_and_sales_profile(db_session)
    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", True)
    customer_b = Customer(phone_number="50470000222", name="Cliente B")
    db_session.add(customer_b)
    db_session.flush()
    db_session.add(InteractionLog(
        customer_id=customer_b.id, sales_profile_id=profile.id,
        role="assistant", content="SECRETO_CLIENTE_B", tokens_used=0,
    ))
    db_session.add(ProcessedMessage(
        message_id=f"ai-duplicate-{uuid4().hex}", channel="whatsapp",
        customer_phone="50470000111", sales_profile_id=profile.id,
        expires_at=datetime.now(UTC)+timedelta(hours=2),
    ))
    db_session.commit()
    message = db_session.query(ProcessedMessage).order_by(ProcessedMessage.id.desc()).first()
    payload = {
        "sales_profile_slug": profile.slug, "customer_phone": "50470000222",
        "message_content": "hola", "message_id": message.message_id,
        "channel_hint": "whatsapp",
    }
    cross_customer = client.post("/api/ai/handle-message", json=payload)
    assert cross_customer.status_code == 409
    assert "SECRETO_CLIENTE_B" not in cross_customer.text

    payload["customer_phone"] = "50470000111"
    duplicate = client.post("/api/ai/handle-message", json=payload)
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["model"] == "duplicate-guard"
    assert "SECRETO_CLIENTE_B" not in duplicate.json()["reply"]

def test_expired_webhook_delivery_claim_survives_ai_cleanup(db_session):
    from datetime import UTC, datetime, timedelta
    from app.models import ProcessedMessage
    from app.routers.ai_intelligence import _cleanup_processed_messages
    from uuid import uuid4

    message_id = "recovery-" + uuid4().hex
    db_session.add(ProcessedMessage(
        message_id=message_id, channel="whatsapp",
        customer_phone="50470001234", sales_profile_id=None,
        delivery_status="pending_delivery", reply_text="Respuesta pendiente",
        expires_at=datetime.now(UTC) - timedelta(hours=2),
    ))
    db_session.commit()
    _cleanup_processed_messages(db_session)
    db_session.commit()
    retained = db_session.query(ProcessedMessage).filter_by(message_id=message_id).one()
    assert retained.reply_text == "Respuesta pendiente"
    assert retained.delivery_status == "pending_delivery"


def test_ai_message_failure_is_quarantined_not_replayed(client, db_session, monkeypatch):
    from uuid import uuid4
    from app.config_production import prod_settings
    from app.models import ProcessedMessage, SalesProfile
    from app.routers import ai_intelligence
    from app.main import app

    monkeypatch.setattr(prod_settings, "ENABLE_AI_FEATURES", True)
    profile = SalesProfile(name="AI quarantined", slug="ai-quarantined-" + uuid4().hex,
                           tipo="bot_ia", canales='["whatsapp"]', active=True)
    db_session.add(profile)
    db_session.commit()
    msg_id = "ai-failing-" + uuid4().hex
    calls = []

    def fail_after_claim(*_args, **_kwargs):
        calls.append("called")
        raise RuntimeError("artificial external service outage")

    monkeypatch.setattr(ai_intelligence, "get_ai_context", fail_after_claim)
    payload = {
        "sales_profile_slug": profile.slug,
        "customer_phone": "50470005551",
        "customer_name": "Test AI retry",
        "message_content": "hola",
        "message_id": msg_id,
        "channel_hint": "whatsapp",
    }
    # The isolated integration route must quarantine the already-persisted claim.
    from app.routers.ai_slug_integrity import handle_message_without_n8n_integrity
    from app.schemas import AIHandleMessageRequest
    with pytest.raises(RuntimeError):
        handle_message_without_n8n_integrity(
            AIHandleMessageRequest.model_validate(payload), db_session, None
        )
    stored = db_session.query(ProcessedMessage).filter_by(message_id=msg_id).one()
    assert stored.delivery_status == "ai_manual_recovery"
    with pytest.raises(HTTPException) as duplicate:
        handle_message_without_n8n_integrity(
            AIHandleMessageRequest.model_validate(payload), db_session, None
        )
    assert duplicate.value.status_code == 409
    assert calls == ["called"]
