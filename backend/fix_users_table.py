import sqlite3
import os

def fix_db():
    # Since we are running this from the backend directory, the DB is in the same dir
    db_path = 'inventory.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        # Fallback check
        if os.path.exists('../backend/inventory.db'):
             db_path = '../backend/inventory.db'
             print(f"Found at {db_path}")
        else:
             return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'role_id' not in columns:
            print(f"Adding role_id column to {db_path}...")
            cursor.execute("ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL")
            conn.commit()
            print("✅ Column role_id added successfully.")
        else:
            print(f"✅ Column role_id already exists in {db_path}.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_db()
