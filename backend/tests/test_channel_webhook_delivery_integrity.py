import json
from typing import Any

from _pytest.monkeypatch import MonkeyPatch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config_production import prod_settings
from app.models import ProcessedMessage, SalesProfile
from app.routers import channel_integrations, channel_webhook_integrity


class _DummyAIResponse:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.tokens_used = 7


def _whatsapp_payload(message_id: str, *, phone_number_id: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "messages": [
            {
                "id": message_id,
                "from": "50499991111",
                "type": "text",
                "text": {"body": "Hola"},
            }
        ]
    }
    if phone_number_id:
        value["metadata"] = {"phone_number_id": phone_number_id}

    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"field": "messages", "value": value}]}],
    }


def test_ai_failure_releases_processing_claim_and_same_message_can_retry(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "retry-bot")
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")
    message_id = "wamid.RETRYABLE-FAILURE"

    def fail_ai(request: Any, db: Any, auth_context: Any) -> _DummyAIResponse:
        raise HTTPException(status_code=503, detail="AI temporalmente no disponible")

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", fail_ai)

    first = client.post("/api/channels/whatsapp/webhook", json=_whatsapp_payload(message_id))

    assert first.status_code == 502, first.text
    first_data = first.json()
    assert first_data["status"] == "retry_required"
    assert first_data["failed_count"] == 1
    assert db_session.query(ProcessedMessage).filter(ProcessedMessage.message_id == message_id).first() is None

    sent: list[str] = []

    def successful_ai(request: Any, db: Any, auth_context: Any) -> _DummyAIResponse:
        return _DummyAIResponse("Respuesta recuperada")

    async def successful_send(
        channel: str,
        recipient: str,
        text: str,
        integration_config: dict[str, Any] | None = None,
    ) -> None:
        sent.append(text)

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", successful_ai)
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", successful_send)

    retry = client.post("/api/channels/whatsapp/webhook", json=_whatsapp_payload(message_id))

    assert retry.status_code == 200, retry.text
    retry_data = retry.json()
    assert retry_data["processed_count"] == 1
    assert retry_data["skipped_duplicates"] == 0
    assert sent == ["Respuesta recuperada"]
    claim = db_session.query(ProcessedMessage).filter(ProcessedMessage.message_id == message_id).one()
    db_session.refresh(claim)
    assert claim.delivery_status == "delivered"
    assert claim.reply_text is None


def test_meta_send_failure_retries_cached_reply_without_rerunning_ai(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "send-retry-bot")
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")
    message_id = "wamid.RETRYABLE-SEND-FAILURE"
    ai_calls: list[str] = []

    def successful_ai(request: Any, db: Any, auth_context: Any) -> _DummyAIResponse:
        ai_calls.append(request.message_content)
        return _DummyAIResponse("Respuesta lista para enviar")

    async def fail_send(
        channel: str,
        recipient: str,
        text: str,
        integration_config: dict[str, Any] | None = None,
    ) -> None:
        raise HTTPException(status_code=502, detail="Meta temporalmente no disponible")

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", successful_ai)
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", fail_send)

    first = client.post("/api/channels/whatsapp/webhook", json=_whatsapp_payload(message_id))

    assert first.status_code == 502, first.text
    assert first.json()["status"] == "retry_required"
    assert first.json()["failed_count"] == 1
    assert ai_calls == ["Hola"]

    pending = db_session.query(ProcessedMessage).filter(ProcessedMessage.message_id == message_id).one()
    db_session.refresh(pending)
    assert pending.delivery_status == "pending_delivery"
    assert pending.reply_text == "Respuesta lista para enviar"

    sent: list[str] = []

    async def successful_send(
        channel: str,
        recipient: str,
        text: str,
        integration_config: dict[str, Any] | None = None,
    ) -> None:
        sent.append(text)

    monkeypatch.setattr(channel_integrations, "_send_channel_reply", successful_send)

    retry = client.post("/api/channels/whatsapp/webhook", json=_whatsapp_payload(message_id))

    assert retry.status_code == 200, retry.text
    retry_data = retry.json()
    assert retry_data["processed_count"] == 1
    assert retry_data["skipped_duplicates"] == 0
    assert retry_data["processed"][0]["delivery_retry"] is True
    assert sent == ["Respuesta lista para enviar"]
    # The provider retry must not invoke the AI/business side effects again.
    assert ai_calls == ["Hola"]

    delivered = db_session.query(ProcessedMessage).filter(ProcessedMessage.message_id == message_id).one()
    db_session.refresh(delivered)
    assert delivered.delivery_status == "delivered"
    assert delivered.reply_text is None


