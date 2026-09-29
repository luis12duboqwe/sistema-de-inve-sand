"""Versioned data migration for the canonical sales discount policy.

The migration records its id in the shared ``schema_migrations`` ledger, but the
business invariant is intentionally re-checked on every startup. That makes the
startup path self-healing if an old/manual integration later writes a discount
above the automated ceiling or removes the canonical AI context rule.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import logging
import sqlite3

from sqlalchemy import inspect, text

import app.database as database
from app.utils.ai_sales_policy import (
    MAX_AUTOMATED_DISCOUNT_RATE,
    ensure_canonical_discount_context_rules,
)


logger = logging.getLogger(__name__)

MIGRATION_ID = "20260925_02_ai_discount_policy_cap_and_context"


def _backup_sqlite_if_needed() -> Path | None:
    if database.engine.dialect.name != "sqlite":
        return None

    database_name = database.engine.url.database
    if not database_name or database_name == ":memory:":
        return None

    source = Path(database_name).expanduser().resolve()
    if not source.exists():
        return None

    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"{source.stem}.pre-pricing-policy-{timestamp}{source.suffix or '.db'}"

    with sqlite3.connect(str(source)) as source_conn, sqlite3.connect(str(destination)) as destination_conn:
        source_conn.backup(destination_conn)

    logger.info("Backup SQLite previo a normalización de descuentos creado en %s", destination)
    return destination


def _normalize_ai_configs() -> int:
    """Enforce the invariant through the configured ORM session.

    Using ``SessionLocal`` keeps the data migration on the exact application/test
    database binding and avoids subtle connection/search-path drift while remaining
    fully idempotent.
    """

    from app.models import AIProfileConfig

    session = database.SessionLocal()
    capped_count = 0
    try:
        configs = session.query(AIProfileConfig).order_by(AIProfileConfig.id.asc()).all()
        max_discount = Decimal(str(MAX_AUTOMATED_DISCOUNT_RATE))
        zero = Decimal("0")

        for config in configs:
            current_discount = (
                Decimal(str(config.max_discount_rate))
                if config.max_discount_rate is not None
                else zero
            )
            if current_discount > max_discount:
                config.max_discount_rate = max_discount
                capped_count += 1
            elif current_discount < zero:
                config.max_discount_rate = zero

            normalized_rules = ensure_canonical_discount_context_rules(config.context_rules)
            if normalized_rules != str(config.context_rules or ""):
                config.context_rules = normalized_rules

        session.commit()
        return capped_count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_pricing_policy_migration() -> bool:
    """Normalize AI discount settings and continuously enforce the canonical rule."""

    engine = database.engine
    dialect = engine.dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        logger.info(
            "Normalización de descuentos omitida para dialecto no soportado %s",
            dialect,
        )
        return True

    table_names = set(inspect(engine).get_table_names())
    if "ai_profile_configs" not in table_names:
        return True

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "id VARCHAR(100) PRIMARY KEY, "
                + (
                    "applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    if dialect == "sqlite"
                    else "applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"
                )
                + ")"
            )
        )
        already_applied = conn.execute(
            text("SELECT 1 FROM schema_migrations WHERE id = :migration_id"),
            {"migration_id": MIGRATION_ID},
        ).first()

    # Only the first application needs a workstation backup. The normalization
    # itself remains idempotent and is deliberately re-run to enforce the invariant.
    if not already_applied:
        _backup_sqlite_if_needed()

    capped_count = _normalize_ai_configs()

    with engine.begin() as conn:
        if dialect == "sqlite":
            ledger_sql = (
                "INSERT OR IGNORE INTO schema_migrations (id) VALUES (:migration_id)"
            )
        else:
            ledger_sql = (
                "INSERT INTO schema_migrations (id) VALUES (:migration_id) "
                "ON CONFLICT (id) DO NOTHING"
            )
        conn.execute(text(ledger_sql), {"migration_id": MIGRATION_ID})

    logger.info(
        "Política de descuentos IA verificada; %s configuraciones fueron limitadas a %.2f%% en esta ejecución",
        capped_count,
        MAX_AUTOMATED_DISCOUNT_RATE * 100,
    )
    return True


__all__ = ["MIGRATION_ID", "run_pricing_policy_migration"]
