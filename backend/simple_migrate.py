import sqlite3
import os

# Assume inventory.db is in the same directory as this script
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "inventory.db")

print(f"🔌 Conectando a la base de datos: {db_path}")

if not os.path.exists(db_path):
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    # Try looking one level up just in case
    db_path_up = os.path.join(os.path.dirname(base_dir), "backend", "inventory.db")
    if os.path.exists(db_path_up):
         db_path = db_path_up
         print(f"🔌 Encontrada en: {db_path}")
    else:
         # Try current working directory
         db_path_cwd = os.path.join(os.getcwd(), "inventory.db")
         if os.path.exists(db_path_cwd):
             db_path = db_path_cwd
             print(f"🔌 Encontrada en CWD: {db_path}")
         else:
             print("❌ No se pudo encontrar la base de datos.")
             exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("🔍 Verificando columnas en tabla 'trade_ins'...")
    
    # Obtener información de las columnas
    cursor.execute("PRAGMA table_info(trade_ins)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Columnas actuales: {columns}")
    
    # Agregar columna 'color' si no existe
    if 'color' not in columns:
        print("➕ Agregando columna 'color'...")
        cursor.execute("ALTER TABLE trade_ins ADD COLUMN color TEXT")
    else:
        print("✅ Columna 'color' ya existe.")

    # Agregar columna 'capacidad' si no existe
    if 'capacidad' not in columns:
        print("➕ Agregando columna 'capacidad'...")
        cursor.execute("ALTER TABLE trade_ins ADD COLUMN capacidad TEXT")
    else:
        print("✅ Columna 'capacidad' ya existe.")

    conn.commit()
    print("✅ Migración completada exitosamente.")

except Exception as e:
    print(f"❌ Error durante la migración: {e}")
    conn.rollback()
finally:
    conn.close()
