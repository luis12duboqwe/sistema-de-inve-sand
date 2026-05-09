#!/usr/bin/env python3
"""Migrate legacy SQLite data into the configured PostgreSQL database.

Usage:
    python migrate_sqlite_to_postgres.py --sqlite inventory.db
    python migrate_sqlite_to_postgres.py --sqlite inventory.db --truncate

The PostgreSQL target is read from DATABASE_URL, normally through backend/.env.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine, inspect, select, text
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
    parser = argparse.ArgumentParser(description="Migra datos de SQLite legado a PostgreSQL.")
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
        raise ValueError("El destino debe ser PostgreSQL (DATABASE_URL debe iniciar con postgresql).")
    return create_engine(database_url, pool_pre_ping=True)


def _existing_source_tables(source_engine: Engine, table_names: Iterable[str]) -> set[str]:
    inspector = inspect(source_engine)
    available = set(inspector.get_table_names())
    return {name for name in table_names if name in available}


def _truncate_tables(target_engine: Engine, table_names: Iterable[str]) -> None:
    ordered_names = ", ".join(f'"{name}"' for name in table_names)
    if not ordered_names:
        return
    with target_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {ordered_names} RESTART IDENTITY CASCADE"))


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
        print(f"No se encontraron tablas compatibles en {sqlite_path}")
        return 1

    try:
        Base.metadata.create_all(bind=target_engine)
        if args.truncate:
            _truncate_tables(target_engine, reversed(table_names))

        total_rows = 0
        with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
            for table in sorted_tables:
                if table.name not in source_tables:
                    continue

                rows = [dict(row._mapping) for row in source_connection.execute(select(table))]
                if not rows:
                    print(f"{table.name}: 0 filas")
                    continue

                target_connection.execute(table.insert(), rows)
                total_rows += len(rows)
                print(f"{table.name}: {len(rows)} filas migradas")

        print(f"Migración completada: {total_rows} filas copiadas a PostgreSQL.")
        return 0
    except SQLAlchemyError as exc:
        print(f"ERROR de base de datos: {exc}", file=sys.stderr)
        return 1
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
