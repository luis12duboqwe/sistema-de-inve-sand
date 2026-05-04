with open("src/lib/inventoryServiceFactory.ts", "r") as f:
    lines = f.readlines()

out = []
in_IInventoryService = False
in_LocalService = False
in_Unified = False
in_Api = False

for line in lines:
    if line.startswith("interface IInventoryService {"):
        in_IInventoryService = True
    elif line.startswith("class LocalServiceWrapper implements"):
        in_LocalService = True
    elif line.startswith("class UnifiedInventoryService implements"):
        in_Unified = True
    elif line.startswith("class ApiInventoryService implements"):
        in_Api = True

    if "createProduct(product: Omit<ProductWithStock, 'id'>, locationId?: number" in line and in_IInventoryService:
        out.append(line)
        out.append("  bulkCreateProducts(products: Partial<ProductWithStock>[], locationId?: number): Promise<ProductWithStock[]>\n")
        out.append("  getProductByIMEI(imei: string): Promise<ProductWithStock>\n")
        in_IInventoryService = False
        continue

    if "  async getReturns()" in line and in_LocalService:
        out.append("  async getProductByIMEI(imei: string): Promise<ProductWithStock> { return this.service.getProductByIMEI(imei) }\n")
        out.append(line)
        continue

    if "  async getReturns()" in line and in_Unified:
        out.append("  async getProductByIMEI(imei: string): Promise<ProductWithStock> { const service = await this.getService(); return service.getProductByIMEI(imei) }\n")
        out.append(line)
        continue

    if "  async getReturns()" in line and in_Api:
        out.append("  async getProductByIMEI(imei: string): Promise<ProductWithStock> { return apiClient.getProductByIMEI(imei) }\n")
        out.append(line)
        continue

    if "  async createOrder(" in line and in_Api: # it might be inside Api
        out.append(line)
        out.append("  async cancelOrder(orderId: number, reason?: string): Promise<import('./types').OrderWithItems> { return apiClient.cancelOrder(orderId, reason) }\n")
        continue

    out.append(line)

with open("src/lib/inventoryServiceFactory.ts", "w") as f:
    f.writelines(out)
