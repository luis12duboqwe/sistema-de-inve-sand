from sqlalchemy import create_engine, text
from app.config import settings

def migrate():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        # Verificar si las columnas ya existen
        result = conn.execute(text("PRAGMA table_info(trade_ins)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'color' not in columns:
            print("Agregando columna 'color' a trade_ins...")
            conn.execute(text("ALTER TABLE trade_ins ADD COLUMN color VARCHAR"))
            
        if 'capacidad' not in columns:
            print("Agregando columna 'capacidad' a trade_ins...")
            conn.execute(text("ALTER TABLE trade_ins ADD COLUMN capacidad VARCHAR"))
            
        print("Migración completada exitosamente.")

if __name__ == "__main__":
    migrate()
