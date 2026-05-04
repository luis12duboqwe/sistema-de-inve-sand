with open("src/lib/inventoryServiceFactory.ts", "r") as f:
    content = f.read()

# IInventoryService
content = content.replace(
    "  createProduct(product: Omit<ProductWithStock, 'id'>, locationId?: number): Promise<ProductWithStock>\n",
    "  createProduct(product: Omit<ProductWithStock, 'id'>, locationId?: number): Promise<ProductWithStock>\n  getProductByIMEI(imei: string): Promise<ProductWithStock>\n  bulkCreateProducts(products: Partial<ProductWithStock>[], locationId?: number): Promise<ProductWithStock[]>\n",
    1
)

# LocalServiceWrapper
content = content.replace(
    "  async getReturns(): Promise<Return[]> {\n    return this.service.getReturns()\n  }",
    "  async getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    return this.service.getProductByIMEI(imei)\n  }\n\n  async getReturns(): Promise<Return[]> {\n    return this.service.getReturns()\n  }",
    1
)

# UnifiedInventoryService
content = content.replace(
    "  async getReturns(): Promise<Return[]> {\n    try {\n      const service = await this.getService()\n      return service.getReturns()",
    "  async getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    const service = await this.getService()\n    return service.getProductByIMEI(imei)\n  }\n\n  async getReturns(): Promise<Return[]> {\n    try {\n      const service = await this.getService()\n      return service.getReturns()",
    1
)

# ApiInventoryService
content = content.replace(
    "  async getReturns(): Promise<Return[]> {\n    return apiClient.getReturns()\n  }",
    "  async getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    return apiClient.getProductByIMEI(imei)\n  }\n\n  async getReturns(): Promise<Return[]> {\n    return apiClient.getReturns()\n  }",
    1
)

content = content.replace(
    "  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {\n    return apiClient.createOrder(request)\n  }",
    "  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {\n    return apiClient.createOrder(request)\n  }\n\n  async cancelOrder(orderId: number, reason?: string): Promise<OrderWithItems> {\n    return apiClient.cancelOrder(orderId, reason)\n  }",
    1
)

with open("src/lib/inventoryServiceFactory.ts", "w") as f:
    f.write(content)
