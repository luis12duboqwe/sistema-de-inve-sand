import re

with open('src/lib/inventoryService.ts', 'r') as f:
    content = f.read()

# Fix stock_anterior shorthand property errors
content = re.sub(r'\bstock_anterior,\n', r'stock_anterior: stockAnterior,\n', content)

# Fix imeiEvents typo in inventoryService.ts (probably inside createOrder)
# Actually let's look at lines 1385-1400 first to understand context
with open('fix_inventory_service_temp_dump.txt', 'w') as temp:
    temp.write(content)

