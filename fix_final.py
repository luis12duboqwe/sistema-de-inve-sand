import re
with open('src/lib/inventoryService.ts', 'r') as f:
    t = f.read()

# 1. stock_anterior, -> stock_anterior: stockAnterior,
t = re.sub(r'\bstock_anterior,\n', r'stock_anterior: stockAnterior,\n', t)

# 2. imeiEvents typo in createProfile. It was copied over. We delete the block.
# Let's cleanly replace the exact problematic snippet.
bad_snippet = """      }
      if (imeiEvents.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'update',
          entityId: null,
          payload: {
            order_id: newOrderId,
            source_location_id: request.source_location_id ?? null,
            events: imeiEvents
          }
        })
      }
  }

  async listProfiles()"""

good_snippet = """      }
  }

  async listProfiles()"""
t = t.replace(bad_snippet, good_snippet)

# 3. reversa_venta -> devolucion
t = t.replace("tipo_cambio: 'reversa_venta'", "tipo_cambio: 'devolucion'")

# 4. order_deleted -> manual_adjustment
t = t.replace("referencia_tipo: 'order_deleted'", "referencia_tipo: 'manual_adjustment'")

# 5. location_id, -> location_id: locationId,
t = re.sub(r'(\s+)location_id,\n', r'\1location_id: locationId,\n', t)

# 6. created_at omitted
t = t.replace("created_at: entry.created_at || new Date().toISOString(),", "/* created_at implicitly omitted */")

# 7. productStock as import('./types').StockByLocation[]
t = t.replace("stock_items: productStock\n", "stock_items: productStock as import('./types').StockByLocation[]\n")

# 8. Location tipo cast
t = re.sub(r"const newLocation = {([\s\S]*?)tipo: location\.tipo,([\s\S]*?)}", r"const newLocation: import('./types').Location = {\1tipo: location.tipo as import('./types').Location['tipo'],\2}", t)

# 9. ReturnItem missing
t = t.replace("ReturnItem['condition']", "import('./types').ReturnItem['condition']")
t = t.replace("ReturnItem['action']", "import('./types').ReturnItem['action']")

# 10. Product[] to ProductWithStock[]
t = t.replace("analyzePricing(products,", "analyzePricing(products as import('./types').ProductWithStock[],")
t = t.replace("analyzeInventory(products,", "analyzeInventory(products as import('./types').ProductWithStock[],")

# 11. return stock as ...
t = t.replace("return stock\n", "return stock as import('./types').StockByLocation[]\n")

# 12. updated_at on TrainingQueueItem
t = t.replace("        admin_correction: correction?.trim() || items[index].admin_correction,\n        updated_at: now\n", "        admin_correction: correction?.trim() || items[index].admin_correction\n")

with open('src/lib/inventoryService.ts', 'w') as f:
    f.write(t)
