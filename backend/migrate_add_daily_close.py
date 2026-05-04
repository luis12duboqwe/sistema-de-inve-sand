#!/usr/bin/env python3
"""Migración: Agrega campos de validación de cierre de día a orders
y crea tabla system_config.

Ejecutar: python3 migrate_add_daily_close.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine
from sqlalchemy import text, inspect


def run():
    inspector = inspect(engine)

    # ── 1. Tabla system_config ────────────────────────────────────────────────
    if "system_config" not in inspector.get_table_names():
        print("Creando tabla system_config...")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value TEXT,
                    description VARCHAR(255),
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_by VARCHAR(100)
                )
            """))
            conn.execute(text("CREATE UNIQUE INDEX idx_system_config_key ON system_config (key)"))
            conn.commit()
        print("  ✅ Tabla system_config creada.")
    else:
        print("  ℹ️  Tabla system_config ya existe.")

    # ── 2. Columnas en orders ─────────────────────────────────────────────────
    existing_cols = [c["name"] for c in inspector.get_columns("orders")]

    with engine.connect() as conn:
        added_any = False
        if "validada_at" not in existing_cols:
            conn.execute(text("ALTER TABLE orders ADD COLUMN validada_at DATETIME"))
            print("  ✅ Columna validada_at agregada a orders.")
            added_any = True

        if "validated_by" not in existing_cols:
            conn.execute(text("ALTER TABLE orders ADD COLUMN validated_by VARCHAR(100)"))
            print("  ✅ Columna validated_by agregada a orders.")
            added_any = True

        if added_any:
            conn.commit()
        else:
            print("  ℹ️  Columnas validada_at y validated_by ya existen en orders.")

    # ── 3. Índice en validada_at ──────────────────────────────────────────────
    try:
        existing_indexes = [i["name"] for i in inspector.get_indexes("orders")]
        if "idx_order_validada_at" not in existing_indexes:
            with engine.connect() as conn:
                conn.execute(text("CREATE INDEX idx_order_validada_at ON orders (validada_at)"))
                conn.commit()
            print("  ✅ Índice idx_order_validada_at creado.")
    except Exception as e:
        print(f"  ⚠️  No se pudo crear el índice (puede ya existir): {e}")

    print("\n✅ Migración completada exitosamente.")


if __name__ == "__main__":
    run()
