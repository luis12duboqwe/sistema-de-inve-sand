#!/usr/bin/env python3
"""
Migración: Agregar campo cantidad_reservada a la tabla stock
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
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(stock)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'cantidad_reservada' in columns:
            print("✅ La columna cantidad_reservada ya existe. No se requiere migración.")
            conn.close()
            return True
        
        print("🔄 Agregando columna cantidad_reservada...")
        
        # Agregar la columna con valor por defecto 0
        cursor.execute("""
            ALTER TABLE stock 
            ADD COLUMN cantidad_reservada INTEGER NOT NULL DEFAULT 0
        """)
        
        conn.commit()
        
        # Verificar que se agregó correctamente
        cursor.execute("PRAGMA table_info(stock)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'cantidad_reservada' not in columns:
            print("❌ Error: La columna no se agregó correctamente")
            conn.close()
            return False
        
        print("✅ Columna cantidad_reservada agregada exitosamente")
        
        # Mostrar estadísticas
        cursor.execute("SELECT COUNT(*) FROM stock")
        count = cursor.fetchone()[0]
        print(f"📊 {count} registros de stock actualizados con cantidad_reservada = 0")
        
        # Advertencia sobre transferencias pendientes
        cursor.execute("SELECT COUNT(*) FROM stock_transfers WHERE estado = 'pendiente'")
        pending = cursor.fetchone()[0]
        
        if pending > 0:
            print(f"\n⚠️  ADVERTENCIA: Hay {pending} transferencias pendientes.")
            print("   Estas transferencias NO tienen stock reservado actualmente.")
            print("   Considera rechazar o confirmar estas transferencias manualmente.")
        
        conn.close()
        print("\n✅ Migración completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
