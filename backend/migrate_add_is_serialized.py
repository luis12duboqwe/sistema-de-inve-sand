import sqlite3
import sys
import os

# Add parent directory to path to import app modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "backend/inventory.db"

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Add is_serialized column to products table
        print("Adding is_serialized column to products table...")
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN is_serialized BOOLEAN DEFAULT 0")
            print("Column added successfully.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Column is_serialized already exists.")
            else:
                raise e

        # 2. Update is_serialized based on existing data
        # Logic: If category is 'celular' OR has entries in product_imeis, set is_serialized = 1
        print("Updating is_serialized values...")
        
        # Set True for all 'celular' category products
        cursor.execute("UPDATE products SET is_serialized = 1 WHERE categoria = 'celular'")
        
        # Set True for products that already have IMEIs registered (even if not 'celular')
        cursor.execute("""
            UPDATE products 
            SET is_serialized = 1 
            WHERE id IN (SELECT DISTINCT product_id FROM product_imeis)
        """)
        
        print(f"Updated {cursor.rowcount} rows.")

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
