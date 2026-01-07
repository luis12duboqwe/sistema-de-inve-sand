import sqlite3
import os

def list_users():
    db_path = 'backend/inventory.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT u.id, u.username, u.is_superuser, r.name, r.is_system_role 
        FROM users u 
        LEFT JOIN roles r ON u.role_id = r.id
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print(f"{'ID':<5} {'Username':<15} {'Superuser':<10} {'Role':<15} {'System Role'}")
        print("-" * 60)
        for row in results:
            print(f"{row[0]:<5} {row[1]:<15} {row[2]:<10} {str(row[3]):<15} {row[4]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_users()
