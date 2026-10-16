"""Read-only, explicit opt-in diagnostics for an OFFLINE legacy SQLite copy.

These utilities do not diagnose the running PostgreSQL production service.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sqlite3


def open_legacy_snapshot(description: str) -> sqlite3.Connection:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--legacy-sqlite", required=True, type=Path,
        help="Explicit pathname of an OFFLINE, disposable legacy SQLite snapshot",
    )
    parser.add_argument(
        "--acknowledge-legacy", action="store_true",
        help="Confirm this is an offline SQLite diagnostic, NOT a PostgreSQL health check",
    )
    args = parser.parse_args()
    if not args.acknowledge_legacy:
        parser.error("--acknowledge-legacy is required; never infer a production database")
    if os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod"):
        parser.error("This legacy SQLite diagnostic is disabled in production")
    try:
        snapshot = args.legacy_sqlite.expanduser().resolve(strict=True)
    except OSError as exc:
        parser.error(f"Snapshot does not exist: {exc}")
    if not snapshot.is_file():
        parser.error("Snapshot must be an existing regular file")
    try:
        conn = sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = ON")
        return conn
    except sqlite3.Error as exc:
        parser.error(f"Cannot open SQLite snapshot read-only: {exc}")
