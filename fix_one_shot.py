import re

with open('src/lib/inventoryService.ts', 'r') as f:
    text = f.read()

# 1. replace shorthand property stock_anterior
text = re.sub(r'\bstock_anterior,', r'stock_anterior: stockAnterior,', text)

# 2. replace exact imeiEvents block without messing up braces.
# We will use regex to find: `      }\n      if (imeiEvents.length > 0) {\n        await this.recordSyncEvent({\n          entity: 'imei',\n          action: 'update',\n          entityId: null,\n          payload: {\n            order_id: newOrderId,\n            source_location_id: request.source_location_id ?? null,\n            events: imeiEvents\n          }\n        })\n      }`
# and replace with empty string.
block_to_remove = r"""      }
      if \(imeiEvents\.length > 0\) \{
        await this\.recordSyncEvent\(\{
          entity: 'imei',
          action: 'update',
          entityId: null,
          payload: \{
            order_id: newOrderId,
            source_location_id: request\.source_location_id \?\? null,
            events: imeiEvents
          \}
        \}\)
      \}"""
text = re.sub(block_to_remove, r"      }", text)

# 3. location_id shorthand
text = re.sub(r'\blocation_id,', r'location_id: locationId,', text)

# 4. created_at in stock history
text = text.replace("created_at: entry.created_at || new Date().toISOString(),", "")

# 5. type casting
text = text.replace("stock_items: productStock\n", "stock_items: productStock as import('./types').StockByLocation[]\n")
text = text.replace("return stock\n", "return stock as import('./types').StockByLocation[]\n")
text = text.replace("tipo_cambio: 'reversa_venta'", "tipo_cambio: 'devolucion'")
text = text.replace("referencia_tipo: 'order_deleted'", "referencia_tipo: 'manual_adjustment'")
text = text.replace("ReturnItem['condition']", "import('./types').ReturnItem['condition']")
text = text.replace("ReturnItem['action']", "import('./types').ReturnItem['action']")
text = text.replace("analyzePricing(products,", "analyzePricing(products as import('./types').ProductWithStock[],")
text = text.replace("analyzeInventory(products,", "analyzeInventory(products as import('./types').ProductWithStock[],")

# 6. location tipo
text = text.replace("tipo: 'tienda',", "tipo: 'tienda' as import('./types').Location['tipo'],")

# 7. updated_at TrainingQueueItem
# Context:
#         admin_correction: correction?.trim() || items[index].admin_correction,
#         updated_at: now
text = text.replace("admin_correction: correction?.trim() || items[index].admin_correction,\n        updated_at: now\n", "admin_correction: correction?.trim() || items[index].admin_correction\n")


with open('src/lib/inventoryService.ts', 'w') as f:
    f.write(text)

