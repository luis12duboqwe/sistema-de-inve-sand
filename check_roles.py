import sqlite3
import os

def list_roles():
    db_path = 'backend/inventory.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description FROM roles")
        roles = cursor.fetchall()
        
        print(f"Roles found in {db_path}:")
        print("-" * 50)
        print(f"{'ID':<5} {'Name':<20} {'Description'}")
        print("-" * 50)
        
        for role in roles:
            print(f"{role[0]:<5} {role[1]:<20} {role[2]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_roles()
