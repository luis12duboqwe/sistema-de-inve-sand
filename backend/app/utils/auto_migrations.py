"""Versioned fail-fast compatibility migrations executed during startup.

Fresh databases are created from SQLAlchemy metadata first. Existing installations
may still require ALTER statements because ``create_all`` does not add columns to
existing tables. This module applies those compatibility changes exactly once,
records them in ``schema_migrations`` and validates the critical schema before the
application starts serving traffic.
"""

from collections.abc import Callable
import logging

from sqlalchemy import inspect, text

import app.database as database


logger = logging.getLogger(__name__)

MIGRATION_TABLE = "schema_migrations"


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
    existing_cols = {
        column["name"] for column in inspect(engine).get_columns("stock_transfers")
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


MIGRATIONS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("20260805_01_daily_close_validation", _apply_daily_close_migration),
    ("20260805_02_transfer_receiving_fields", _apply_transfer_receiving_fields_migration),
)


def _ensure_migration_table() -> None:
    with database.engine.begin() as conn:
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                    id VARCHAR(100) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
                """
            )
        )


def _get_applied_migrations() -> set[str]:
    with database.engine.connect() as conn:
        rows = conn.execute(text(f"SELECT id FROM {MIGRATION_TABLE}"))
        return {str(row[0]) for row in rows}


def _mark_migration_applied(migration_id: str) -> None:
    with database.engine.begin() as conn:
        conn.execute(
            text(
                f"INSERT INTO {MIGRATION_TABLE} (id) VALUES (:migration_id) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"migration_id": migration_id},
        )


def _validate_critical_schema() -> None:
    inspector = inspect(database.engine)
    table_names = set(inspector.get_table_names())
    required_tables = {"orders", "stock_transfers", "system_config", MIGRATION_TABLE}
    missing_tables = sorted(required_tables - table_names)
    if missing_tables:
        raise RuntimeError(
            "Esquema incompleto: faltan tablas críticas: " + ", ".join(missing_tables)
        )

    required_columns = {
        "orders": {"validada_at", "validated_by"},
        "stock_transfers": {"received_quantity", "missing_quantity", "incident_notes"},
    }
    missing_columns: list[str] = []
    for table, required in required_columns.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for column in sorted(required - existing):
            missing_columns.append(f"{table}.{column}")

    if missing_columns:
        raise RuntimeError(
            "Esquema incompleto: faltan columnas críticas: " + ", ".join(missing_columns)
        )


def run_auto_migrations() -> bool:
    """Apply pending compatibility migrations and fail startup on schema errors."""
    engine = database.engine
    if engine.dialect.name != "postgresql":
        logger.info(
            "Migraciones PostgreSQL versionadas omitidas para dialecto %s",
            engine.dialect.name,
        )
        return True

    logger.info("Ejecutando migraciones versionadas de compatibilidad...")
    try:
        _ensure_migration_table()
        applied = _get_applied_migrations()

        for migration_id, migration in MIGRATIONS:
            if migration_id in applied:
                logger.debug("Migración %s ya aplicada", migration_id)
                continue

            logger.info("Aplicando migración %s", migration_id)
            migration()
            _mark_migration_applied(migration_id)

        _validate_critical_schema()
    except Exception:
        logger.exception(
            "Fallo crítico aplicando/verificando migraciones; se cancela el "
            "arranque para evitar operar con un esquema incompleto"
        )
        raise

    logger.info("Migraciones versionadas completadas y esquema validado")
    return True
