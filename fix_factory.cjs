const fs = require('fs');
const file = 'src/lib/inventoryServiceFactory.ts';
let content = fs.readFileSync(file, 'utf8');

// IInventoryService
content = content.replace(
  /deleteProduct\(id: string\): Promise<void>/,
  `deleteProduct(id: string): Promise<void>
  getProductByIMEI(imei: string): Promise<ProductWithStock | null>
  bulkCreateProducts(products: Omit<ProductWithStock, 'id'>[]): Promise<ProductWithStock[]>`
);

// LocalServiceWrapper
content = content.replace(
  /deleteProduct\(id: string\): Promise<void> \{\s*return this\.local\.deleteProduct\(id\)\s*\}/,
  `deleteProduct(id: string): Promise<void> {
    return this.local.deleteProduct(id)
  }
  async getProductByIMEI(imei: string): Promise<ProductWithStock | null> {
    return this.local.getProductByIMEI(imei)
  }
  async bulkCreateProducts(products: Omit<ProductWithStock, 'id'>[]): Promise<ProductWithStock[]> {
    return this.local.bulkCreateProducts(products)
  }`
);

// ApiInventoryService
content = content.replace(
  /async deleteProduct\(id: string\): Promise<void> \{\s*return this\.api\.deleteProduct\(id\)\s*\}/,
  `async deleteProduct(id: string): Promise<void> {
    return this.api.deleteProduct(id)
  }
  async getProductByIMEI(imei: string): Promise<ProductWithStock | null> {
    return this.api.getProductByIMEI(imei)
  }
  async bulkCreateProducts(products: Omit<ProductWithStock, 'id'>[]): Promise<ProductWithStock[]> {
    return this.api.bulkCreateProducts? this.api.bulkCreateProducts(products) : []
  }`
);

// UnifiedInventoryService
content = content.replace(
  /async deleteProduct\(id: string\): Promise<void> \{\s*return this\.activeService\.deleteProduct\(id\)\s*\}/,
  `async deleteProduct(id: string): Promise<void> {
    return this.activeService.deleteProduct(id)
  }
  async getProductByIMEI(imei: string): Promise<ProductWithStock | null> {
    return this.activeService.getProductByIMEI(imei)
  }
  async bulkCreateProducts(products: Omit<ProductWithStock, 'id'>[]): Promise<ProductWithStock[]> {
    return this.activeService.bulkCreateProducts(products)
  }`
);

fs.writeFileSync(file, content);
console.log('Done');
