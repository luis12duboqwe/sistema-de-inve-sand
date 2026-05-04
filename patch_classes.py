with open("src/lib/inventoryServiceFactory.ts", "r") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Check if LocalServiceWrapper's createProduct
    if i == 394 - 1:
        new_lines.append("  async getProductByIMEI(imei: string) { return this.service.getProductByIMEI(imei) }\n")
        new_lines.append("  async bulkCreateProducts(products: import('./types').ProductCreate[], locationId?: number) { return this.service.bulkCreateProducts(products, locationId) }\n")
        
    # Check if UnifiedInventoryService's createProduct
    if i == 989 - 1:
        new_lines.append("  async getProductByIMEI(imei: string) { const service = await this.getService(); return service.getProductByIMEI(imei) }\n")
        new_lines.append("  async bulkCreateProducts(products: import('./types').ProductCreate[], locationId?: number) { const service = await this.getService(); return service.bulkCreateProducts(products, locationId) }\n")
        
    # Check if ApiInventoryService's createProduct
    if i == 1880 - 1:
        new_lines.append("  async getProductByIMEI(imei: string) { return apiClient.getProductByIMEI(imei) }\n")
        new_lines.append("  async bulkCreateProducts(products: import('./types').ProductCreate[], locationId?: number) { return apiClient.bulkCreateProducts(products, locationId) }\n")
        
    # Check if ApiInventoryService's createOrder
    if i == 1769 - 1:
        new_lines.append("  async cancelOrder(orderId: number, reason?: string): Promise<import('./types').OrderWithItems> { return apiClient.cancelOrder(orderId, reason) }\n")

with open("src/lib/inventoryServiceFactory.ts", "w") as f:
    f.writelines(new_lines)
