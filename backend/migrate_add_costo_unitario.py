#!/usr/bin/env python3
"""
Migración: Agregar costo_unitario a order_items para histórico de costos

Problema: El costo del producto no se copia a la orden cuando se vende.
Los reportes de márgenes usan el costo actual, no el costo al momento de venta.

Solución: 
1. Agregar columna costo_unitario a order_items
2. Llenar con costo actual del producto (es retroactivo, pero mejor que nada)
3. Actualizar código para copiar costo_unitario al crear órdenes
"""

from sqlalchemy import text, inspect
from app.database import engine, SessionLocal

def apply_migration():
    """Agrega la columna costo_unitario a order_items si no existe."""
    print("🔄 Ejecutando migración en PostgreSQL...")
    _migrate_postgres()
    
    print("✅ Migración completada")

def _migrate_postgres():
    """Migración para PostgreSQL."""
    db = SessionLocal()
    
    try:
        # Verificar si la columna existe
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('order_items')}
        
        if "costo_unitario" not in columns:
            print("  ➕ Agregando columna costo_unitario a order_items...")
            db.execute(text("""
                ALTER TABLE order_items
                ADD COLUMN costo_unitario NUMERIC(10, 2) DEFAULT 0
            """))
            print("  ✓ Columna agregada")
            
            # Llenar con costo actual del producto
            print("  ➕ Llenando costo_unitario con costo actual del producto...")
            result = db.execute(text("""
                UPDATE order_items
                SET costo_unitario = products.costo
                FROM products
                WHERE products.id = order_items.product_id
                AND (order_items.costo_unitario IS NULL OR order_items.costo_unitario = 0)
            """))
            updated_rows = int(getattr(result, "rowcount", 0) or 0)
            print(f"  ✓ {updated_rows} registros actualizados")
        else:
            print("  ✓ Columna costo_unitario ya existe")
        
        db.commit()
        print("  ✓ Cambios guardados")
        
    except Exception as e:
        print(f"  ❌ Error ejecutando migración: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("MIGRACIÓN: Agregar costo_unitario a order_items")
    print("=" * 70)
    apply_migration()
    print("\n✅ Migración exitosa\n")
