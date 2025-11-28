import type {
  Profile,
  Product,
  Stock,
  Order,
  OrderItem,
  ProductWithStock,
  OrderWithItems,
  CreateOrderRequest
} from './types'

const STORAGE_KEYS = {
  PROFILES: 'inventory_profiles',
  PRODUCTS: 'inventory_products',
  STOCK: 'inventory_stock',
  ORDERS: 'inventory_orders',
  ORDER_ITEMS: 'inventory_order_items'
}

export class InventoryService {
  private async loadProfiles(): Promise<Profile[]> {
    const data = await window.spark.kv.get<Profile[]>(STORAGE_KEYS.PROFILES)
    return data || []
  }

  private async setProfiles(profiles: Profile[]): Promise<void> {
    await window.spark.kv.set(STORAGE_KEYS.PROFILES, profiles)
  }

  private async loadProducts(): Promise<Product[]> {
    const data = await window.spark.kv.get<Product[]>(STORAGE_KEYS.PRODUCTS)
    return data || []
  }

  private async setProducts(products: Product[]): Promise<void> {
    await window.spark.kv.set(STORAGE_KEYS.PRODUCTS, products)
  }

  private async getStock(): Promise<Stock[]> {
    const data = await window.spark.kv.get<Stock[]>(STORAGE_KEYS.STOCK)
    return data || []
  }

  private async setStock(stock: Stock[]): Promise<void> {
    await window.spark.kv.set(STORAGE_KEYS.STOCK, stock)
  }

  private async loadOrders(): Promise<Order[]> {
    const data = await window.spark.kv.get<Order[]>(STORAGE_KEYS.ORDERS)
    return data || []
  }

  private async setOrders(orders: Order[]): Promise<void> {
    await window.spark.kv.set(STORAGE_KEYS.ORDERS, orders)
  }

  private async getOrderItems(): Promise<OrderItem[]> {
    const data = await window.spark.kv.get<OrderItem[]>(STORAGE_KEYS.ORDER_ITEMS)
    return data || []
  }

  private async setOrderItems(items: OrderItem[]): Promise<void> {
    await window.spark.kv.set(STORAGE_KEYS.ORDER_ITEMS, items)
  }

  async initializeData(
    profiles: Profile[],
    products: Product[],
    stock: Stock[],
    orders: Order[] = [],
    orderItems: OrderItem[] = []
  ): Promise<void> {
    await this.setProfiles(profiles)
    await this.setProducts(products)
    await this.setStock(stock)
    await this.setOrders(orders)
    await this.setOrderItems(orderItems)
  }

  async fetchProducts(profileSlug?: string, search?: string, includeInactive = false): Promise<ProductWithStock[]> {
    const [products, stock, profiles] = await Promise.all([
      this.loadProducts(),
      this.getStock(),
      this.loadProfiles()
    ])

    let filtered = includeInactive ? products : products.filter(p => p.activo)

    if (profileSlug) {
      const profile = profiles.find(pr => pr.slug === profileSlug)
      if (profile) {
        filtered = filtered.filter(p => p.profile_id === profile.id)
      }
    }

    if (search) {
      const searchLower = search.toLowerCase()
      filtered = filtered.filter(
        p =>
          String(p.nombre || '').toLowerCase().includes(searchLower) ||
          String(p.marca || '').toLowerCase().includes(searchLower) ||
          String(p.modelo || '').toLowerCase().includes(searchLower) ||
          String(p.sku || '').toLowerCase().includes(searchLower)
      )
    }

    const productsWithStock: ProductWithStock[] = filtered
      .map(product => {
        const stockEntry = stock.find(s => s.product_id === product.id)
        return {
          ...product,
          stock_disponible: stockEntry?.cantidad_disponible || 0
        }
      })

    return productsWithStock
  }

