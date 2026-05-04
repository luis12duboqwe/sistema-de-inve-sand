from typing import Any
import json

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config_production import prod_settings
from app.models import SalesProfile
from app.routers import channel_integrations


class _DummyAIResponse:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.tokens_used = 21


def test_verify_whatsapp_webhook(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(prod_settings, "WHATSAPP_VERIFY_TOKEN", "token-wh")

    ok = client.get(
        "/api/channels/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "token-wh",
            "hub.challenge": "1234",
        },
    )
    assert ok.status_code == 200
    assert ok.json() == 1234

    bad = client.get(
        "/api/channels/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "token-invalido",
            "hub.challenge": "999",
        },
    )
    assert bad.status_code == 403


def test_whatsapp_webhook_processes_and_replies(
    client: TestClient,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "bot-whatsapp")
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")

    ai_calls: list[dict[str, Any]] = []
    sent_messages: list[dict[str, str]] = []

    def fake_handle_message(request: Any, db: Any, auth_context: Any) -> _DummyAIResponse:
        ai_calls.append(
            {
                "sales_profile_slug": request.sales_profile_slug,
                "customer_phone": request.customer_phone,
                "message_content": request.message_content,
            }
        )
        return _DummyAIResponse("Hola 👋, te ayudo con eso")

    async def fake_send(channel: str, recipient: str, text: str, integration_config: dict[str, Any] | None = None) -> None:
        sent_messages.append({"channel": channel, "recipient": recipient, "text": text})

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", fake_handle_message)
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", fake_send)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "contacts": [
                                {"wa_id": "50499990000", "profile": {"name": "Cliente Demo"}}
                            ],
                            "messages": [
                                {
                                    "id": "wamid.ABC123",
                                    "from": "50499990000",
                                    "type": "text",
                                    "text": {"body": "Hola, tienen iPhone?"},
                                }
                            ],
                        },
                    }
                ]
            }
        ],
    }

    response = client.post("/api/channels/whatsapp/webhook", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["processed_count"] == 1
    assert data["failed_count"] == 0
    assert ai_calls
    assert ai_calls[0]["sales_profile_slug"] == "bot-whatsapp"
    assert sent_messages
    assert sent_messages[0]["channel"] == "whatsapp"
    assert sent_messages[0]["recipient"] == "50499990000"

    duplicate = client.post("/api/channels/whatsapp/webhook", json=payload)
    assert duplicate.status_code == 200
    duplicate_data = duplicate.json()
    assert duplicate_data["processed_count"] == 0
    assert duplicate_data["skipped_duplicates"] == 1


def test_channels_health_snapshot(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(prod_settings, "META_VERIFY_TOKEN", "verify-global")
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "bot-whatsapp")
    monkeypatch.setattr(prod_settings, "WHATSAPP_ACCESS_TOKEN", "token-wh")
    monkeypatch.setattr(prod_settings, "WHATSAPP_PHONE_NUMBER_ID", "phone-id")
    monkeypatch.setattr(prod_settings, "META_PAGE_ACCESS_TOKEN", "token-page")
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "app-secret")
    monkeypatch.setattr(prod_settings, "CHANNEL_MESSAGE_TTL_SECONDS", 900)

    response = client.get("/api/channels/health")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "ok"
    assert data["ready"] is True
    assert data["global"]["has_verify_token"] is True
    assert data["global"]["has_default_sales_profile"] is True
    assert data["global"]["signature_validation_enabled"] is True
    assert data["global"]["message_ttl_seconds"] == 900
    assert data["channels"]["whatsapp"]["ready"] is True
    assert data["channels"]["messenger"]["ready"] is True
    assert data["channels"]["instagram"]["ready"] is True


def test_whatsapp_webhook_routes_by_profile_phone_number_id(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")

    profile_a = SalesProfile(
        name="Softmobile Bot",
        slug="softmobile-bot",
        tipo="bot_ia",
        canales=json.dumps(["whatsapp"]),
        active=True,
        configuracion=json.dumps(
            {
                "channel_integrations": {
                    "whatsapp": {
                        "phone_number_id": "11111",
                        "access_token": "token-a",
                        "verify_token": "verify-a",
                    }
                }
            }
        ),
    )
    profile_b = SalesProfile(
        name="Techstore Bot",
        slug="techstore-bot",
        tipo="bot_ia",
        canales=json.dumps(["whatsapp"]),
        active=True,
        configuracion=json.dumps(
            {
                "channel_integrations": {
                    "whatsapp": {
                        "phone_number_id": "22222",
                        "access_token": "token-b",
                        "verify_token": "verify-b",
                    }
                }
            }
        ),
    )
    db_session.add(profile_a)
    db_session.add(profile_b)
    db_session.commit()

    ai_calls: list[dict[str, Any]] = []
    send_calls: list[dict[str, Any]] = []

    def fake_handle_message(request: Any, db: Any, auth_context: Any) -> _DummyAIResponse:
        ai_calls.append({"sales_profile_slug": request.sales_profile_slug})
        return _DummyAIResponse("Respuesta enrutada")

    async def fake_send(channel: str, recipient: str, text: str, integration_config: dict[str, Any] | None = None) -> None:
        send_calls.append(
            {
                "channel": channel,
                "recipient": recipient,
                "token": (integration_config or {}).get("access_token"),
            }
        )

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", fake_handle_message)
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", fake_send)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "22222"},
                            "messages": [
                                {
                                    "id": "wamid.222",
                                    "from": "50477770000",
                                    "type": "text",
                                    "text": {"body": "Hola"},
                                }
                            ],
                        },
                    }
                ]
            }
        ],
    }

    response = client.post("/api/channels/whatsapp/webhook", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["processed_count"] == 1
    assert data["processed"][0]["sales_profile_slug"] == "techstore-bot"
    assert ai_calls and ai_calls[0]["sales_profile_slug"] == "techstore-bot"
    assert send_calls and send_calls[0]["token"] == "token-b"


def test_verify_whatsapp_webhook_accepts_profile_verify_token(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = SalesProfile(
        name="Perfil Verify",
        slug="perfil-verify",
        tipo="bot_ia",
        canales=json.dumps(["whatsapp"]),
        active=True,
        configuracion=json.dumps(
            {
                "channel_integrations": {
                    "whatsapp": {
                        "phone_number_id": "99999",
                        "access_token": "token-v",
                        "verify_token": "verify-from-profile",
                    }
                }
            }
        ),
    )
    db_session.add(profile)
    db_session.commit()

    response = client.get(
        "/api/channels/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-from-profile",
            "hub.challenge": "4321",
        },
    )
    assert response.status_code == 200
    assert response.json() == 4321
