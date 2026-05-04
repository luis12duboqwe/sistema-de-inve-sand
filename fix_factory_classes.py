with open("src/lib/inventoryServiceFactory.ts", "r") as f:
    content = f.read()

# IInventoryService cancellation for ApiInventoryService
content = content.replace(
    "  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {\n    return apiClient.createOrder(request)\n  }",
    "  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {\n    return apiClient.createOrder(request)\n  }\n\n  async cancelOrder(orderId: number, reason?: string): Promise<OrderWithItems> {\n    return apiClient.cancelOrder(orderId, reason)\n  }"
)

# getProductByIMEI injections
content = content.replace(
    "  async getReturns(): Promise<Return[]> {\n    return this.service.getReturns()\n  }",
    "  async getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    return this.service.getProductByIMEI(imei)\n  }\n\n  async getReturns(): Promise<Return[]> {\n    return this.service.getReturns()\n  }"
)

content = content.replace(
    "  async getReturns(): Promise<Return[]> {\n    const useApi = await this.useApi()\n    if (useApi) {\n      const service = await this.getService()\n      return service.getReturns()\n    }",
    "  async getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    const service = await this.getService()\n    return service.getProductByIMEI(imei)\n  }\n\n  async getReturns(): Promise<Return[]> {\n    const useApi = await this.useApi()\n    if (useApi) {\n      const service = await this.getService()\n      return service.getReturns()\n    }"
)

content = content.replace(
    "  async getReturns(): Promise<Return[]> {\n    return apiClient.getReturns()\n  }",
    "  async getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    return apiClient.getProductByIMEI(imei)\n  }\n\n  async getReturns(): Promise<Return[]> {\n    return apiClient.getReturns()\n  }"
)

with open("src/lib/inventoryServiceFactory.ts", "w") as f:
    f.write(content)
