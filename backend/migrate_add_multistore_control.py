#!/usr/bin/env python3
"""Migración: agrega control operativo multitienda.

Crea tablas de acceso por ubicación, auditoría, recepciones, conteos físicos y
cierres por tienda. También agrega columnas de conciliación por método de pago
a instalaciones que ya tenían location_daily_closes.

Ejecutar: python3 migrate_add_multistore_control.py
"""

import os
import sys

from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine
from app.models.control import (  # noqa: E402
    AuditLog,
    LocationDailyClose,
    PhysicalInventoryCount,
    PhysicalInventoryCountItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    UserLocationAccess,
)


CONTROL_TABLES = [
    UserLocationAccess.__table__,
    AuditLog.__table__,
    PurchaseReceipt.__table__,
    PurchaseReceiptItem.__table__,
    PhysicalInventoryCount.__table__,
    PhysicalInventoryCountItem.__table__,
    LocationDailyClose.__table__,
]


def _numeric_type() -> str:
    return "NUMERIC(12, 2)"


def _add_column_if_missing(table_name: str, column_name: str, ddl_type: str, default: str = "0", nullable: bool = False) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        print(f"  ℹ️  Columna {table_name}.{column_name} ya existe.")
        return

    with engine.connect() as conn:
        null_sql = "" if nullable else " NOT NULL"
        default_sql = f" DEFAULT {default}" if default is not None else ""
        conn.execute(text(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}{null_sql}{default_sql}"
        ))
        conn.commit()
    print(f"  ✅ Columna {table_name}.{column_name} agregada.")


def _ensure_close_day_column() -> None:
    inspector = inspect(engine)
    if "location_daily_closes" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("location_daily_closes")}
    with engine.connect() as conn:
        if "close_day" not in existing_columns:
            conn.execute(text("ALTER TABLE location_daily_closes ADD COLUMN close_day DATE"))
            print("  ✅ Columna location_daily_closes.close_day agregada.")

        conn.execute(text("UPDATE location_daily_closes SET close_day = CAST(close_date AS DATE) WHERE close_day IS NULL"))
        conn.commit()


def _create_daily_close_unique_index() -> None:
    inspector = inspect(engine)
    if "location_daily_closes" not in inspector.get_table_names():
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes("location_daily_closes")}
    index_name = "uq_location_daily_close_location_day"
    if index_name in existing_indexes:
        print(f"  ℹ️  Índice {index_name} ya existe.")
        return

    sql = f"CREATE UNIQUE INDEX {index_name} ON location_daily_closes (location_id, close_day)"
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print(f"  ✅ Índice {index_name} creado.")


def run() -> None:
    inspector = inspect(engine)
    before_tables = set(inspector.get_table_names())

    for table in CONTROL_TABLES:
        if table.name in before_tables:
            print(f"  ℹ️  Tabla {table.name} ya existe.")
        else:
            print(f"  ✅ Creando tabla {table.name}...")

    CONTROL_TABLES[0].metadata.create_all(bind=engine, tables=CONTROL_TABLES)

    for column_name in ("transfer_expected", "card_expected", "financing_expected"):
        _add_column_if_missing("location_daily_closes", column_name, _numeric_type())

    _add_column_if_missing("physical_inventory_count_items", "imeis_json", "TEXT", None, nullable=True)

    _ensure_close_day_column()
    _create_daily_close_unique_index()

    print("\n✅ Migración de control multitienda completada exitosamente.")


if __name__ == "__main__":
    run()