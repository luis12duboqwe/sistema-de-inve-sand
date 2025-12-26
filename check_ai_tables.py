import sqlite3
import os

db_path = 'backend/inventory.db'

if not os.path.exists(db_path):
    print(f"❌ Database file {db_path} does not exist!")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['customers', 'ai_profile_configs', 'interaction_logs', 'training_queue']
    missing_tables = [t for t in required_tables if t not in tables]
    
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
        print(f"Existing tables: {tables}")
    else:
        print("✅ All AI tables exist!")
        
        # Check columns in ai_profile_configs to be sure
        cursor.execute("PRAGMA table_info(ai_profile_configs)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"   ai_profile_configs columns: {columns}")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
