"""Versioned data migration for the canonical sales discount policy.

This migration is deliberately separate from schema migrations because it only
normalizes business configuration data. It still records its id in the shared
``schema_migrations`` ledger so it runs exactly once per database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import logging
import sqlite3

from sqlalchemy import inspect, text

import app.database as database


logger = logging.getLogger(__name__)

MIGRATION_ID = "20260925_01_ai_discount_policy_cap"
MAX_AUTOMATED_DISCOUNT = 0.03


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


def run_pricing_policy_migration() -> bool:
    """Clamp historical AI discount configuration to the automated 3% ceiling."""

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

    if already_applied:
        return True

    _backup_sqlite_if_needed()

    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE ai_profile_configs "
                "SET max_discount_rate = :max_discount "
                "WHERE max_discount_rate IS NOT NULL "
                "AND max_discount_rate > :max_discount"
            ),
            {"max_discount": MAX_AUTOMATED_DISCOUNT},
        )
        conn.execute(
            text(
                "UPDATE ai_profile_configs SET max_discount_rate = 0 "
                "WHERE max_discount_rate IS NOT NULL AND max_discount_rate < 0"
            )
        )

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
        "Normalización de descuentos IA aplicada; %s configuraciones históricas fueron limitadas a %.2f%%",
        max(int(result.rowcount or 0), 0),
        MAX_AUTOMATED_DISCOUNT * 100,
    )
    return True


__all__ = ["MAX_AUTOMATED_DISCOUNT", "MIGRATION_ID", "run_pricing_policy_migration"]
