#!/usr/bin/env python3
"""Fix: Agregar columna supplier_id faltante"""

from sqlalchemy import create_engine, text, inspect
from app.config import settings

def fix_supplier_column():
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    
    print("🔄 Verificando columna supplier_id...")
    
    product_columns = [col['name'] for col in inspector.get_columns('products')]
    
    if 'supplier_id' not in product_columns:
        print("  ➕ Agregando columna 'supplier_id' a products...")
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE products 
                ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)
            """))
            conn.commit()
        print("  ✅ Columna 'supplier_id' agregada exitosamente")
    else:
        print("  ✅ Columna 'supplier_id' ya existe")
    
    print("\n✅ Listo! Reinicia el backend")

if __name__ == "__main__":
    fix_supplier_column()
