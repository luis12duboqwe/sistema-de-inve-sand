import sqlite3
import os

DB_PATH = "/workspaces/spark-template/backend/inventory.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(product_imeis)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "transfer_id" not in columns:
            print("Adding transfer_id column to product_imeis table...")
            # Add transfer_id column
            cursor.execute("ALTER TABLE product_imeis ADD COLUMN transfer_id INTEGER REFERENCES stock_transfers(id) ON DELETE SET NULL")
            
            # Create index for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_imei_transfer ON product_imeis(transfer_id)")
            
            conn.commit()
            print("Migration successful: transfer_id column added.")
        else:
            print("Column transfer_id already exists in product_imeis.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
