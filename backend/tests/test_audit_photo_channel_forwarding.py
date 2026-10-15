"""Preserve the provider source when a multi-channel profile requests photos."""
from types import SimpleNamespace

from app.routers import channel_webhook_integrity, channel_integrations


def test_webhook_forwards_incoming_channel_to_ai_request(db_session, monkeypatch):
    captured = []
    monkeypatch.setattr(
        channel_integrations, "_resolve_profile_for_event",
        lambda _db, _event: ("multi-channel-profile", {"access_token": "synthetic"}),
    )
    def fake_ai(payload, *_args):
        captured.append(payload)
        return SimpleNamespace(reply="Bienvenido", tokens_used=0)
    monkeypatch.setattr(channel_integrations, "handle_message_without_n8n", fake_ai)

    for channel in ("instagram", "messenger", "whatsapp"):
        event = channel_integrations.IncomingEvent(
            channel=channel,
            external_message_id="m-" + channel,
            account_id="synthetic-account",
            customer_id="50495550111",
            customer_name="Cliente",
            text="Enviame fotos",
        )
        result, reply, config = channel_webhook_integrity._prepare_incoming_event(event, db_session)
        assert captured[-1].channel_hint == channel
        assert result["channel"] == channel
        assert reply == "Bienvenido"
