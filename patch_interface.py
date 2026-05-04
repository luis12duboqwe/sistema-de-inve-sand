with open("src/lib/inventoryServiceFactory.ts", "r") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    if "createProduct(product: Omit<ProductWithStock," in line:
        new_lines.append("  getProductByIMEI(imei: string): Promise<ProductWithStock>\n")
        new_lines.append("  bulkCreateProducts(products: import('./types').ProductCreate[], locationId?: number): Promise<ProductWithStock[]>\n")

with open("src/lib/inventoryServiceFactory.ts", "w") as f:
    f.writelines(new_lines)
