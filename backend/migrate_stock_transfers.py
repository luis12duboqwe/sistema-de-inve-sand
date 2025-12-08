"""
Script de migración para agregar la tabla stock_transfers.

Este script agrega la tabla de transferencias de stock a la base de datos existente.

Uso:
    python migrate_stock_transfers.py
"""

import sys
from app.database import engine, SessionLocal
from app.models import Base, StockTransfer


def migrate():
    """Crea la tabla stock_transfers si no existe."""
    print("Aplicando migración: Agregar tabla stock_transfers...")
    
    try:
        # Crear solo la tabla StockTransfer
        StockTransfer.__table__.create(bind=engine, checkfirst=True)
        print("✓ Tabla stock_transfers creada exitosamente")
        return True
    except Exception as e:
        print(f"✗ Error al crear la tabla: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    if success:
        print("\n✓ Migración completada con éxito")
        print("Ahora puedes transferir stock entre perfiles usando el endpoint /api/stock-transfers")
    else:
        print("\n✗ Migración fallida. Verifica los errores arriba.")
        sys.exit(1)
