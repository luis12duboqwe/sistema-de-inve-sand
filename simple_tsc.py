import re

with open('src/lib/inventoryService.ts', 'r') as f:
    text = f.read()

# 1. replace shorthand property stock_anterior with stockAnterior mapping
text = re.sub(r'(\s+)stock_anterior,', r'\1stock_anterior: stockAnterior,', text)

# 3. location_id shorthand
text = re.sub(r'(\s+)location_id,', r'\1location_id: locationId,', text)

# 4. created_at
text = text.replace("created_at: entry.created_at || new Date().toISOString(),", "")

# 5. Type casts
text = text.replace("stock_items: productStock\n", "stock_items: productStock as import('./types').StockByLocation[]\n")
text = text.replace("return stock\n", "return stock as import('./types').StockByLocation[]\n")

# 6. literals
text = text.replace("tipo_cambio: 'reversa_venta'", "tipo_cambio: 'devolucion'")
text = text.replace("referencia_tipo: 'order_deleted'", "referencia_tipo: 'manual_adjustment'")
text = text.replace("tipo: 'tienda',", "tipo: 'tienda' as import('./types').Location['tipo'],")

# 7. imports
text = text.replace("condition: ReturnItem['condition']", "condition: import('./types').ReturnItem['condition']")
text = text.replace("action: ReturnItem['action']", "action: import('./types').ReturnItem['action']")
text = text.replace("analyzePricing(products,", "analyzePricing(products as import('./types').ProductWithStock[],")
text = text.replace("analyzeInventory(products,", "analyzeInventory(products as import('./types').ProductWithStock[],")

# 8. remove updated_at in training queue
text = text.replace("        admin_correction: correction?.trim() || items[index].admin_correction,\n        updated_at: now\n", "        admin_correction: correction?.trim() || items[index].admin_correction\n")

with open('src/lib/inventoryService.ts', 'w') as f:
    f.write(text)
