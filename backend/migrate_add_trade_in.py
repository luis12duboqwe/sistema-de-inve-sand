#!/usr/bin/env python3
"""
Migración: Agregar tabla trade_ins
Ejecutar este script para actualizar la base de datos existente sin perder datos.
"""

import sqlite3
import sys
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / "inventory.db"
    
    if not db_path.exists():
        print(f"❌ Base de datos no encontrada en {db_path}")
        print("ℹ️  Ejecuta init_db.py para crear una nueva base de datos.")
        return False
    
    print(f"📦 Migrando base de datos: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la tabla ya existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trade_ins'")
        if cursor.fetchone():
            print("✅ La tabla trade_ins ya existe. No se requiere migración.")
            conn.close()
            return True
        
        print("🔄 Creando tabla trade_ins...")
        
        # Crear la tabla trade_ins
        cursor.execute("""
            CREATE TABLE trade_ins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                marca VARCHAR NOT NULL,
                modelo VARCHAR NOT NULL,
                imei VARCHAR,
                condicion VARCHAR NOT NULL,
                valor_estimado NUMERIC(10, 2) NOT NULL,
                notas VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        """)
        
        # Crear índice para order_id
        cursor.execute("CREATE INDEX idx_trade_ins_order_id ON trade_ins (order_id)")
        
        conn.commit()
        print("✅ Tabla trade_ins creada exitosamente.")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False

if __name__ == "__main__":
    if migrate():
        sys.exit(0)
    else:
        sys.exit(1)
