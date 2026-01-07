from sqlalchemy import create_engine, text
from app.config import settings
import sys

# Setup database connection
engine = create_engine(settings.database_url)

def migrate():
    print("🔄 Iniciando migración: Agregar tablas de devoluciones (Returns)...")
    
    with engine.connect() as connection:
        # Verificar si la tabla ya existe
        result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='returns'"))
        if result.fetchone():
            print("✅ La tabla 'returns' ya existe.")
            return

        print("🛠️ Creando tabla 'returns'...")
        connection.execute(text("""
            CREATE TABLE returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reason VARCHAR,
                status VARCHAR DEFAULT 'completed' NOT NULL,
                created_by VARCHAR,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        """))
        
        print("🛠️ Creando tabla 'return_items'...")
        connection.execute(text("""
            CREATE TABLE return_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                return_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                condition VARCHAR NOT NULL,
                action VARCHAR NOT NULL,
                imei VARCHAR,
                FOREIGN KEY(return_id) REFERENCES returns(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """))
        
        # Crear índices
        print("📊 Creando índices...")
        connection.execute(text("CREATE INDEX idx_returns_order ON returns (order_id)"))
        connection.execute(text("CREATE INDEX idx_return_items_return ON return_items (return_id)"))
        
        print("✅ Migración completada exitosamente.")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        sys.exit(1)
