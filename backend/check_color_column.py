import sqlite3

def check_column():
    conn = sqlite3.connect('backend/inventory.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(products)")
    columns = cursor.fetchall()
    conn.close()
    
    found = False
    for col in columns:
        if col[1] == 'color':
            found = True
            print("✅ Columna 'color' encontrada en la tabla products.")
            break
    
    if not found:
        print("❌ Columna 'color' NO encontrada.")

if __name__ == "__main__":
    check_column()
