from sqlalchemy import create_engine, inspect, text
from app.config import settings
import sys

# Setup database connection
engine = create_engine(settings.database_url)

def migrate():
    print("🔄 Iniciando migración: Agregar tabla imei_history...")
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        if "imei_history" in existing_tables:
            print("✅ La tabla 'imei_history' ya existe.")
            return

        print("🛠️ Creando tabla 'imei_history'...")
        connection.execute(text("""
            CREATE TABLE imei_history (
                id SERIAL PRIMARY KEY,
                imei VARCHAR NOT NULL,
                product_id INTEGER NOT NULL,
                location_id INTEGER,
                event_type VARCHAR NOT NULL,
                reference_id INTEGER,
                reference_type VARCHAR,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        connection.commit()
        
        print("✅ Migración completada exitosamente.")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        sys.exit(1)
