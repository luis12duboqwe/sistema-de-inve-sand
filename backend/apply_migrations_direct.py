import sys
import os

# Agregar el directorio actual al path para poder importar app
sys.path.append(os.getcwd())

from app.database import init_db
from app import models  # Importar modelos para registrarlos en Base.metadata

print("Iniciando creación de tablas faltantes...")
try:
    init_db()
    print("✅ Tablas creadas exitosamente.")
except Exception as e:
    print(f"❌ Error al crear tablas: {e}")
