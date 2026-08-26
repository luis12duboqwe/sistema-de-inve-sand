"""Cross-process serialization for schema initialization and compatibility migrations."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
from threading import Lock
from typing import Iterator

from sqlalchemy import text

import app.database as database


# One stable signed BIGINT key dedicated to inventory schema startup work.
POSTGRES_SCHEMA_LOCK_KEY = 0x534F4654494E5645
_IN_MEMORY_SQLITE_LOCK = Lock()


@contextmanager
def _postgres_schema_lock() -> Iterator[None]:
    """Hold a PostgreSQL session advisory lock across all startup schema work."""
    with database.engine.connect() as conn:
        conn.execute(
            text("SELECT pg_advisory_lock(:lock_key)"),
            {"lock_key": POSTGRES_SCHEMA_LOCK_KEY},
        )
        try:
            yield
        finally:
            conn.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": POSTGRES_SCHEMA_LOCK_KEY},
            )


def _sqlite_lock_path() -> Path | None:
    database_name = database.engine.url.database
    if not database_name or database_name == ":memory:":
        return None

    db_path = Path(database_name).expanduser().resolve()
    return db_path.with_name(f".{db_path.name}.schema-startup.lock")


@contextmanager
def _sqlite_file_schema_lock() -> Iterator[None]:
    """Use a real OS file lock; the lock is released automatically on process exit."""
    lock_path = _sqlite_lock_path()
    if lock_path is None:
        with _IN_MEMORY_SQLITE_LOCK:
            yield
        return

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        # Windows byte-range locking needs at least one byte in the file.
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"0")
            lock_file.flush()
        lock_file.seek(0)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def startup_schema_lock() -> Iterator[None]:
    """Serialize ``init_db`` + migrations for every supported production engine."""
    dialect = database.engine.dialect.name
    if dialect == "postgresql":
        with _postgres_schema_lock():
            yield
        return
    if dialect == "sqlite":
        with _sqlite_file_schema_lock():
            yield
        return

    # Unsupported/test-only engines keep the existing behavior.
    yield


__all__ = ["POSTGRES_SCHEMA_LOCK_KEY", "startup_schema_lock"]