def test_post_ai_persistence_failure_quarantines_claim_without_rerunning_ai(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "quarantine-bot")
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")
    message_id = "wamid.POST-AI-PERSISTENCE-FAILURE"
    ai_calls: list[str] = []
    send_calls: list[str] = []

    def successful_ai(request: Any, db: Any, auth_context: Any) -> _DummyAIResponse:
        ai_calls.append(request.message_content)
        return _DummyAIResponse("Respuesta ya generada")

    def fail_reply_persistence(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("fallo temporal persistiendo respuesta")

    async def successful_send(
        channel: str,
        recipient: str,
        text: str,
        integration_config: dict[str, Any] | None = None,
    ) -> None:
        send_calls.append(text)

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", successful_ai)
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", successful_send)
    monkeypatch.setattr(channel_webhook_integrity, "_store_reply_for_delivery", fail_reply_persistence)

    first = client.post("/api/channels/whatsapp/webhook", json=_whatsapp_payload(message_id))

    assert first.status_code == 502, first.text
    assert ai_calls == ["Hola"]
    assert send_calls == []

    quarantined = db_session.query(ProcessedMessage).filter(ProcessedMessage.message_id == message_id).one()
    db_session.refresh(quarantined)
    assert quarantined.delivery_status == "manual_recovery"
    assert quarantined.reply_text is None

    # A provider retry is intentionally deduplicated: we prefer an operator-visible
    # recovery case over replaying already-committed AI/business side effects.
    retry = client.post("/api/channels/whatsapp/webhook", json=_whatsapp_payload(message_id))

    assert retry.status_code == 200, retry.text
    assert retry.json()["processed_count"] == 0
    assert retry.json()["skipped_duplicates"] == 1
    assert ai_calls == ["Hola"]
    assert send_calls == []


def test_successful_webhook_claim_is_associated_with_resolved_sales_profile(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")
    profile = SalesProfile(
        name="Delivery Integrity Bot",
        slug="delivery-integrity-bot",
        tipo="bot_ia",
        canales=json.dumps(["whatsapp"]),
        active=True,
        configuracion=json.dumps(
            {
                "channel_integrations": {
                    "whatsapp": {
                        "phone_number_id": "delivery-phone-id",
                        "access_token": "test-token",
                    }
                }
            }
        ),
    )
    db_session.add(profile)
    db_session.commit()

    def successful_ai(request: Any, db: Any, auth_context: Any) -> _DummyAIResponse:
        return _DummyAIResponse("Respuesta asociada")

    async def successful_send(
        channel: str,
        recipient: str,
        text: str,
        integration_config: dict[str, Any] | None = None,
    ) -> None:
        return None

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", successful_ai)
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", successful_send)

    message_id = "wamid.PROFILE-ASSOCIATION"
    response = client.post(
        "/api/channels/whatsapp/webhook",
        json=_whatsapp_payload(message_id, phone_number_id="delivery-phone-id"),
    )

    assert response.status_code == 200, response.text
    claim = db_session.query(ProcessedMessage).filter(ProcessedMessage.message_id == message_id).one()
    db_session.refresh(claim)
    assert claim.sales_profile_id == profile.id
    assert claim.delivery_status == "delivered"
    assert claim.reply_text is None


def test_delivered_message_remains_deduplicated_without_rerunning_ai(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "dedupe-bot")
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")
    ai_calls: list[str] = []
    sent: list[str] = []

    def successful_ai(request: Any, db: Any, auth_context: Any) -> _DummyAIResponse:
        ai_calls.append(request.message_content)
        return _DummyAIResponse("Una sola respuesta")

    async def successful_send(
        channel: str,
        recipient: str,
        text: str,
        integration_config: dict[str, Any] | None = None,
    ) -> None:
        sent.append(text)

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", successful_ai)
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", successful_send)

    message_id = "wamid.ALREADY-DELIVERED"
    first = client.post("/api/channels/whatsapp/webhook", json=_whatsapp_payload(message_id))
    duplicate = client.post("/api/channels/whatsapp/webhook", json=_whatsapp_payload(message_id))

    assert first.status_code == 200, first.text
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["processed_count"] == 0
    assert duplicate.json()["skipped_duplicates"] == 1
    assert ai_calls == ["Hola"]
    assert sent == ["Una sola respuesta"]
