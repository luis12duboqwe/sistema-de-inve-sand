"""
Script de migración para agregar confirmación de transferencias.

Este script agrega campos de confirmación a la tabla stock_transfers:
- estado (pendiente, confirmada, rechazada, cancelada)
- confirmed_at
- confirmed_by
- rejection_reason

Uso:
    python migrate_transfer_confirmation.py
"""

import sys
from app.database import engine
from sqlalchemy import inspect, text


def migrate():
    """Aplica las migraciones necesarias para confirmación de transferencias."""
    print("Aplicando migración: Confirmación de transferencias...")
    
    inspector = inspect(engine)
    
    try:
        # Verificar si la tabla existe
        if 'stock_transfers' not in inspector.get_table_names():
            print("  ✗ La tabla stock_transfers no existe. Ejecuta migrate_stock_transfers.py primero.")
            return False
        
        columns = [col['name'] for col in inspector.get_columns('stock_transfers')]
        
        # 1. Agregar columna estado
        if 'estado' not in columns:
            print("  - Agregando columna estado...")
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE stock_transfers ADD COLUMN estado VARCHAR(20) DEFAULT 'pendiente' NOT NULL"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_transfer_estado ON stock_transfers(estado)"
                ))
                conn.commit()
            print("  ✓ Columna estado agregada")
        else:
            print("  ✓ Columna estado ya existe")
        
        # 2. Agregar columna confirmed_at
        if 'confirmed_at' not in columns:
            print("  - Agregando columna confirmed_at...")
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE stock_transfers ADD COLUMN confirmed_at TIMESTAMP"
                ))
                conn.commit()
            print("  ✓ Columna confirmed_at agregada")
        else:
            print("  ✓ Columna confirmed_at ya existe")
        
        # 3. Agregar columna confirmed_by
        if 'confirmed_by' not in columns:
            print("  - Agregando columna confirmed_by...")
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE stock_transfers ADD COLUMN confirmed_by VARCHAR(100)"
                ))
                conn.commit()
            print("  ✓ Columna confirmed_by agregada")
        else:
            print("  ✓ Columna confirmed_by ya existe")
        
        # 4. Agregar columna rejection_reason
        if 'rejection_reason' not in columns:
            print("  - Agregando columna rejection_reason...")
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE stock_transfers ADD COLUMN rejection_reason TEXT"
                ))
                conn.commit()
            print("  ✓ Columna rejection_reason agregada")
        else:
            print("  ✓ Columna rejection_reason ya existe")
        
        # 5. Actualizar transferencias existentes a estado confirmada
        print("  - Actualizando transferencias existentes...")
        with engine.connect() as conn:
            result = conn.execute(text(
                "UPDATE stock_transfers SET estado = 'confirmada' WHERE estado IS NULL OR estado = ''"
            ))
            conn.commit()
            print(f"  ✓ {result.rowcount} transferencias actualizadas a estado 'confirmada'")
        
        return True
    except Exception as e:
        print(f"  ✗ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate()
    if success:
        print("\n✓ Migración completada con éxito")
        print("\nNuevas características disponibles:")
        print("  - Transferencias con confirmación de dos pasos")
        print("  - Estados: pendiente, confirmada, rechazada, cancelada")
        print("  - Stock se mueve solo al confirmar la transferencia")
        print("  - Historial de confirmaciones y rechazos")
        print("\nNuevos endpoints:")
        print("  POST /api/stock-transfers/{id}/confirm  - Confirmar transferencia")
        print("  POST /api/stock-transfers/{id}/reject   - Rechazar transferencia")
        print("  DELETE /api/stock-transfers/{id}        - Cancelar transferencia pendiente")
    else:
        print("\n✗ Migración fallida. Verifica los errores arriba.")
        sys.exit(1)
