"""Sentry has exactly one initializer even when legacy entrypoint is used."""
from types import SimpleNamespace
from unittest.mock import Mock

from app.utils import observability, sentry_config


def test_legacy_sentry_initializer_is_idempotent_with_canonical(monkeypatch):
    fake_init = Mock()
    monkeypatch.setattr(
        observability, "settings",
        SimpleNamespace(
            sentry_dsn="https://public@example.invalid/123",
            sentry_environment="test", environment="testing",
            sentry_traces_sample_rate=0.0, sentry_profiles_sample_rate=0.0,
        ),
    )
    monkeypatch.setattr(observability, "sentry_sdk", SimpleNamespace(init=fake_init))
    monkeypatch.setattr(observability, "FastApiIntegration", lambda **_kw: object())
    monkeypatch.setattr(observability, "LoggingIntegration", lambda **_kw: object())
    monkeypatch.setattr(observability, "SqlalchemyIntegration", lambda **_kw: object())
    monkeypatch.setattr(observability, "_sentry_initialized", False)

    sentry_config.init_sentry()
    observability.initialize_observability()
    sentry_config.init_sentry()

    assert fake_init.call_count == 1
    assert fake_init.call_args.kwargs["send_default_pii"] is False
