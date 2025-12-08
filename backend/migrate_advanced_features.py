#!/usr/bin/env python3
"""
Migración para agregar funcionalidades avanzadas:
- Campo 'notes' y 'delivery_date' en Order
- Campo 'garantia_condiciones' en Product  
- Tabla StockHistory para tracking completo de cambios
"""

import sys
from sqlalchemy import create_engine, inspect, text
from app.config import settings

def run_migration():
    """Ejecuta la migración de base de datos"""
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    
    print("🔄 Iniciando migración de funcionalidades avanzadas...")
    
    with engine.connect() as conn:
        # 1. Agregar columnas a la tabla orders
        print("\n📝 Verificando tabla 'orders'...")
        order_columns = [col['name'] for col in inspector.get_columns('orders')]
        
        if 'notes' not in order_columns:
            print("  ➕ Agregando columna 'notes' a orders...")
            conn.execute(text("""
                ALTER TABLE orders 
                ADD COLUMN notes TEXT
            """))
            print("  ✅ Columna 'notes' agregada")
        else:
            print("  ⏭️  Columna 'notes' ya existe")
        
        if 'delivery_date' not in order_columns:
            print("  ➕ Agregando columna 'delivery_date' a orders...")
            conn.execute(text("""
                ALTER TABLE orders 
                ADD COLUMN delivery_date TIMESTAMP WITH TIME ZONE
            """))
            print("  ✅ Columna 'delivery_date' agregada")
            
            # Crear índice para delivery_date
            print("  ➕ Creando índice idx_order_delivery_date...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_order_delivery_date 
                ON orders(delivery_date)
            """))
            print("  ✅ Índice idx_order_delivery_date creado")
        else:
            print("  ⏭️  Columna 'delivery_date' ya existe")
        
        # 2. Agregar columna a la tabla products
        print("\n📦 Verificando tabla 'products'...")
        product_columns = [col['name'] for col in inspector.get_columns('products')]
        
        if 'garantia_condiciones' not in product_columns:
            print("  ➕ Agregando columna 'garantia_condiciones' a products...")
            conn.execute(text("""
                ALTER TABLE products 
                ADD COLUMN garantia_condiciones TEXT
            """))
            print("  ✅ Columna 'garantia_condiciones' agregada")
        else:
            print("  ⏭️  Columna 'garantia_condiciones' ya existe")
        
        # 3. Crear tabla stock_history si no existe
        print("\n📊 Verificando tabla 'stock_history'...")
        tables = inspector.get_table_names()
        
        if 'stock_history' not in tables:
            print("  ➕ Creando tabla 'stock_history'...")
            conn.execute(text("""
                CREATE TABLE stock_history (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    tipo_cambio VARCHAR(50) NOT NULL,
                    cantidad INTEGER NOT NULL,
                    stock_anterior INTEGER NOT NULL,
                    stock_nuevo INTEGER NOT NULL,
                    referencia_id INTEGER,
                    referencia_tipo VARCHAR(50),
                    notas TEXT,
                    usuario VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))
            print("  ✅ Tabla 'stock_history' creada")
            
            # Crear índices para stock_history
            print("  ➕ Creando índices para stock_history...")
            conn.execute(text("""
                CREATE INDEX idx_stock_history_product_id 
                ON stock_history(product_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_stock_history_product_date 
                ON stock_history(product_id, created_at)
            """))
            conn.execute(text("""
                CREATE INDEX idx_stock_history_tipo 
                ON stock_history(tipo_cambio)
            """))
            conn.execute(text("""
                CREATE INDEX idx_stock_history_created 
                ON stock_history(created_at)
            """))
            conn.execute(text("""
                CREATE INDEX idx_stock_history_referencia 
                ON stock_history(referencia_tipo, referencia_id)
            """))
            print("  ✅ Índices de stock_history creados")
        else:
            print("  ⏭️  Tabla 'stock_history' ya existe")
        
        conn.commit()
        print("\n✅ Migración completada exitosamente!")
        print("\n📋 Resumen de cambios:")
        print("   - Órdenes: ahora soportan notas y fecha de entrega")
        print("   - Productos: ahora pueden tener condiciones de garantía detalladas")
        print("   - Stock History: tracking completo de todos los movimientos de inventario")
        return 0

if __name__ == "__main__":
    try:
        sys.exit(run_migration())
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
