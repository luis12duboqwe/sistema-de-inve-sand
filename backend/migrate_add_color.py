import sqlite3

def migrate():
    print("Migrando base de datos: Agregando columna 'color' a tabla products...")
    # Fix: Use relative path assuming script runs from backend/ dir
    db_path = 'inventory.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN color VARCHAR")
        print("✅ Columna 'color' agregada exitosamente.")
        
        # Crear índice para búsquedas rápidas por color
        try:
            cursor.execute("CREATE INDEX idx_product_color ON products(color)")
            print("✅ Índice idx_product_color creado.")
        except Exception as e:
            print(f"⚠️ No se pudo crear índice (quizás ya existe): {e}")
            
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ La columna ya existe, omitiendo.")
        else:
            print(f"❌ Error: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
