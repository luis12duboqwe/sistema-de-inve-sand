#!/usr/bin/env python3
"""Migrate a legacy SQLite installation into PostgreSQL without losing data.

The migration is intentionally conservative:

* the SQLite source is never modified;
* a consistent backup copy is created before reading data;
* legacy tables are reflected from SQLite so missing newer columns do not make
  the SELECT itself fail;
* only columns present in both source and current target metadata are copied;
* a non-empty PostgreSQL target is rejected unless ``--truncate`` is explicit;
* PostgreSQL sequences are repaired after inserting historical integer IDs.

Usage:
    python migrate_sqlite_to_postgres.py --sqlite inventory.db
    python migrate_sqlite_to_postgres.py --sqlite inventory.db --truncate

The PostgreSQL target is read from DATABASE_URL, normally through backend/.env.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys
from typing import Iterable

from sqlalchemy import MetaData, Table, create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migra datos de SQLite legado a PostgreSQL preservando la fuente."
    )
    parser.add_argument(
        "--sqlite",
        default=str(BACKEND_DIR / "inventory.db"),
        help="Ruta al archivo SQLite legado. Default: backend/inventory.db",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="DATABASE_URL PostgreSQL destino. Default: variable de entorno/backend/.env",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Vacía las tablas destino antes de insertar los datos migrados.",
    )
    return parser.parse_args()


def _sqlite_engine(sqlite_path: Path) -> Engine:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"No existe el archivo SQLite: {sqlite_path}")
    return create_engine(f"sqlite:///{sqlite_path}")


def _postgres_engine(database_url: str) -> Engine:
    if not database_url.lower().startswith("postgresql"):
        raise ValueError(
            "El destino debe ser PostgreSQL (DATABASE_URL debe iniciar con postgresql)."
        )
    return create_engine(database_url, pool_pre_ping=True)


def _backup_sqlite_source(sqlite_path: Path) -> Path:
    backup_dir = sqlite_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = (
        backup_dir
        / f"{sqlite_path.stem}.pre-postgres-migration-{timestamp}{sqlite_path.suffix or '.db'}"
    )

    with sqlite3.connect(str(sqlite_path)) as source, sqlite3.connect(
        str(destination)
    ) as target:
        source.backup(target)

    return destination


def _existing_source_tables(source_engine: Engine, table_names: Iterable[str]) -> set[str]:
    inspector = inspect(source_engine)
    available = set(inspector.get_table_names())
    return {name for name in table_names if name in available}


def _target_tables_with_rows(target_engine: Engine, table_names: Iterable[str]) -> list[str]:
    non_empty: list[str] = []
    metadata = MetaData()
    with target_engine.connect() as connection:
        for table_name in table_names:
            table = Table(table_name, metadata, autoload_with=target_engine)
            count = connection.execute(select(func.count()).select_from(table)).scalar_one()
            if count > 0:
                non_empty.append(table_name)
    return non_empty


def _truncate_tables(target_engine: Engine, table_names: Iterable[str]) -> None:
    ordered_names = ", ".join(f'"{name}"' for name in table_names)
    if not ordered_names:
        return
    with target_engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {ordered_names} RESTART IDENTITY CASCADE")
        )


def _required_target_columns_missing_from_source(source_table: Table, target_table: Table) -> list[str]:
    source_names = set(source_table.c.keys())
    missing: list[str] = []

    for column in target_table.columns:
        if column.name in source_names:
            continue
        if column.nullable or column.default is not None or column.server_default is not None:
            continue
        if column.primary_key and getattr(column, "autoincrement", False):
            continue
        missing.append(column.name)

    return missing


def _copy_table_rows(
    source_engine: Engine,
    target_connection,
    target_table: Table,
) -> int:
    source_metadata = MetaData()
    source_table = Table(
        target_table.name,
        source_metadata,
        autoload_with=source_engine,
    )

    required_missing = _required_target_columns_missing_from_source(
        source_table, target_table
    )
    if required_missing:
        raise RuntimeError(
            f"La tabla SQLite '{target_table.name}' es demasiado antigua: faltan "
            "columnas obligatorias para el esquema actual: "
            + ", ".join(required_missing)
            + ". Actualiza primero el SQLite con esta versión y vuelve a ejecutar la migración."
        )

    target_names = set(target_table.c.keys())
    common_columns = [
        column.name for column in source_table.columns if column.name in target_names
    ]
    if not common_columns:
        return 0

    statement = select(*(source_table.c[name] for name in common_columns))
    with source_engine.connect() as source_connection:
        rows = [dict(row._mapping) for row in source_connection.execute(statement)]

    if rows:
        target_connection.execute(target_table.insert(), rows)
    return len(rows)


def _reset_postgres_sequences(target_engine: Engine, tables: Iterable[Table]) -> None:
    """Advance SERIAL/IDENTITY sequences after historical IDs were inserted."""
    with target_engine.begin() as connection:
        for table in tables:
            pk_columns = list(table.primary_key.columns)
            if len(pk_columns) != 1:
                continue

            column = pk_columns[0]
            sequence_name = connection.execute(
                text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
                {"table_name": table.name, "column_name": column.name},
            ).scalar_one_or_none()
            if not sequence_name:
                continue

            max_value = connection.execute(
                select(func.max(column))
            ).scalar_one_or_none()
            if max_value is None:
                connection.execute(
                    text("SELECT setval(CAST(:seq AS regclass), 1, false)"),
                    {"seq": sequence_name},
                )
            else:
                connection.execute(
                    text("SELECT setval(CAST(:seq AS regclass), :value, true)"),
                    {"seq": sequence_name, "value": int(max_value)},
                )


def main() -> int:
    _load_env_file(BACKEND_DIR / ".env")
    args = _parse_args()

    database_url = (args.database_url or os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL no está configurado.", file=sys.stderr)
        return 2

    from app.database import Base
    from app import models  # noqa: F401 - registra modelos en Base.metadata

    sqlite_path = Path(args.sqlite).expanduser().resolve()
    source_engine = _sqlite_engine(sqlite_path)
    target_engine = _postgres_engine(database_url)

    sorted_tables = list(Base.metadata.sorted_tables)
    table_names = [table.name for table in sorted_tables]
    source_tables = _existing_source_tables(source_engine, table_names)

    if not source_tables:
        print(f"No se encontraron tablas compatibles en {sqlite_path}", file=sys.stderr)
        source_engine.dispose()
        target_engine.dispose()
        return 1

    try:
        backup_path = _backup_sqlite_source(sqlite_path)
        print(f"Backup SQLite creado antes de migrar: {backup_path}")

        Base.metadata.create_all(bind=target_engine)
        matching_target_tables = [name for name in table_names if name in source_tables]

        if args.truncate:
            _truncate_tables(target_engine, reversed(matching_target_tables))
        else:
            non_empty = _target_tables_with_rows(target_engine, matching_target_tables)
            if non_empty:
                print(
                    "ERROR: el PostgreSQL destino ya contiene datos en: "
                    + ", ".join(non_empty)
                    + ". Se rechaza la mezcla automática para evitar duplicados. "
                    "Usa una base vacía o --truncate sólo si confirmaste que el destino puede reemplazarse.",
                    file=sys.stderr,
                )
                return 3

        total_rows = 0
        migrated_tables: list[Table] = []
        with target_engine.begin() as target_connection:
            for table in sorted_tables:
                if table.name not in source_tables:
                    continue

                copied = _copy_table_rows(source_engine, target_connection, table)
                total_rows += copied
                migrated_tables.append(table)
                print(f"{table.name}: {copied} filas migradas")

        _reset_postgres_sequences(target_engine, migrated_tables)
        print(
            f"Migración completada: {total_rows} filas copiadas a PostgreSQL. "
            "La fuente SQLite original no fue modificada."
        )
        return 0
    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        print(f"ERROR de migración: {exc}", file=sys.stderr)
        return 1
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
