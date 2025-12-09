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
import { getKV } from './kvStorage'

const STORAGE_KEYS = {
  PROFILES: 'inventory-profiles',
  PRODUCTS: 'inventory-products',
  STOCK: 'inventory-stock',
  ORDERS: 'inventory-orders',
  ORDER_ITEMS: 'inventory-order-items'
}

export class InventoryService {
  private async loadProfiles(): Promise<Profile[]> {
    try {
      const kv = getKV()
      const data = await kv.get<Profile[]>(STORAGE_KEYS.PROFILES)
      return data || []
    } catch (error) {
      console.error('Error loading profiles from KV, returning empty array:', error)
      // No lanzar error, simplemente retornar array vacío para permitir inicialización
      return []
    }
  }

  private async setProfiles(profiles: Profile[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.PROFILES, profiles)
    } catch (error) {
      console.error('Error saving profiles:', error)
      throw new Error(`Failed to save profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async loadProducts(): Promise<Product[]> {
    try {
      const kv = getKV()
      const data = await kv.get<Product[]>(STORAGE_KEYS.PRODUCTS)
      return data || []
    } catch (error) {
      console.error('Error loading products:', error)
      throw new Error(`Failed to load products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async setProducts(products: Product[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.PRODUCTS, products)
    } catch (error) {
      console.error('Error saving products:', error)
      throw new Error(`Failed to save products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async getStock(): Promise<Stock[]> {
    try {
      const kv = getKV()
      const data = await kv.get<Stock[]>(STORAGE_KEYS.STOCK)
      return data || []
    } catch (error) {
      console.error('Error loading stock:', error)
      throw new Error(`Failed to load stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async setStock(stock: Stock[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.STOCK, stock)
    } catch (error) {
      console.error('Error saving stock:', error)
      throw new Error(`Failed to save stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async loadOrders(): Promise<Order[]> {
    try {
      const kv = getKV()
      const data = await kv.get<Order[]>(STORAGE_KEYS.ORDERS)
      return data || []
    } catch (error) {
      console.error('Error loading orders:', error)
      throw new Error(`Failed to load orders: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async setOrders(orders: Order[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.ORDERS, orders)
    } catch (error) {
      console.error('Error saving orders:', error)
      throw new Error(`Failed to save orders: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async getOrderItems(): Promise<OrderItem[]> {
    try {
      const kv = getKV()
      const data = await kv.get<OrderItem[]>(STORAGE_KEYS.ORDER_ITEMS)
      return data || []
    } catch (error) {
      console.error('Error loading order items:', error)
      throw new Error(`Failed to load order items: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async setOrderItems(items: OrderItem[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.ORDER_ITEMS, items)
    } catch (error) {
      console.error('Error saving order items:', error)
      throw new Error(`Failed to save order items: ${error instanceof Error ? error.message : 'Unknown error'}`)
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
      await this.setProfiles(profiles)
      await this.setProducts(products)
      await this.setStock(stock)
      await this.setOrders(orders)
      await this.setOrderItems(orderItems)
    } catch (error) {
      console.error('Error initializing data:', error)
      throw new Error(`Failed to initialize data: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchProducts(profileSlug?: string, search?: string, includeInactive = false): Promise<ProductWithStock[]> {
    try {
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
    } catch (error) {
      console.error('Error fetching products:', error)
      throw new Error(`Failed to fetch products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getProducts(): Promise<ProductWithStock[]> {
    return this.fetchProducts(undefined, undefined, true)
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    try {
      const [profiles, products, stock, orders, orderItems] = await Promise.all([
        this.loadProfiles(),
        this.loadProducts(),
        this.getStock(),
        this.loadOrders(),
        this.getOrderItems()
      ])

      if (!request.source_location_id) {
        throw new Error('source_location_id is required in V2.0')
      }

      if (!request.profile_slug) {
        throw new Error('Local mode requires profile_slug (legacy) until SalesProfiles are supported locally')
      }

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
        source_location_id: request.source_location_id,
        customer_name: request.customer_name,
        customer_phone: phoneAsString,
        canal: request.canal,
        metodo_pago: request.metodo_pago,
        total,
        estado: 'pendiente',
        created_at: new Date().toISOString(),
        notas: request.notas,
        updated_at: new Date().toISOString()
      }

      await this.setStock(stock)
      await this.setOrders([...orders, newOrder])
      await this.setOrderItems([...orderItems, ...newOrderItems])

      const orderWithItems: OrderWithItems = {
        ...newOrder,
        items: newOrderItems.map(oi => ({
          ...oi,
          product: products.find(p => p.id === oi.product_id)
        }))
      }

      return orderWithItems
    } catch (error) {
      console.error('Error creating order:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to create order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchOrders(salesProfileSlug?: string): Promise<OrderWithItems[]> {
    try {
      const [orders, orderItems, products, profiles] = await Promise.all([
        this.loadOrders(),
        this.getOrderItems(),
        this.loadProducts(),
        this.loadProfiles()
      ])

      let filtered = orders

      // Nota: modo local aún no soporta SalesProfiles; se ignora salesProfileSlug

      const ordersWithItems: OrderWithItems[] = filtered.map(order => {
        const items = orderItems
          .filter(oi => oi.order_id === order.id)
          .map(oi => ({
            ...oi,
            product: products.find(p => p.id === oi.product_id)
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
    } catch (error) {
      console.error('Error fetching orders:', error)
      throw new Error(`Failed to fetch orders: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getOrders(): Promise<OrderWithItems[]> {
    return this.fetchOrders()
  }

  async createProfile(name: string, slug: string): Promise<Profile> {
    try {
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
    } catch (error) {
      console.error('Error creating profile:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to create profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listProfiles(): Promise<Profile[]> {
    try {
      return this.loadProfiles()
    } catch (error) {
      console.error('Error listing profiles:', error)
      throw new Error(`Failed to list profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getProfiles(): Promise<Profile[]> {
    try {
      return this.loadProfiles()
    } catch (error) {
      console.error('Error getting profiles:', error)
      throw new Error(`Failed to get profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    try {
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
    } catch (error) {
      console.error('Error updating profile:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to update profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    try {
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
    } catch (error) {
      console.error('Error updating order status:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to update order status: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateOrder(
    orderId: number,
    updates: {
      customer_name?: string
      customer_phone?: string
      canal?: Order['canal']
      metodo_pago?: Order['metodo_pago']
      notas?: string
      items?: Array<{
        id?: number
        product_id: number
        cantidad: number
      }>
    }
  ): Promise<OrderWithItems> {
    try {
      const [orders, orderItems, products, stock] = await Promise.all([
        this.loadOrders(),
        this.getOrderItems(),
        this.loadProducts(),
        this.getStock()
      ])

      const orderIndex = orders.findIndex(o => o.id === orderId)
      if (orderIndex === -1) {
        throw new Error(`Order with id ${orderId} not found`)
      }

      const currentOrder = orders[orderIndex]
      const currentItems = orderItems.filter(oi => oi.order_id === orderId)

      if (updates.items) {
        for (const item of currentItems) {
          const stockEntry = stock.find(s => s.product_id === item.product_id)
          if (stockEntry) {
            stockEntry.cantidad_disponible += item.cantidad
          }
        }

        for (const item of updates.items) {
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

        const updatedOrderItems = orderItems.filter(oi => oi.order_id !== orderId)
        const newOrderItems: OrderItem[] = []
        let nextItemId = Math.max(0, ...orderItems.map(i => i.id)) + 1

        let total = 0
        for (const item of updates.items) {
          const product = products.find(p => p.id === item.product_id)
          if (!product) {
            throw new Error(`Product with id ${item.product_id} not found`)
          }
          total += product.precio * item.cantidad

          const stockEntry = stock.find(s => s.product_id === item.product_id)
          if (!stockEntry) {
            throw new Error(`Stock entry for product ${item.product_id} not found`)
          }
          stockEntry.cantidad_disponible -= item.cantidad

          const newOrderItem: OrderItem = {
            id: item.id || nextItemId++,
            order_id: orderId,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: product.precio,
            es_regalo_promocion: false
          }
          newOrderItems.push(newOrderItem)
        }

        await this.setOrderItems([...updatedOrderItems, ...newOrderItems])
        await this.setStock(stock)

        orders[orderIndex].total = total
      }

      const phoneAsString = updates.customer_phone ? String(updates.customer_phone).trim() : currentOrder.customer_phone
      if (updates.customer_phone && !phoneAsString) {
        throw new Error('Customer phone number is required')
      }

      orders[orderIndex] = {
        ...currentOrder,
        customer_name: updates.customer_name ?? currentOrder.customer_name,
        customer_phone: phoneAsString,
        canal: updates.canal ?? currentOrder.canal,
        metodo_pago: updates.metodo_pago ?? currentOrder.metodo_pago,
        notas: updates.notas !== undefined ? updates.notas : currentOrder.notas,
        updated_at: new Date().toISOString()
      }

      await this.setOrders(orders)

      const orderWithItems = await this.fetchOrders()
      const found = orderWithItems.find(o => o.id === orderId)
      if (!found) {
        throw new Error(`Order with id ${orderId} not found after update`)
      }
      return found
    } catch (error) {
      console.error('Error updating order:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to update order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async addProduct(product: Omit<Product, 'id'>, initialStock: number): Promise<ProductWithStock> {
    try {
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
    } catch (error) {
      console.error('Error adding product:', error)
      throw new Error(`Failed to add product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>, locationId?: number): Promise<ProductWithStock> {
    try {
      const { stock_disponible, ...productData } = product
      // V2.0: locationId se ignora en modo local, solo aplicable en modo API
      return this.addProduct(productData as Omit<Product, 'id'>, stock_disponible)
    } catch (error) {
      console.error('Error creating product:', error)
      throw new Error(`Failed to create product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    try {
      const stock = await this.getStock()
      const stockEntry = stock.find(s => s.product_id === productId)

      if (!stockEntry) {
        throw new Error(`Stock entry for product ${productId} not found`)
      }

      stockEntry.cantidad_disponible = cantidad
      await this.setStock(stock)
    } catch (error) {
      console.error('Error updating stock:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to update stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateProduct(productId: number, updates: Partial<ProductWithStock>): Promise<ProductWithStock> {
    try {
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
    } catch (error) {
      console.error('Error updating product:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to update product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteProduct(productId: number): Promise<void> {
    try {
      const [products, stock, orderItems] = await Promise.all([
        this.loadProducts(),
        this.getStock(),
        this.getOrderItems()
      ])

      // Verificar si el producto está en alguna orden
      const isInOrder = orderItems.some(item => item.product_id === productId)
      if (isInOrder) {
        throw new Error('No se puede eliminar el producto porque está referenciado en órdenes existentes')
      }

      // Eliminar producto y su stock
      const updatedProducts = products.filter(p => p.id !== productId)
      const updatedStock = stock.filter(s => s.product_id !== productId)

      await Promise.all([
        this.setProducts(updatedProducts),
        this.setStock(updatedStock)
      ])
    } catch (error) {
      console.error('Error deleting product:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to delete product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteOrder(orderId: number): Promise<void> {
    try {
      const [orders, orderItems, stock] = await Promise.all([
        this.loadOrders(),
        this.getOrderItems(),
        this.getStock()
      ])

      // Encontrar la orden
      const order = orders.find(o => o.id === orderId)
      if (!order) {
        throw new Error('Orden no encontrada')
      }

      // Reponer stock de los productos
      const itemsToRestore = orderItems.filter(item => item.order_id === orderId)
      const updatedStock = [...stock]
      
      for (const item of itemsToRestore) {
        const stockItem = updatedStock.find(s => s.product_id === item.product_id)
        if (stockItem) {
          stockItem.cantidad_disponible += item.cantidad
        }
      }

      // Eliminar orden y sus items
      const updatedOrders = orders.filter(o => o.id !== orderId)
      const updatedOrderItems = orderItems.filter(item => item.order_id !== orderId)

      await Promise.all([
        this.setOrders(updatedOrders),
        this.setOrderItems(updatedOrderItems),
        this.setStock(updatedStock)
      ])
    } catch (error) {
      console.error('Error deleting order:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to delete order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[]): Promise<ProductWithStock[]> {
    try {
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
    } catch (error) {
      console.error('Error bulk creating products:', error)
      throw new Error(`Failed to bulk create products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }
}

export const inventoryService = new InventoryService()
