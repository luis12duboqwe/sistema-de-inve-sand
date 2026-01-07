import sqlite3
import os

def check_columns():
    # Try to find the DB file
    possible_paths = ['backend/inventory.db', 'inventory.db', '../backend/inventory.db']
    db_path = None
    for p in possible_paths:
        if os.path.exists(p):
            db_path = p
            break
            
    if not db_path:
        print(f"Database not found in {possible_paths}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print(f"Columns in users table ({db_path}):")
        found_role_id = False
        for col in columns:
            print(col)
            if col[1] == 'role_id':
                found_role_id = True
        
        if found_role_id:
            print("\n✅ role_id column FOUND.")
        else:
            print("\n❌ role_id column NOT FOUND.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
