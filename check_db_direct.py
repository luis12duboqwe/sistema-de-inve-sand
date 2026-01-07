import sqlite3
import os

db_path = 'backend/inventory.db'

if not os.path.exists(db_path):
    print(f"❌ Database file {db_path} does not exist!")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT count(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT count(*) FROM orders")
        orders_count = cursor.fetchone()[0]
        
        print(f"✅ Database check:")
        print(f"   Products: {products_count}")
        print(f"   Orders: {orders_count}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error reading database: {e}")
