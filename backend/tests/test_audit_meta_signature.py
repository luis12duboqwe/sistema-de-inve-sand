"""Real HMAC verification at the HTTP Meta webhook boundary.

No Meta credentials or network access are used in these tests.
"""
import hashlib
import hmac
import json
from uuid import uuid4

from app.config_production import prod_settings
from app.models import ProcessedMessage
from app.routers import channel_integrations


def _signed_raw_payload(message_id: str) -> bytes:
    event = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"field": "messages", "value": {
            "messages": [{"id": message_id, "from": "50499991111",
                          "type": "text", "text": {"body": "Consulta firmada"}}],
        }}]}],
    }
    return json.dumps(event, sort_keys=True, separators=(",", ":")).encode()


def test_signed_meta_webhook_accepts_only_matching_raw_body(client, db_session, monkeypatch):
    secret = "only-for-tests-meta-secret-" + uuid4().hex
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", secret)
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "signed-qa-profile")

    class AIReply:
        reply = "Respuesta autorizada"
        tokens_used = 1

    sent = []

    async def fake_send(*args, **kwargs):
        sent.append(args)

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", lambda *a, **kw: AIReply())
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", fake_send)

    message_id = "signed-" + uuid4().hex
    raw = _signed_raw_payload(message_id)
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()

    signed = client.post(
        "/api/channels/whatsapp/webhook",
        content=raw,
        headers={
            "content-type": "application/json",
            "X-Hub-Signature-256": "sha256=" + signature,
        },
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["processed_count"] == 1
    assert len(sent) == 1
    assert db_session.query(ProcessedMessage).filter_by(message_id=message_id).count() == 1


def test_meta_webhook_rejects_missing_invalid_or_altered_signature_before_claim(client, db_session, monkeypatch):
    secret = "only-for-tests-meta-secret-" + uuid4().hex
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", secret)
    message_id = "unsigned-" + uuid4().hex
    raw = _signed_raw_payload(message_id)
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()

    cases = [
        (raw, {}),
        (raw, {"X-Hub-Signature-256": "sha256=" + "0" * 64}),
        (raw + b" ", {"X-Hub-Signature-256": "sha256=" + signature}),
    ]
    for body, headers in cases:
        response = client.post(
            "/api/channels/whatsapp/webhook",
            content=body,
            headers={"content-type": "application/json", **headers},
        )
        assert response.status_code in (401, 403), response.text

    assert db_session.query(ProcessedMessage).filter_by(message_id=message_id).count() == 0
