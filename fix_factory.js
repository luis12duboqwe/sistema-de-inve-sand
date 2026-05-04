const fs = require('fs');
let content = fs.readFileSync('src/lib/inventoryServiceFactory.ts', 'utf8');

if (!content.includes('getProductByIMEI(imei: string) {')) {
  // Add to LocalServiceWrapper
  content = content.replace(
    'updateOrder(id: number, order: UpdateOrderRequest): Promise<OrderWithItems> {\n    return localService.updateOrder(id, order)\n  }',
    'updateOrder(id: number, order: UpdateOrderRequest): Promise<OrderWithItems> {\n    return localService.updateOrder(id, order)\n  }\n\n  getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    return localService.getProductByIMEI(imei)\n  }'
  );
  
  // Add to ApiInventoryService
  content = content.replace(
    'updateOrder(id: number, order: UpdateOrderRequest): Promise<OrderWithItems> {\n    return apiClient.updateOrder(id, order)\n  }',
    'updateOrder(id: number, order: UpdateOrderRequest): Promise<OrderWithItems> {\n    return apiClient.updateOrder(id, order)\n  }\n\n  getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    return apiClient.getProductByIMEI(imei)\n  }\n\n  cancelOrder(id: number, returnToStock: boolean, locationId?: number): Promise<OrderWithItems> {\n    // apiClient does not have raw cancelOrder, use updateOrder to cancel\n    return apiClient.updateOrder(id, { status: "cancelled" } as any);\n  }'
  );
  
  // Add to UnifiedInventoryService
  content = content.replace(
    /return service\.updateOrder\(id, order\)\n  \}/,
    'return service.updateOrder(id, order)\n  }\n\n  async getProductByIMEI(imei: string): Promise<ProductWithStock> {\n    const service = await this.getService()\n    return service.getProductByIMEI(imei)\n  }'
  );
}

fs.writeFileSync('src/lib/inventoryServiceFactory.ts', content);
