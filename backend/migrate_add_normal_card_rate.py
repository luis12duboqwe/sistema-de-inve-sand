from app.database import engine, Base
from sqlalchemy import text

def migrate():
    print("Migrating database for Normal Card Rate...")
    
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(banks)"))
            columns = [row[1] for row in result]
            
            if "normal_card_rate" not in columns:
                print("Adding normal_card_rate column to banks...")
                conn.execute(text("ALTER TABLE banks ADD COLUMN normal_card_rate NUMERIC(5, 4) DEFAULT 0.0 NOT NULL"))
                print("✓ Added normal_card_rate column")
            else:
                print("✓ normal_card_rate column already exists")
                
        except Exception as e:
            print(f"Error migrating: {e}")

if __name__ == "__main__":
    migrate()
