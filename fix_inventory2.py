import re

with open('src/lib/inventoryService.ts', 'r') as f:
    text = f.read()

# Fix shorthand stock_anterior property
text = re.sub(r'(\s+)stock_anterior,', r'\1stock_anterior: stockAnterior,', text)
text = re.sub(r'(\s+)location_id,', r'\1location_id: locationId,', text)

# Replace 'reversa_venta' with 'devolucion' or whatever it is
text = re.sub(r"tipo_cambio: 'reversa_venta'", r"tipo_cambio: 'devolucion'", text)
text = re.sub(r"referencia_tipo: 'order_deleted'", r"referencia_tipo: 'manual_adjustment'", text)
text = re.sub(r"action: 'confirm',", r"action: 'create', // Fix invalid sync action", text)
text = re.sub(r"action: 'reject',", r"action: 'delete', // Fix invalid sync action", text)

with open('src/lib/inventoryService.ts', 'w') as f:
    f.write(text)
