#!/usr/bin/env python3
"""Migracion: agrega campos de recepcion parcial a transferencias.

Ejecutar: python3 migrate_add_transfer_receiving_fields.py
"""

import os
import sys

from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine  # noqa: E402


def _add_column_if_missing(table_name: str, column_name: str, ddl_type: str) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        print(f"  ⚠️  Tabla {table_name} no existe; se omite {column_name}.")
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        print(f"  ℹ️  Columna {table_name}.{column_name} ya existe.")
        return

    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}"))
        conn.commit()
    print(f"  ✅ Columna {table_name}.{column_name} agregada.")


def run() -> None:
    _add_column_if_missing("stock_transfers", "received_quantity", "INTEGER")
    _add_column_if_missing("stock_transfers", "missing_quantity", "INTEGER")
    _add_column_if_missing("stock_transfers", "incident_notes", "TEXT")
    print("\n✅ Migracion de recepcion parcial de transferencias completada.")


if __name__ == "__main__":
    run()
