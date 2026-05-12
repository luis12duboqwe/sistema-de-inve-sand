import sys
import os
import sqlite3

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.db")
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Agregando métricas a photo_requests...")
    
    try:
        cursor.execute("ALTER TABLE photo_requests ADD COLUMN agent_response_time_minutes INTEGER;")
        print("  Columna 'agent_response_time_minutes' añadida.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  Columna 'agent_response_time_minutes' ya existe.")
        else:
            print(f"  Error: {e}")
            
    try:
        cursor.execute("ALTER TABLE photo_requests ADD COLUMN csat_score INTEGER;")
        print("  Columna 'csat_score' añadida.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  Columna 'csat_score' ya existe.")
        else:
            print(f"  Error: {e}")

    try:
        cursor.execute("ALTER TABLE photo_requests ADD COLUMN csat_feedback TEXT;")
        print("  Columna 'csat_feedback' añadida.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  Columna 'csat_feedback' ya existe.")
        else:
            print(f"  Error: {e}")
            
    conn.commit()
    conn.close()
    print("Métrica actualizadas localmente OK")

if __name__ == "__main__":
    migrate()
