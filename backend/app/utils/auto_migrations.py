"""Versioned fail-fast compatibility migrations executed during startup.

Fresh databases are created from SQLAlchemy metadata first. Existing installations
may still require ALTER statements because ``create_all`` does not add columns to
existing tables. This module applies those compatibility changes exactly once,
records them in ``schema_migrations`` and validates the critical schema before the
application starts serving traffic.

Both PostgreSQL and the legacy Windows SQLite installation are supported. Before
SQLite is changed for the first time, a consistent copy of the database is written
to ``backend/backups`` so an in-place workstation upgrade never destroys the only
copy of the user's data.
"""

from collections.abc import Callable
from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3

from sqlalchemy import inspect, text

import app.database as database


logger = logging.getLogger(__name__)

MIGRATION_TABLE = "schema_migrations"
SUPPORTED_DIALECTS = {"postgresql", "sqlite"}


def _dialect_name() -> str:
    return database.engine.dialect.name


def _column_type(postgresql_type: str, sqlite_type: str) -> str:
    return sqlite_type if _dialect_name() == "sqlite" else postgresql_type


def _add_column_if_missing(table: str, column: str, column_type: str) -> None:
    existing_cols = {
        item["name"] for item in inspect(database.engine).get_columns(table)
    }
    if column in existing_cols:
        return

    with database.engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))
    logger.info("Auto-migration: columna %s agregada a %s", column, table)


def _apply_daily_close_migration() -> None:
    """Apply fields used by daily-close validation to the active database."""
    engine = database.engine
    inspector = inspect(engine)

    with engine.begin() as conn:
        if "system_config" not in inspector.get_table_names():
            if _dialect_name() == "sqlite":
                create_system_config = """
                    CREATE TABLE IF NOT EXISTS system_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key VARCHAR(100) UNIQUE NOT NULL,
                        value TEXT,
                        description VARCHAR(255),
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_by VARCHAR(100)
                    )
                """
            else:
                create_system_config = """
                    CREATE TABLE IF NOT EXISTS system_config (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(100) UNIQUE NOT NULL,
                        value TEXT,
                        description VARCHAR(255),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_by VARCHAR(100)
                    )
                """

            conn.execute(text(create_system_config))
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "idx_system_config_key ON system_config (key)"
                )
            )
            logger.info("Auto-migration: tabla system_config creada")

    _add_column_if_missing(
        "orders",
        "validada_at",
        _column_type("TIMESTAMP WITH TIME ZONE", "DATETIME"),
    )
    _add_column_if_missing("orders", "validated_by", "VARCHAR(100)")


def _apply_transfer_receiving_fields_migration() -> None:
    _add_column_if_missing("stock_transfers", "received_quantity", "INTEGER")
    _add_column_if_missing("stock_transfers", "missing_quantity", "INTEGER")
    _add_column_if_missing("stock_transfers", "incident_notes", "TEXT")


def _apply_order_completion_timestamp_migration() -> None:
    """Track the real sale-finalization time without losing order creation time."""
    _add_column_if_missing(
        "orders",
        "completed_at",
        _column_type("TIMESTAMP WITH TIME ZONE", "DATETIME"),
    )
    with database.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE orders "
                "SET completed_at = COALESCE(validada_at, created_at) "
                "WHERE completed_at IS NULL AND estado IN ('completada', 'validada')"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_order_completed_at "
                "ON orders (completed_at)"
            )
        )


MIGRATIONS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("20260805_01_daily_close_validation", _apply_daily_close_migration),
    ("20260805_02_transfer_receiving_fields", _apply_transfer_receiving_fields_migration),
    ("20260820_01_order_completion_timestamp", _apply_order_completion_timestamp_migration),
)


def _ensure_migration_table() -> None:
    applied_at_type = _column_type(
        "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()",
        "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
    )
    with database.engine.begin() as conn:
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                    id VARCHAR(100) PRIMARY KEY,
                    applied_at {applied_at_type}
                )
                """
            )
        )


def _get_applied_migrations() -> set[str]:
    if MIGRATION_TABLE not in inspect(database.engine).get_table_names():
        return set()

    with database.engine.connect() as conn:
        rows = conn.execute(text(f"SELECT id FROM {MIGRATION_TABLE}"))
        return {str(row[0]) for row in rows}


def _mark_migration_applied(migration_id: str) -> None:
    if _dialect_name() == "sqlite":
        statement = f"INSERT OR IGNORE INTO {MIGRATION_TABLE} (id) VALUES (:migration_id)"
    else:
        statement = (
            f"INSERT INTO {MIGRATION_TABLE} (id) VALUES (:migration_id) "
            "ON CONFLICT (id) DO NOTHING"
        )

    with database.engine.begin() as conn:
        conn.execute(text(statement), {"migration_id": migration_id})


def _sqlite_database_path() -> Path | None:
    if _dialect_name() != "sqlite":
        return None

    database_name = database.engine.url.database
    if not database_name or database_name == ":memory:":
        return None

    return Path(database_name).expanduser().resolve()


def _backup_sqlite_before_migration() -> Path | None:
    source = _sqlite_database_path()
    if source is None or not source.exists():
        return None

    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"{source.stem}.pre-migration-{timestamp}{source.suffix or '.db'}"

    with sqlite3.connect(str(source)) as source_conn, sqlite3.connect(str(destination)) as dest_conn:
        source_conn.backup(dest_conn)

    logger.info("Backup SQLite previo a migración creado en %s", destination)
    return destination


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
        "orders": {"validada_at", "validated_by", "completed_at"},
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
    dialect = engine.dialect.name
    if dialect not in SUPPORTED_DIALECTS:
        logger.info(
            "Migraciones versionadas omitidas para dialecto no soportado %s",
            dialect,
        )
        return True

    logger.info("Ejecutando migraciones versionadas de compatibilidad para %s...", dialect)
    try:
        applied = _get_applied_migrations()
        pending = [item for item in MIGRATIONS if item[0] not in applied]

        if pending and dialect == "sqlite":
            _backup_sqlite_before_migration()

        _ensure_migration_table()

        for migration_id, migration in pending:
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
