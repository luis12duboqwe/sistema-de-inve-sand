import { inventoryService as localService } from './inventoryService'
import { apiClient } from './apiClient'
import type {
  Profile,
  Product,
  ProductWithStock,
  OrderWithItems,
  CreateOrderRequest,
  Order,
  Stock,
  OrderItem
} from './types'

async function getUseApiSetting(): Promise<boolean> {
  const useApi = await window.spark.kv.get<boolean>('settings_use_api')
  return useApi ?? false
}

export interface IInventoryService {
  initializeData(
    profiles: Profile[],
    products: Product[],
    stock: Stock[],
    orders?: Order[],
    orderItems?: OrderItem[]
  ): Promise<void>
  
  fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive?: boolean
  ): Promise<ProductWithStock[]>
  
  createOrder(request: CreateOrderRequest): Promise<OrderWithItems>
  
  fetchOrders(profileSlug?: string): Promise<OrderWithItems[]>
  
  createProfile(name: string, slug: string): Promise<Profile>
  
  listProfiles(): Promise<Profile[]>
  
  updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<Order>
  
  addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number
  ): Promise<Product | ProductWithStock>
  
  updateStock(productId: number, cantidad: number): Promise<void>
  
  updateProduct(
    productId: number,
    updates: Partial<Product>
  ): Promise<Product | ProductWithStock>
}

class UnifiedInventoryService implements IInventoryService {
  private async getService(): Promise<IInventoryService> {
    const useApi = await getUseApiSetting()
    return useApi ? new ApiInventoryService() : localService
  }

  async initializeData(
    profiles: Profile[],
    products: Product[],
    stock: Stock[],
    orders: Order[] = [],
    orderItems: OrderItem[] = []
  ): Promise<void> {
    const service = await this.getService()
    return service.initializeData(profiles, products, stock, orders, orderItems)
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive = false
  ): Promise<ProductWithStock[]> {
    const service = await this.getService()
    return service.fetchProducts(profileSlug, search, includeInactive)
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    const service = await this.getService()
    return service.createOrder(request)
  }

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    const service = await this.getService()
    return service.fetchOrders(profileSlug)
  }

  async createProfile(name: string, slug: string): Promise<Profile> {
    const service = await this.getService()
    return service.createProfile(name, slug)
  }

  async listProfiles(): Promise<Profile[]> {
    const service = await this.getService()
    return service.listProfiles()
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<Order> {
    const service = await this.getService()
    return service.updateOrderStatus(orderId, estado)
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number
  ): Promise<Product | ProductWithStock> {
    const service = await this.getService()
    return service.addProduct(product, initialStock)
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    const service = await this.getService()
    return service.updateStock(productId, cantidad)
  }

  async updateProduct(
    productId: number,
    updates: Partial<Product>
  ): Promise<Product | ProductWithStock> {
    const service = await this.getService()
    return service.updateProduct(productId, updates)
  }
}

class ApiInventoryService implements IInventoryService {
  async initializeData(): Promise<void> {
    await apiClient.initializeData()
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive = false
  ): Promise<ProductWithStock[]> {
    return apiClient.fetchProducts(profileSlug, search, includeInactive)
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    return apiClient.createOrder(request)
  }

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    return apiClient.fetchOrders(profileSlug)
  }

  async createProfile(name: string, slug: string): Promise<Profile> {
    return apiClient.createProfile(name, slug)
  }

  async listProfiles(): Promise<Profile[]> {
    return apiClient.listProfiles()
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<Order> {
    return apiClient.updateOrderStatus(orderId, estado)
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number
  ): Promise<ProductWithStock> {
    return apiClient.createProduct(product as Omit<Product, 'id' | 'activo'>, initialStock)
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    return apiClient.updateStock(productId, cantidad)
  }

  async updateProduct(
    productId: number,
    updates: Partial<Product>
  ): Promise<ProductWithStock> {
    return apiClient.updateProduct(productId, updates)
  }
}

export const inventoryServiceInstance: IInventoryService = new UnifiedInventoryService()

export { getUseApiSetting }
