import sqlite3
import json

db_path = 'backend/inventory.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Obtener la última orden
cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1")
order = cursor.fetchone()

if not order:
    print("No se encontraron órdenes.")
    exit()

print(f"=== Orden #{order['id']} ===")
print(f"Cliente: {order['customer_name']}")
print(f"Total Final: {order['total']}")
print(f"Método de Pago: {order['metodo_pago']}")
print(f"Estado: {order['estado']}")

if order['financing_details']:
    print(f"\n--- Detalles de Financiamiento ---")
    try:
        details = json.loads(order['financing_details'])
        print(json.dumps(details, indent=2))
    except:
        print(order['financing_details'])

print(f"\n--- Items ---")
cursor.execute("""
    SELECT oi.*, p.nombre, p.precio, p.moneda 
    FROM order_items oi 
    JOIN products p ON oi.product_id = p.id 
    WHERE oi.order_id = ?
""", (order['id'],))
items = cursor.fetchall()

subtotal_items = 0
for item in items:
    total_item = item['cantidad'] * item['precio_unitario']
    subtotal_items += total_item
    print(f"- {item['nombre']} (x{item['cantidad']})")
    print(f"  Precio Unitario en Orden: {item['precio_unitario']}")
    print(f"  Precio Original Producto: {item['precio']} {item['moneda']}")
    print(f"  Subtotal Item: {total_item}")

print(f"\nSubtotal Items: {subtotal_items}")

print(f"\n--- Trade-Ins (Retomas) ---")
cursor.execute("SELECT * FROM trade_ins WHERE order_id = ?", (order['id'],))
trade_ins = cursor.fetchall()

total_trade_ins = 0
for trade in trade_ins:
    print(f"- {trade['marca']} {trade['modelo']} ({trade['condicion']})")
    print(f"  Valor Estimado: {trade['valor_estimado']}")
    total_trade_ins += trade['valor_estimado']

print(f"\nTotal Trade-Ins: {total_trade_ins}")

print(f"\n=== Cálculo Final ===")
print(f"Subtotal Items: {subtotal_items}")
print(f"(-) Trade-Ins:  {total_trade_ins}")
base_imponible = subtotal_items - total_trade_ins
print(f"(=) Base a Pagar: {base_imponible}")

if order['financing_details']:
    details = json.loads(order['financing_details'])
    print(f"(+) Recargo Financiero: {details.get('surcharge', 0)}")
    print(f"(=) Total Final: {order['total']}")

conn.close()
