from app.database import engine, Base
import app.models  # Import models to register them with Base
from sqlalchemy import text

def migrate():
    print("Migrating database for Financing features...")
    
    # 1. Create new tables (Banks, FinancingOptions)
    Base.metadata.create_all(bind=engine)
    print("✓ Created new tables (if not existed)")
    
    # 2. Add financing_details column to orders
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(orders)"))
            columns = [row[1] for row in result]
            
            if "financing_details" not in columns:
                print("Adding financing_details column to orders...")
                conn.execute(text("ALTER TABLE orders ADD COLUMN financing_details TEXT"))
                print("✓ Added financing_details column")
            else:
                print("✓ financing_details column already exists")
                
        except Exception as e:
            print(f"Error altering table: {e}")

if __name__ == "__main__":
    migrate()
