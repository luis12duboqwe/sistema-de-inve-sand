import sqlite3
import os

DB_PATH = "inventory.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(profiles)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "settings" not in columns:
            print("Adding 'settings' column to 'profiles' table...")
            cursor.execute("ALTER TABLE profiles ADD COLUMN settings TEXT")
            conn.commit()
            print("Migration successful.")
        else:
            print("'settings' column already exists in 'profiles' table.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
