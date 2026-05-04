from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Callable, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _read_database_url_from_env_file() -> str:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return ""

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("DATABASE_URL="):
            continue
        return line.split("=", 1)[1].strip().strip('"').strip("'")

    return ""


def get_postgres_database_url() -> str:
    database_url = (os.getenv("DATABASE_URL") or _read_database_url_from_env_file()).strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL no está configurado para las pruebas.")
    if not database_url.lower().startswith("postgresql"):
        raise RuntimeError("Las pruebas ahora requieren PostgreSQL.")
    return database_url


def _sanitize_schema_prefix(prefix: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", prefix or "test")
    return cleaned.strip("_").lower() or "test"


def create_postgres_test_engine(prefix: str = "test") -> Tuple[Engine, str, Callable[[], None]]:
    database_url = get_postgres_database_url()
    schema_name = f"{_sanitize_schema_prefix(prefix)}_{uuid.uuid4().hex[:12]}"

    admin_engine = create_engine(database_url, pool_pre_ping=True)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={schema_name}"},
    )

    def cleanup() -> None:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        admin_engine.dispose()

    return engine, schema_name, cleanup
