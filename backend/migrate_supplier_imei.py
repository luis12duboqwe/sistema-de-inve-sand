"""
Script de migración para agregar Supplier y actualizar Product.

Este script agrega:
- Tabla suppliers
- Campos supplier_id e imei a products

Uso:
    python migrate_supplier_imei.py
"""

import sys
from app.database import engine
from app.models import Base, Supplier, Product
from sqlalchemy import inspect, text


def migrate():
    """Aplica las migraciones necesarias."""
    print("Aplicando migraciones para Supplier e IMEI...")
    
    inspector = inspect(engine)
    
    try:
        # 1. Crear tabla suppliers si no existe
        if 'suppliers' not in inspector.get_table_names():
            print("  - Creando tabla suppliers...")
            Supplier.__table__.create(bind=engine, checkfirst=True)
            print("  ✓ Tabla suppliers creada")
        else:
            print("  ✓ Tabla suppliers ya existe")
        
        # 2. Agregar columna supplier_id a products si no existe
        columns = [col['name'] for col in inspector.get_columns('products')]
        
        if 'supplier_id' not in columns:
            print("  - Agregando columna supplier_id a products...")
            with engine.connect() as conn:
                conn.execute(text(
                    'ALTER TABLE products ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL'
                ))
                conn.execute(text(
                    'CREATE INDEX IF NOT EXISTS idx_product_supplier ON products(supplier_id)'
                ))
                conn.commit()
            print("  ✓ Columna supplier_id agregada")
        else:
            print("  ✓ Columna supplier_id ya existe")
        
        # 3. Agregar columna imei a products si no existe
        if 'imei' not in columns:
            print("  - Agregando columna imei a products...")
            with engine.connect() as conn:
                conn.execute(text(
                    'ALTER TABLE products ADD COLUMN imei VARCHAR UNIQUE'
                ))
                conn.execute(text(
                    'CREATE INDEX IF NOT EXISTS idx_product_imei ON products(imei)'
                ))
                conn.commit()
            print("  ✓ Columna imei agregada")
        else:
            print("  ✓ Columna imei ya existe")
        
        return True
    except Exception as e:
        print(f"  ✗ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate()
    if success:
        print("\n✓ Migraciones completadas con éxito")
        print("\nNuevas características disponibles:")
        print("  - Gestión de proveedores (suppliers)")
        print("  - Asignación de proveedor a productos")
        print("  - Registro de IMEI para celulares")
        print("\nEndpoints disponibles:")
        print("  POST   /api/suppliers         - Crear proveedor")
        print("  GET    /api/suppliers         - Listar proveedores")
        print("  GET    /api/suppliers/{id}    - Obtener proveedor")
        print("  PUT    /api/suppliers/{id}    - Actualizar proveedor")
        print("  DELETE /api/suppliers/{id}    - Eliminar proveedor")
    else:
        print("\n✗ Migraciones fallidas. Verifica los errores arriba.")
        sys.exit(1)
