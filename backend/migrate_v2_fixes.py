import sqlite3
import os

DB_FILE = "inventory.db"

def migrate():
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # 1. Add 'costo' to 'products' table
        print("Adding 'costo' column to 'products' table...")
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN costo NUMERIC(10, 2) DEFAULT 0")
            print("  - Added 'costo' column.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("  - 'costo' column already exists.")
            else:
                raise e

        # 2. Add 'cantidad_defectuosa' to 'stock' table
        print("Adding 'cantidad_defectuosa' column to 'stock' table...")
        try:
            cursor.execute("ALTER TABLE stock ADD COLUMN cantidad_defectuosa INTEGER DEFAULT 0")
            print("  - Added 'cantidad_defectuosa' column.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("  - 'cantidad_defectuosa' column already exists.")
            else:
                raise e

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
