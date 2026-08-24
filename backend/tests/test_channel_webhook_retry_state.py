from datetime import UTC, datetime, timedelta
from typing import Any

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config_production import prod_settings
from app.models import ProcessedMessage
from app.routers import channel_webhook_integrity


def _payload(message_id: str) -> dict[str, Any]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": "50499992222",
                                    "type": "text",
                                    "text": {"body": "Hola de nuevo"},
                                }
                            ]
                        },
                    }
                ]
            }
        ],
    }


def test_pending_delivery_context_failure_returns_to_retryable_state(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")
    message_id = "wamid.PENDING-CONTEXT-FAILURE"
    row = ProcessedMessage(
        message_id=message_id,
        channel="whatsapp",
        customer_phone="50499992222",
        delivery_status="pending_delivery",
        reply_text="Respuesta que no debe perderse",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(row)
    db_session.commit()

    def fail_context(*args: Any, **kwargs: Any):
        raise RuntimeError("configuración temporalmente indisponible")

    monkeypatch.setattr(channel_webhook_integrity, "_cached_delivery_context", fail_context)

    response = client.post("/api/channels/whatsapp/webhook", json=_payload(message_id))

    assert response.status_code == 502, response.text
    db_session.expire_all()
    preserved = db_session.query(ProcessedMessage).filter(ProcessedMessage.message_id == message_id).one()
    assert preserved.delivery_status == "pending_delivery"
    assert preserved.reply_text == "Respuesta que no debe perderse"
