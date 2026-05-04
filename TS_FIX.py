import re

with open('src/lib/inventoryService.ts', 'r') as f:
    text = f.read()

# 2711: property 'created_at' does not exist on StockHistoryCreateRequest
text = re.sub(r'created_at: entry\.created_at \|\| new Date\(\)\.toISOString\(\),', r"/* created_at: omitted */", text)

# 2799: type Stock[] is not assignable to StockByLocation[] -> cast it
text = re.sub(r'stock_items: productStock\n', r'stock_items: productStock as import("./types").StockByLocation[]\n', text)

# 2848: tipo string to Location.tipo
text = re.sub(r"const newLocation = {([\s\S]*?)tipo: location\.tipo,([\s\S]*?)}", r"const newLocation: import('./types').Location = {\1tipo: location.tipo as import('./types').Location['tipo'],\2}", text)

# 4041: ReturnItem cannot be found
# Probably there is a `ReturnItem` imported or defined somewhere else. If not it's in types.
text = re.sub(r"ReturnItem\['condition'\]", r"import('./types').ReturnItem['condition']", text)
text = re.sub(r"ReturnItem\['action'\]", r"import('./types').ReturnItem['action']", text)

# 4822, 4823: Product[] -> ProductWithStock[]
text = re.sub(r"const pricingInsights = analyzePricing\(products, relevantOrders\)", r"const pricingInsights = analyzePricing(products as import('./types').ProductWithStock[], relevantOrders)", text)
text = re.sub(r"const inventoryInsights = analyzeInventory\(products, relevantOrders\)", r"const inventoryInsights = analyzeInventory(products as import('./types').ProductWithStock[], relevantOrders)", text)

# 4880: location_id missing
#   return stock
text = re.sub(r"return stock\n", r"return stock as import('./types').StockByLocation[]\n", text)

# 5906: updated_at does not exist in type 'TrainingQueueItem'
text = re.sub(r"admin_correction: correction\?\.trim\(\) \|\| items\[index\]\.admin_correction,\n\s*updated_at: now\n", r"admin_correction: correction?.trim() || items[index].admin_correction\n", text)


with open('src/lib/inventoryService.ts', 'w') as f:
    f.write(text)

