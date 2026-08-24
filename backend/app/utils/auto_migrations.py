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
from app.utils.bank_names import bank_name_hash, bank_name_key


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
    """Track sale finalization time while preserving the oldest supported schemas.

    Some legacy databases predate ``created_at`` and ``validada_at``. We only
    backfill from timestamps that actually exist; when none exist, leaving
    ``completed_at`` NULL is safer than inventing a historical sale date.
    """
    _add_column_if_missing(
        "orders",
        "completed_at",
        _column_type("TIMESTAMP WITH TIME ZONE", "DATETIME"),
    )

    order_columns = {
        item["name"] for item in inspect(database.engine).get_columns("orders")
    }
    backfill_expression: str | None = None
    if "validada_at" in order_columns and "created_at" in order_columns:
        backfill_expression = "COALESCE(validada_at, created_at)"
    elif "validada_at" in order_columns:
        backfill_expression = "validada_at"
    elif "created_at" in order_columns:
        backfill_expression = "created_at"

    with database.engine.begin() as conn:
        if backfill_expression:
            conn.execute(
                text(
                    "UPDATE orders "
                    f"SET completed_at = {backfill_expression} "
                    "WHERE completed_at IS NULL AND estado IN ('completada', 'validada')"
                )
            )
        else:
            logger.warning(
                "Auto-migration: orders no tiene timestamps históricos para "
                "backfill de completed_at; se conservan valores NULL"
            )

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_order_completed_at "
                "ON orders (completed_at)"
            )
        )


def _apply_processed_message_delivery_state_migration() -> None:
    """Add durable reply-delivery state to existing webhook deduplication tables."""
    if "processed_messages" not in inspect(database.engine).get_table_names():
        # Very old SQLite fixtures/installations can predate the table entirely.
        # Normal application startup creates missing model tables before these
        # compatibility ALTERs run, so there is nothing safe to alter here.
        return

    _add_column_if_missing("processed_messages", "delivery_status", "VARCHAR(32)")
    _add_column_if_missing("processed_messages", "reply_text", "TEXT")
    with database.engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_processed_message_delivery_status "
                "ON processed_messages (delivery_status)"
            )
        )


def _apply_bank_name_normalization_migration() -> None:
    """Backfill canonical bank identities without guessing how to merge duplicates."""
    if "banks" not in inspect(database.engine).get_table_names():
        return

    _add_column_if_missing("banks", "name_normalized", "TEXT")
    _add_column_if_missing("banks", "name_key_hash", "VARCHAR(64)")

    # A pre-release version briefly indexed the full normalized text. Drop that
    # index before any potentially multi-KB Unicode expansion is backfilled.
    with database.engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_banks_name_normalized"))
        if _dialect_name() == "postgresql":
            conn.execute(
                text("ALTER TABLE banks ALTER COLUMN name_normalized TYPE TEXT")
            )

    seen_keys: dict[str, tuple[int, str]] = {}
    seen_hashes: dict[str, tuple[str, int, str]] = {}
    with database.engine.begin() as conn:
        rows = conn.execute(text("SELECT id, name FROM banks ORDER BY id")).mappings().all()
        normalized_rows: list[tuple[int, str, str]] = []
        for row in rows:
            bank_id = int(row["id"])
            raw_name = str(row["name"] or "")
            try:
                normalized_key = bank_name_key(raw_name)
                normalized_hash = bank_name_hash(raw_name)
            except ValueError as exc:
                raise RuntimeError(
                    f"Banco existente ID {bank_id} tiene un nombre inválido; "
                    "corrígelo antes de continuar la migración"
                ) from exc

            previous = seen_keys.get(normalized_key)
            if previous is not None:
                previous_id, previous_name = previous
                raise RuntimeError(
                    "Bancos duplicados después de normalizar: "
                    f"ID {previous_id} '{previous_name}' e ID {bank_id} '{raw_name}'. "
                    "Unifica esos registros antes de continuar la migración."
                )

            hash_previous = seen_hashes.get(normalized_hash)
            if hash_previous is not None and hash_previous[0] != normalized_key:
                _, previous_id, previous_name = hash_previous
                raise RuntimeError(
                    "Colisión de identidad bancaria detectada: "
                    f"ID {previous_id} '{previous_name}' e ID {bank_id} '{raw_name}'. "
                    "No se puede continuar de forma segura."
                )

            seen_keys[normalized_key] = (bank_id, raw_name)
            seen_hashes[normalized_hash] = (normalized_key, bank_id, raw_name)
            normalized_rows.append((bank_id, normalized_key, normalized_hash))

        for bank_id, normalized_key, normalized_hash in normalized_rows:
            conn.execute(
                text(
                    "UPDATE banks SET name_normalized = :normalized_key, "
                    "name_key_hash = :normalized_hash WHERE id = :bank_id"
                ),
                {
                    "normalized_key": normalized_key,
                    "normalized_hash": normalized_hash,
                    "bank_id": bank_id,
                },
            )

        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_banks_name_key_hash "
                "ON banks (name_key_hash)"
            )
        )

        if _dialect_name() == "postgresql":
            conn.execute(
                text("ALTER TABLE banks ALTER COLUMN name_normalized SET NOT NULL")
            )
            conn.execute(
                text("ALTER TABLE banks ALTER COLUMN name_key_hash SET NOT NULL")
            )


MIGRATIONS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("20260805_01_daily_close_validation", _apply_daily_close_migration),
    ("20260805_02_transfer_receiving_fields", _apply_transfer_receiving_fields_migration),
    ("20260820_01_order_completion_timestamp", _apply_order_completion_timestamp_migration),
    ("20260824_01_processed_message_delivery_state", _apply_processed_message_delivery_state_migration),
    ("20260824_02_bank_name_normalized_uniqueness", _apply_bank_name_normalization_migration),
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
    if "processed_messages" in table_names:
        required_columns["processed_messages"] = {"delivery_status", "reply_text"}
    if "banks" in table_names:
        required_columns["banks"] = {"name_normalized", "name_key_hash"}

    missing_columns: list[str] = []
    for table, required in required_columns.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for column in sorted(required - existing):
            missing_columns.append(f"{table}.{column}")

    if missing_columns:
        raise RuntimeError(
            "Esquema incompleto: faltan columnas críticas: " + ", ".join(missing_columns)
        )

    if "banks" in table_names:
        with database.engine.connect() as conn:
            null_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM banks WHERE name_normalized IS NULL "
                    "OR name_key_hash IS NULL"
                )
            ).scalar_one()
        if int(null_count) != 0:
            raise RuntimeError("Esquema incompleto: existen bancos sin identidad normalizada")

        bank_indexes = inspect(database.engine).get_indexes("banks")
        has_unique_hash_index = any(
            index.get("unique")
            and index.get("name") == "ix_banks_name_key_hash"
            for index in bank_indexes
        )
        if not has_unique_hash_index:
            raise RuntimeError(
                "Esquema incompleto: falta índice único ix_banks_name_key_hash"
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
