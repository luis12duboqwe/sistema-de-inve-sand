import sqlite3

def migrate():
    print("Migrando base de datos: Agregando admin_notification_phone a ai_profile_configs...")
    # Fix: Use relative path assuming script runs from backend/ dir
    db_path = 'inventory.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE ai_profile_configs ADD COLUMN admin_notification_phone VARCHAR")
        print("✅ Columna agregada exitosamente.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ La columna ya existe, omitiendo.")
        else:
            print(f"❌ Error: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
