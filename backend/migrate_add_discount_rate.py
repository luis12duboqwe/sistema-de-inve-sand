import sqlite3
import sys

def migrate():
    print("🚀 Iniciando migración de tasa de descuento para IA...")
    
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    
    try:
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(ai_profile_configs)")
        columns = [info[1] for info in cursor.fetchall()]
        
        new_columns = {
            "max_discount_rate": "REAL" # Float for percentage (e.g. 0.10 for 10%)
        }
        
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                print(f"➕ Agregando columna '{col_name}'...")
                cursor.execute(f"ALTER TABLE ai_profile_configs ADD COLUMN {col_name} {col_type}")
            else:
                print(f"ℹ️ Columna '{col_name}' ya existe.")
        
        conn.commit()
        print("✅ Migración completada exitosamente.")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
