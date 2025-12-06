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

  updateOrder(
    orderId: number,
    updates: {
      customer_name?: string
      customer_phone?: string
      canal?: Order['canal']
      metodo_pago?: Order['metodo_pago']
      items?: Array<{
        id?: number
        product_id: number
        cantidad: number
      }>
    }
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

  bulkCreateProducts(productsData: Partial<ProductWithStock>[]): Promise<ProductWithStock[]>
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

  async updateOrder(
    orderId: number,
    updates: {
      customer_name?: string
      customer_phone?: string
      canal?: Order['canal']
      metodo_pago?: Order['metodo_pago']
      items?: Array<{
        id?: number
        product_id: number
        cantidad: number
      }>
    }
  ): Promise<OrderWithItems> {
    return this.service.updateOrder(orderId, updates)
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

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[]): Promise<ProductWithStock[]> {
    return this.service.bulkCreateProducts(productsData)
  }
}

class UnifiedInventoryService implements IInventoryService {
  private async getService(): Promise<IInventoryService> {
    try {
      const useApi = await getUseApiSetting()
      return useApi ? new ApiInventoryService() : new LocalServiceWrapper()
    } catch (error) {
      console.error('Error determining service type:', error)
      return new LocalServiceWrapper()
    }
  }

  async initializeData(
    profiles: Profile[],
    products: Product[],
    stock: Stock[],
    orders: Order[] = [],
    orderItems: OrderItem[] = []
  ): Promise<void> {
    try {
      const service = await this.getService()
      return service.initializeData(profiles, products, stock, orders, orderItems)
    } catch (error) {
      console.error('Error initializing data (unified):', error)
      throw new Error(`Failed to initialize data: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive = false
  ): Promise<ProductWithStock[]> {
    try {
      const service = await this.getService()
      return service.fetchProducts(profileSlug, search, includeInactive)
    } catch (error) {
      console.error('Error fetching products (unified):', error)
      throw new Error(`Failed to fetch products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getProducts(): Promise<ProductWithStock[]> {
    try {
      return this.fetchProducts(undefined, undefined, true)
    } catch (error) {
      console.error('Error getting products (unified):', error)
      throw new Error(`Failed to get products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    try {
      const service = await this.getService()
      return service.createOrder(request)
    } catch (error) {
      console.error('Error creating order (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to create order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    try {
      const service = await this.getService()
      return service.fetchOrders(profileSlug)
    } catch (error) {
      console.error('Error fetching orders (unified):', error)
      throw new Error(`Failed to fetch orders: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getOrders(): Promise<OrderWithItems[]> {
    try {
      return this.fetchOrders()
    } catch (error) {
      console.error('Error getting orders (unified):', error)
      throw new Error(`Failed to get orders: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createProfile(profile: Omit<Profile, 'id'>): Promise<Profile> {
    try {
      const service = await this.getService()
      return service.createProfile(profile)
    } catch (error) {
      console.error('Error creating profile (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to create profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listProfiles(): Promise<Profile[]> {
    try {
      const service = await this.getService()
      return service.listProfiles()
    } catch (error) {
      console.error('Error listing profiles (unified):', error)
      throw new Error(`Failed to list profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getProfiles(): Promise<Profile[]> {
    try {
      return this.listProfiles()
    } catch (error) {
      console.error('Error getting profiles (unified):', error)
      throw new Error(`Failed to get profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    try {
      const service = await this.getService()
      return service.updateProfile(profileId, updates)
    } catch (error) {
      console.error('Error updating profile (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    try {
      const service = await this.getService()
      return service.updateOrderStatus(orderId, estado)
    } catch (error) {
      console.error('Error updating order status (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update order status: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateOrder(
    orderId: number,
    updates: {
      customer_name?: string
      customer_phone?: string
      canal?: Order['canal']
      metodo_pago?: Order['metodo_pago']
      items?: Array<{
        id?: number
        product_id: number
        cantidad: number
      }>
    }
  ): Promise<OrderWithItems> {
    try {
      const service = await this.getService()
      return service.updateOrder(orderId, updates)
    } catch (error) {
      console.error('Error updating order (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number
  ): Promise<ProductWithStock> {
    try {
      const service = await this.getService()
      return service.addProduct(product, initialStock) as Promise<ProductWithStock>
    } catch (error) {
      console.error('Error adding product (unified):', error)
      throw new Error(`Failed to add product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>): Promise<ProductWithStock> {
    try {
      const { stock_disponible, ...productData } = product
      return this.addProduct(productData as Omit<Product, 'id'>, stock_disponible)
    } catch (error) {
      console.error('Error creating product (unified):', error)
      throw new Error(`Failed to create product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.updateStock(productId, cantidad)
    } catch (error) {
      console.error('Error updating stock (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock> {
    try {
      const service = await this.getService()
      return service.updateProduct(productId, updates)
    } catch (error) {
      console.error('Error updating product (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[]): Promise<ProductWithStock[]> {
    try {
      const service = await this.getService()
      return service.bulkCreateProducts(productsData)
    } catch (error) {
      console.error('Error bulk creating products (unified):', error)
      throw new Error(`Failed to bulk create products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
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

  async updateOrder(
    orderId: number,
    updates: {
      customer_name?: string
      customer_phone?: string
      canal?: Order['canal']
      metodo_pago?: Order['metodo_pago']
      items?: Array<{
        id?: number
        product_id: number
        cantidad: number
      }>
    }
  ): Promise<OrderWithItems> {
    return apiClient.updateOrder(orderId, updates)
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

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[]): Promise<ProductWithStock[]> {
    return apiClient.bulkCreateProducts(productsData)
  }
}

export function inventoryServiceFactory(_useAPI: boolean, _apiUrl: string): IInventoryService {
  return new UnifiedInventoryService()
}

export const inventoryServiceInstance: IInventoryService = new UnifiedInventoryService()

export { getUseApiSetting }