  async getProducts(): Promise<ProductWithStock[]> {
    return this.fetchProducts(undefined, undefined, true)
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    const [profiles, products, stock, orders, orderItems] = await Promise.all([
      this.loadProfiles(),
      this.loadProducts(),
      this.getStock(),
      this.loadOrders(),
      this.getOrderItems()
    ])

    const profile = profiles.find(p => p.slug === request.profile_slug)
    if (!profile) {
      throw new Error(`Profile with slug "${request.profile_slug}" not found`)
    }

    const phoneAsString = String(request.customer_phone || '').trim()
    if (!phoneAsString) {
      throw new Error('Customer phone number is required')
    }

    for (const item of request.items) {
      const product = products.find(p => p.id === item.product_id && p.activo)
      if (!product) {
        throw new Error(`Product with id ${item.product_id} not found or inactive`)
      }

      const stockEntry = stock.find(s => s.product_id === item.product_id)
      if (!stockEntry || stockEntry.cantidad_disponible < item.cantidad) {
        throw new Error(
          `Insufficient stock for product "${product.nombre}". Available: ${stockEntry?.cantidad_disponible || 0}, Requested: ${item.cantidad}`
        )
      }
    }

    let total = 0
    const newOrderItems: OrderItem[] = []
    const newOrderId = Math.max(0, ...orders.map(o => o.id)) + 1

    for (const item of request.items) {
      const product = products.find(p => p.id === item.product_id)!
      total += product.precio * item.cantidad

      const stockEntry = stock.find(s => s.product_id === item.product_id)!
      stockEntry.cantidad_disponible -= item.cantidad

      const newOrderItem: OrderItem = {
        id: Math.max(0, ...orderItems.map(i => i.id)) + newOrderItems.length + 1,
        order_id: newOrderId,
        product_id: item.product_id,
        cantidad: item.cantidad,
        precio_unitario: product.precio,
        es_regalo_promocion: false
      }
      newOrderItems.push(newOrderItem)
    }

    const newOrder: Order = {
      id: newOrderId,
      profile_id: profile.id,
      customer_name: request.customer_name,
      customer_phone: phoneAsString,
      canal: request.canal,
      metodo_pago: request.metodo_pago,
      total,
      estado: 'pendiente',
      created_at: new Date().toISOString()
    }

    await this.setStock(stock)
    await this.setOrders([...orders, newOrder])
    await this.setOrderItems([...orderItems, ...newOrderItems])

    const orderWithItems: OrderWithItems = {
      ...newOrder,
      items: newOrderItems.map(oi => ({
        ...oi,
        product: products.find(p => p.id === oi.product_id)!
      }))
    }

    return orderWithItems
  }

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    const [orders, orderItems, products, profiles] = await Promise.all([
      this.loadOrders(),
      this.getOrderItems(),
      this.loadProducts(),
      this.loadProfiles()
    ])

    let filtered = orders

    if (profileSlug) {
      const profile = profiles.find(p => p.slug === profileSlug)
      if (profile) {
        filtered = filtered.filter(o => o.profile_id === profile.id)
      }
    }

    const ordersWithItems: OrderWithItems[] = filtered.map(order => {
      const items = orderItems
        .filter(oi => oi.order_id === order.id)
        .map(oi => ({
          ...oi,
          product: products.find(p => p.id === oi.product_id)!
        }))

      return {
        ...order,
        customer_name: String(order.customer_name || ''),
        customer_phone: String(order.customer_phone || ''),
        items
      }
    })

