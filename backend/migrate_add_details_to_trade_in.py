import sqlite3
import os
from app.config import settings

# Obtener la ruta de la base de datos desde la configuración
# settings.database_url es algo como "sqlite:///./inventory.db"
db_path = settings.database_url.replace("sqlite:///", "")

# Ajustar ruta si es relativa
if db_path.startswith("./"):
    # Asumimos que el script se ejecuta desde el directorio backend/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, db_path[2:])

print(f"🔌 Conectando a la base de datos: {db_path}")

if not os.path.exists(db_path):
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("🔍 Verificando columnas en tabla 'trade_ins'...")
    
    # Obtener información de las columnas
    cursor.execute("PRAGMA table_info(trade_ins)")
    columns = [info[1] for info in cursor.fetchall()]
    
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
