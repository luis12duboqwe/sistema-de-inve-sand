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
  
  getProducts(): Promise<ProductWithStock[]>
  
  createOrder(request: CreateOrderRequest): Promise<OrderWithItems>
  
  fetchOrders(profileSlug?: string): Promise<OrderWithItems[]>
  
  getOrders(): Promise<OrderWithItems[]>
  
  createProfile(profile: Omit<Profile, 'id'>): Promise<Profile>
  
  listProfiles(): Promise<Profile[]>
  
  getProfiles(): Promise<Profile[]>

  updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile>
  
  updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems>
  
  addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number
  ): Promise<Product | ProductWithStock>
  
  createProduct(product: Omit<ProductWithStock, 'id'>): Promise<ProductWithStock>
  
  updateStock(productId: number, cantidad: number): Promise<void>
  
  updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock>
}

class LocalServiceWrapper implements IInventoryService {
  private service = localService

  async initializeData(
    profiles: Profile[],
    products: Product[],
    stock: Stock[],
    orders?: Order[],
    orderItems?: OrderItem[]
  ): Promise<void> {
    return this.service.initializeData(profiles, products, stock, orders, orderItems)
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive?: boolean
  ): Promise<ProductWithStock[]> {
    return this.service.fetchProducts(profileSlug, search, includeInactive)
  }

  async getProducts(): Promise<ProductWithStock[]> {
    return this.service.getProducts()
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    return this.service.createOrder(request)
  }

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    return this.service.fetchOrders(profileSlug)
  }

  async getOrders(): Promise<OrderWithItems[]> {
    return this.service.getOrders()
  }

  async createProfile(profile: Omit<Profile, 'id'>): Promise<Profile> {
    return this.service.createProfile(profile.name, profile.slug)
  }

  async listProfiles(): Promise<Profile[]> {
    return this.service.listProfiles()
  }

  async getProfiles(): Promise<Profile[]> {
    return this.service.getProfiles()
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    return this.service.updateProfile(profileId, updates)
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    return this.service.updateOrderStatus(orderId, estado)
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number
  ): Promise<ProductWithStock> {
    return this.service.addProduct(product, initialStock)
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>): Promise<ProductWithStock> {
    return this.service.createProduct(product)
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    return this.service.updateStock(productId, cantidad)
  }

  async updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock> {
    return this.service.updateProduct(productId, updates)
  }
}

class UnifiedInventoryService implements IInventoryService {
  private async getService(): Promise<IInventoryService> {
    const useApi = await getUseApiSetting()
    return useApi ? new ApiInventoryService() : new LocalServiceWrapper()
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

  async getProducts(): Promise<ProductWithStock[]> {
    return this.fetchProducts(undefined, undefined, true)
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    const service = await this.getService()
    return service.createOrder(request)
  }

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    const service = await this.getService()
    return service.fetchOrders(profileSlug)
  }

  async getOrders(): Promise<OrderWithItems[]> {
    return this.fetchOrders()
  }

  async createProfile(profile: Omit<Profile, 'id'>): Promise<Profile> {
    const service = await this.getService()
    return service.createProfile(profile)
  }

  async listProfiles(): Promise<Profile[]> {
    const service = await this.getService()
    return service.listProfiles()
  }

  async getProfiles(): Promise<Profile[]> {
    return this.listProfiles()
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    const service = await this.getService()
    return service.updateProfile(profileId, updates)
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    const service = await this.getService()
    return service.updateOrderStatus(orderId, estado)
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number
  ): Promise<ProductWithStock> {
    const service = await this.getService()
    return service.addProduct(product, initialStock) as Promise<ProductWithStock>
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>): Promise<ProductWithStock> {
    const { stock_disponible, ...productData } = product
    return this.addProduct(productData as Omit<Product, 'id'>, stock_disponible)
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    const service = await this.getService()
    return service.updateStock(productId, cantidad)
  }

  async updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock> {
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

  async getProducts(): Promise<ProductWithStock[]> {
    return this.fetchProducts(undefined, undefined, true)
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    return apiClient.createOrder(request)
  }

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    return apiClient.fetchOrders(profileSlug)
  }

  async getOrders(): Promise<OrderWithItems[]> {
    return this.fetchOrders()
  }

  async createProfile(profile: Omit<Profile, 'id'>): Promise<Profile> {
    return apiClient.createProfile(profile.name, profile.slug)
  }

  async listProfiles(): Promise<Profile[]> {
    return apiClient.listProfiles()
  }

  async getProfiles(): Promise<Profile[]> {
    return this.listProfiles()
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    return apiClient.updateProfile(profileId, updates)
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    const order = await apiClient.updateOrderStatus(orderId, estado)
    const orders = await this.fetchOrders()
    const orderWithItems = orders.find(o => o.id === order.id)
    if (!orderWithItems) {
      throw new Error(`Order with id ${orderId} not found after update`)
    }
    return orderWithItems
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number
  ): Promise<ProductWithStock> {
    return apiClient.createProduct(product as Omit<Product, 'id' | 'activo'>, initialStock)
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>): Promise<ProductWithStock> {
    const { stock_disponible, ...productData } = product
    return this.addProduct(productData as Omit<Product, 'id'>, stock_disponible)
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    return apiClient.updateStock(productId, cantidad)
  }

  async updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock> {
    return apiClient.updateProduct(productId, updates)
  }
}

export function inventoryServiceFactory(useAPI: boolean, apiUrl: string): IInventoryService {
  return new UnifiedInventoryService()
}

export const inventoryServiceInstance: IInventoryService = new UnifiedInventoryService()

export { getUseApiSetting }