    return ordersWithItems.sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  }

  async getOrders(): Promise<OrderWithItems[]> {
    return this.fetchOrders()
  }

  async createProfile(name: string, slug: string): Promise<Profile> {
    const profiles = await this.loadProfiles()

    if (profiles.some(p => p.slug === slug)) {
      throw new Error(`Profile with slug "${slug}" already exists`)
    }

    const newProfile: Profile = {
      id: Math.max(0, ...profiles.map(p => p.id)) + 1,
      name,
      slug,
      active: true
    }

    await this.setProfiles([...profiles, newProfile])
    return newProfile
  }

  async listProfiles(): Promise<Profile[]> {
    return this.loadProfiles()
  }

  async getProfiles(): Promise<Profile[]> {
    return this.loadProfiles()
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    const profiles = await this.loadProfiles()
    const profileIndex = profiles.findIndex(p => p.id === profileId)

    if (profileIndex === -1) {
      throw new Error(`Profile with id ${profileId} not found`)
    }

    profiles[profileIndex] = {
      ...profiles[profileIndex],
      ...updates
    }

    await this.setProfiles(profiles)
    return profiles[profileIndex]
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    const orders = await this.loadOrders()
    const orderIndex = orders.findIndex(o => o.id === orderId)

    if (orderIndex === -1) {
      throw new Error(`Order with id ${orderId} not found`)
    }

    orders[orderIndex].estado = estado
    await this.setOrders(orders)

    const orderWithItems = await this.fetchOrders()
    const found = orderWithItems.find(o => o.id === orderId)
    if (!found) {
      throw new Error(`Order with id ${orderId} not found after update`)
    }
    return found
  }

  async addProduct(product: Omit<Product, 'id'>, initialStock: number): Promise<ProductWithStock> {
    const [products, stock] = await Promise.all([
      this.loadProducts(),
      this.getStock()
    ])

    const newProduct: Product = {
      ...product,
      id: Math.max(0, ...products.map(p => p.id)) + 1
    }

    const newStock: Stock = {
      id: Math.max(0, ...stock.map(s => s.id)) + 1,
      product_id: newProduct.id,
      cantidad_disponible: initialStock
    }

    await this.setProducts([...products, newProduct])
    await this.setStock([...stock, newStock])

    return {
      ...newProduct,
      stock_disponible: initialStock
    }
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>): Promise<ProductWithStock> {
    const { stock_disponible, ...productData } = product
    return this.addProduct(productData as Omit<Product, 'id'>, stock_disponible)
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    const stock = await this.getStock()
    const stockEntry = stock.find(s => s.product_id === productId)

    if (!stockEntry) {
      throw new Error(`Stock entry for product ${productId} not found`)
    }

    stockEntry.cantidad_disponible = cantidad
    await this.setStock(stock)
  }

  async updateProduct(productId: number, updates: Partial<ProductWithStock>): Promise<ProductWithStock> {
    const products = await this.loadProducts()
    const productIndex = products.findIndex(p => p.id === productId)

    if (productIndex === -1) {
      throw new Error(`Product with id ${productId} not found`)
    }

    const { stock_disponible, ...productUpdates } = updates

    products[productIndex] = {
      ...products[productIndex],
      ...productUpdates
    }

    await this.setProducts(products)

    if (stock_disponible !== undefined) {
      await this.updateStock(productId, stock_disponible)
    }

    const stock = await this.getStock()
    const stockEntry = stock.find(s => s.product_id === productId)

    return {
      ...products[productIndex],
      stock_disponible: stockEntry?.cantidad_disponible || 0
    }
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[]): Promise<ProductWithStock[]> {
    const [products, stock] = await Promise.all([
      this.loadProducts(),
      this.getStock()
    ])

    let nextProductId = Math.max(0, ...products.map(p => p.id)) + 1
    let nextStockId = Math.max(0, ...stock.map(s => s.id)) + 1

    const newProducts: Product[] = []
    const newStockEntries: Stock[] = []
    const createdProducts: ProductWithStock[] = []

    for (const productData of productsData) {
      const { stock_disponible, ...productFields } = productData

      const newProduct: Product = {
        id: nextProductId++,
        profile_id: productFields.profile_id!,
        sku: productFields.sku!,
        nombre: productFields.nombre!,
        categoria: productFields.categoria!,
        marca: productFields.marca!,
        modelo: productFields.modelo || '',
        capacidad: productFields.capacidad || '',
        condicion: productFields.condicion!,
        precio: productFields.precio!,
        moneda: productFields.moneda || 'HNL',
        garantia_meses: productFields.garantia_meses || 0,
        activo: productFields.activo ?? true
      }

      const newStockEntry: Stock = {
        id: nextStockId++,
        product_id: newProduct.id,
        cantidad_disponible: stock_disponible || 0
      }

      newProducts.push(newProduct)
      newStockEntries.push(newStockEntry)

      createdProducts.push({
        ...newProduct,
        stock_disponible: newStockEntry.cantidad_disponible
      })
    }

    await this.setProducts([...products, ...newProducts])
    await this.setStock([...stock, ...newStockEntries])

    return createdProducts
  }
}

export const inventoryService = new InventoryService()
