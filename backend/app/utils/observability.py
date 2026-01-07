"""Utilities for observability features such as Sentry error tracking."""

from __future__ import annotations

import logging

from app.config import settings

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
except ImportError:  # pragma: no cover - optional dependency guard
    sentry_sdk = None  # type: ignore[assignment]
    FastApiIntegration = None  # type: ignore[assignment]
    LoggingIntegration = None  # type: ignore[assignment]
    SqlalchemyIntegration = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
_sentry_initialized = False


def initialize_observability() -> None:
    """Configure optional observability providers.

    Currently this sets up Sentry when a DSN is present. The call is idempotent
    to allow reuse from tests or workers without re-initializing the SDK.
    """

    global _sentry_initialized

    if _sentry_initialized:
        return

    dsn = settings.sentry_dsn
    if not dsn:
        logger.info("Sentry DSN not configured; skipping error tracking setup")
        return

    if (
        sentry_sdk is None
        or FastApiIntegration is None
        or LoggingIntegration is None
        or SqlalchemyIntegration is None
    ):
        logger.warning("sentry-sdk is not available even though DSN is set")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment or settings.environment,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        send_default_pii=False,
    )

    _sentry_initialized = True
    logger.info(
        "Sentry observability initialized",
        extra={
            "environment": settings.sentry_environment or settings.environment,
            "traces_sample_rate": settings.sentry_traces_sample_rate,
            "profiles_sample_rate": settings.sentry_profiles_sample_rate,
        },
    )
