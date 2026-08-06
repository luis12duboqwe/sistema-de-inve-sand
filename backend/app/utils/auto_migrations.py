"""Small fail-fast compatibility migrations executed during startup.

These migrations exist for installations created before the current models.
Fresh development SQLite databases are created from SQLAlchemy metadata and do
not need PostgreSQL-specific ALTER statements.
"""

import logging

from sqlalchemy import inspect, text

import app.database as database


logger = logging.getLogger(__name__)


def _apply_daily_close_migration() -> None:
    """Apply fields used by daily-close validation to the active database."""
    engine = database.engine
    inspector = inspect(engine)

    with engine.begin() as conn:
        if "system_config" not in inspector.get_table_names():
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS system_config (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(100) UNIQUE NOT NULL,
                        value TEXT,
                        description VARCHAR(255),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_by VARCHAR(100)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "idx_system_config_key ON system_config (key)"
                )
            )
            logger.info("Auto-migration: tabla system_config creada")

        existing_cols = {
            column["name"] for column in inspect(conn).get_columns("orders")
        }

        if "validada_at" not in existing_cols:
            conn.execute(
                text(
                    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS "
                    "validada_at TIMESTAMP WITH TIME ZONE"
                )
            )
            logger.info("Auto-migration: columna validada_at agregada a orders")

        if "validated_by" not in existing_cols:
            conn.execute(
                text(
                    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS "
                    "validated_by VARCHAR(100)"
                )
            )
            logger.info("Auto-migration: columna validated_by agregada a orders")


def _apply_transfer_receiving_fields_migration() -> None:
    engine = database.engine
    inspector = inspect(engine)
    existing_cols = {
        column["name"] for column in inspector.get_columns("stock_transfers")
    }

    statements = {
        "received_quantity": (
            "ALTER TABLE stock_transfers ADD COLUMN IF NOT EXISTS "
            "received_quantity INTEGER"
        ),
        "missing_quantity": (
            "ALTER TABLE stock_transfers ADD COLUMN IF NOT EXISTS "
            "missing_quantity INTEGER"
        ),
        "incident_notes": (
            "ALTER TABLE stock_transfers ADD COLUMN IF NOT EXISTS "
            "incident_notes TEXT"
        ),
    }

    with engine.begin() as conn:
        for column, statement in statements.items():
            if column not in existing_cols:
                conn.execute(text(statement))
                logger.info(
                    "Auto-migration: columna %s agregada a stock_transfers",
                    column,
                )


def run_auto_migrations() -> bool:
    """Apply compatibility migrations and fail startup on any PostgreSQL error."""
    engine = database.engine
    if engine.dialect.name != "postgresql":
        logger.info(
            "Auto-migrations PostgreSQL omitidas para dialecto %s",
            engine.dialect.name,
        )
        return True

    logger.info("Ejecutando auto-migraciones de compatibilidad...")
    try:
        _apply_daily_close_migration()
        _apply_transfer_receiving_fields_migration()
    except Exception:
        logger.exception(
            "Fallo crítico aplicando migraciones; se cancela el arranque para "
            "evitar operar con un esquema incompleto"
        )
        raise

    logger.info("Auto-migraciones completadas")
    return True
