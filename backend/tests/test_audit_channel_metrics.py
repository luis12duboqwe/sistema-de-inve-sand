"""Channel metrics must reflect canonical incoming webhook outcomes."""
from app.channel_audit import channel_metrics
from app.config_production import prod_settings
from app.routers import channel_integrations


def _event(message_id):
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"field": "messages", "value": {
            "messages": [{"id": message_id, "from": "50499991111",
                          "type": "text", "text": {"body": "Hola"}}],
        }}]}],
    }


def _count(metric, channel):
    return metric.get(channel, 0)


def test_channel_metrics_increment_for_success_and_duplicate(client, monkeypatch):
    from uuid import uuid4
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "metric-test-bot")

    async def send(_channel, _recipient, _text, _config=None):
        return None

    class Reply:
        reply = "Hola de regreso"
        tokens_used = 1

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", lambda *a, **kw: Reply())
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", send)
    before = channel_metrics.get_summary()
    message = _event("metric-" + uuid4().hex)

    first = client.post("/api/channels/whatsapp/webhook", json=message)
    duplicate = client.post("/api/channels/whatsapp/webhook", json=message)
    assert first.status_code == 200, first.text
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["skipped_duplicates"] == 1

    after = channel_metrics.get_summary()
    assert _count(after["messages_received"], "whatsapp") - _count(before["messages_received"], "whatsapp") == 2
    assert _count(after["messages_sent"], "whatsapp") - _count(before["messages_sent"], "whatsapp") == 1
    assert _count(after["duplicate_messages"], "whatsapp") - _count(before["duplicate_messages"], "whatsapp") == 1
    assert _count(after["api_errors"], "whatsapp") == _count(before["api_errors"], "whatsapp")


def test_channel_metrics_record_failed_delivery(client, monkeypatch):
    from uuid import uuid4
    from fastapi import HTTPException
    monkeypatch.setattr(prod_settings, "META_APP_SECRET", "")
    monkeypatch.setattr(prod_settings, "CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "metric-test-bot")

    class Reply:
        reply = "Respuesta preparada"
        tokens_used = 1

    async def fail_send(*_args, **_kwargs):
        raise HTTPException(status_code=502, detail="Simulated provider failure")

    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", lambda *a, **kw: Reply())
    monkeypatch.setattr(channel_integrations, "_send_channel_reply", fail_send)
    before = channel_metrics.get_summary()
    result = client.post("/api/channels/whatsapp/webhook", json=_event("metric-fail-" + uuid4().hex))
    assert result.status_code == 502

    after = channel_metrics.get_summary()
    assert _count(after["messages_received"], "whatsapp") - _count(before["messages_received"], "whatsapp") == 1
    assert _count(after["api_errors"], "whatsapp") - _count(before["api_errors"], "whatsapp") == 1
    assert _count(after["messages_sent"], "whatsapp") == _count(before["messages_sent"], "whatsapp")
