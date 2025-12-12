from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from app.config import settings
import sys

# Setup database connection
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def migrate():
    print("🔄 Iniciando migración: Agregar tabla imei_history...")
    
    with engine.connect() as connection:
        # Verificar si la tabla ya existe
        result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='imei_history'"))
        if result.fetchone():
            print("✅ La tabla 'imei_history' ya existe.")
            return

        print("🛠️ Creando tabla 'imei_history'...")
        connection.execute(text("""
            CREATE TABLE imei_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imei VARCHAR NOT NULL,
                product_id INTEGER NOT NULL,
                location_id INTEGER,
                event_type VARCHAR NOT NULL,
                reference_id INTEGER,
                reference_type VARCHAR,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR,
                FOREIGN KEY(product_id) REFERENCES products(id),
                FOREIGN KEY(location_id) REFERENCES locations(id)
            )
        """))
        
        # Crear índices
        print("📊 Creando índices...")
        connection.execute(text("CREATE INDEX idx_imei_history_imei ON imei_history (imei)"))
        connection.execute(text("CREATE INDEX idx_imei_history_product ON imei_history (product_id)"))
        connection.execute(text("CREATE INDEX idx_imei_history_date ON imei_history (created_at)"))
        
        print("✅ Migración completada exitosamente.")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        sys.exit(1)
