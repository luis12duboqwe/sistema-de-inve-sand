import type {
  Profile,
  Product,
  Stock,
  Order,
  OrderItem,
  ProductWithStock,
  OrderWithItems,
  CreateOrderRequest,
  Location,
  SalesProfile,
  Supplier,
  CreateStockTransferRequest,
  StockByLocation,
  StockTransfer,
  StockHistory,
  ProductIMEI,
  TradeIn
} from './types'
import { getKV } from './kvStorage'

const STORAGE_KEYS = {
  PROFILES: 'inventory-profiles',
  PRODUCTS: 'inventory-products',
  STOCK: 'inventory-stock',
  ORDERS: 'inventory-orders',
  ORDER_ITEMS: 'inventory-order-items',
  TRADE_INS: 'inventory-trade-ins', // V2.0
  LOCATIONS: 'inventory-locations',          // V2.0
  SALES_PROFILES: 'inventory-sales-profiles', // V2.0
  SUPPLIERS: 'inventory-suppliers',           // V2.0
  STOCK_TRANSFERS: 'inventory-stock-transfers', // V2.0
  STOCK_HISTORY: 'inventory-stock-history',   // V2.0
  PRODUCT_IMEIS: 'inventory-product-imeis'    // V2.0
}

export class InventoryService {
  private async loadStockHistory(): Promise<StockHistory[]> {
    try {
      const kv = getKV()
      const data = await kv.get<StockHistory[]>(STORAGE_KEYS.STOCK_HISTORY)
      return data || []
    } catch (error) {
      console.error('Error loading stock history:', error)
      return []
    }
  }

  private async setStockHistory(history: StockHistory[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.STOCK_HISTORY, history)
    } catch (error) {
      console.error('Error saving stock history:', error)
    }
  }

  private async loadProductIMEIs(): Promise<ProductIMEI[]> {
    try {
      const kv = getKV()
      const data = await kv.get<ProductIMEI[]>(STORAGE_KEYS.PRODUCT_IMEIS)
      return data || []
    } catch (error) {
      console.error('Error loading product IMEIs:', error)
      return []
    }
  }

  private async setProductIMEIs(imeis: ProductIMEI[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.PRODUCT_IMEIS, imeis)
    } catch (error) {
      console.error('Error saving product IMEIs:', error)
    }
  }

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

  private async loadTradeIns(): Promise<TradeIn[]> {
    try {
      const kv = getKV()
      const data = await kv.get<TradeIn[]>(STORAGE_KEYS.TRADE_INS)
      return data || []
    } catch (error) {
      console.error('Error loading trade-ins:', error)
      throw new Error(`Failed to load trade-ins: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async setTradeIns(tradeIns: TradeIn[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.TRADE_INS, tradeIns)
    } catch (error) {
      console.error('Error saving trade-ins:', error)
      throw new Error(`Failed to save trade-ins: ${error instanceof Error ? error.message : 'Unknown error'}`)
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
      const [products, stock, profiles, locations] = await Promise.all([
        this.loadProducts(),
        this.getStock(),
        this.loadProfiles(),
        this.loadLocations()
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

      const productsWithStock: ProductWithStock[] = filtered.map(product => {
        const stockEntries = stock.filter(s => s.product_id === product.id)

        const stockItems = stockEntries.map(s => {
          const location = s.location_id ? locations.find(l => l.id === s.location_id) : undefined
          const cantidad_reservada = s.cantidad_reservada || 0
          const stock_libre = (s.cantidad_disponible || 0) - cantidad_reservada
          return {
            ...s,
            location_id: s.location_id || 0,
            cantidad_reservada,
            stock_libre: Math.max(stock_libre, 0),
            location
          }
        })

        const stockTotal = stockItems.reduce((acc, s) => acc + (s.stock_libre ?? 0), 0)

        return {
          ...product,
          stock_disponible: stockTotal,
          stock_items: stockItems
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
      const [profiles, products, stock, orders, orderItems, salesProfiles, locations, stockHistory, productIMEIs, tradeIns] = await Promise.all([
        this.loadProfiles(),
        this.loadProducts(),
        this.getStock(),
        this.loadOrders(),
        this.getOrderItems(),
        this.loadSalesProfiles(),
        this.loadLocations(),
        this.loadStockHistory(),
        this.loadProductIMEIs(),
        this.loadTradeIns()
      ])

      if (!request.source_location_id) {
        throw new Error('source_location_id is required in V2.0')
      }

      // 🔒 BUG #4 FIX: Validar ubicación existente
      const existingLocation = locations.find(loc => loc.id === request.source_location_id)
      if (!existingLocation) {
        throw new Error(`Location with ID ${request.source_location_id} not found.`)
      }

      // V2.0: Permitir sales_profile_slug; mantener profile_slug para compatibilidad
      const profile = request.profile_slug ? profiles.find(p => p.slug === request.profile_slug) : undefined
      const salesProfile = request.sales_profile_slug
        ? salesProfiles.find(sp => sp.slug === request.sales_profile_slug)
        : undefined

      if (!salesProfile && !profile) {
        throw new Error('Debe proporcionar sales_profile_slug (V2.0) o profile_slug (legacy)')
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

        const stockEntry = stock.find(
          s => s.product_id === item.product_id && s.location_id === request.source_location_id
        )

        if (!stockEntry) {
          throw new Error(`No stock found for product "${product.nombre}" at location ${request.source_location_id}`)
        }

        const reservado = stockEntry.cantidad_reservada || 0
        const stockLibre = stockEntry.cantidad_disponible - reservado
        if (stockLibre < item.cantidad) {
          throw new Error(
            `Insufficient stock for product "${product.nombre}" at location ${request.source_location_id}. Free: ${stockLibre}, Reserved: ${reservado}, Requested: ${item.cantidad}`
          )
        }
      }

      let total = 0
      const newOrderItems: OrderItem[] = []
      const newOrderId = Math.max(0, ...orders.map(o => o.id)) + 1
      const newStockHistory: StockHistory[] = []
      const updatedIMEIs: ProductIMEI[] = [...productIMEIs]

      for (const item of request.items) {
        const product = products.find(p => p.id === item.product_id)!
        total += product.precio * item.cantidad

        const stockEntry = stock.find(
          s => s.product_id === item.product_id && s.location_id === request.source_location_id
        )!
        
        const stockAnterior = stockEntry.cantidad_disponible
        stockEntry.cantidad_disponible -= item.cantidad
        const stockNuevo = stockEntry.cantidad_disponible

        if (stockEntry.cantidad_reservada && stockEntry.cantidad_disponible < stockEntry.cantidad_reservada) {
          throw new Error(
            `Critical stock error for product ${item.product_id}: available below reserved after sale`
          )
        }

        // V2.0: Handle IMEIs
        const productHasIMEIs = updatedIMEIs.some(pi => pi.product_id === item.product_id)
        if (productHasIMEIs) {
          const availableIMEIs = updatedIMEIs.filter(
            pi => pi.product_id === item.product_id && 
                  pi.location_id === request.source_location_id && 
                  !pi.vendido
          )

          if (availableIMEIs.length < item.cantidad) {
             throw new Error(`Insufficient IMEIs for product ${product.nombre}. Available: ${availableIMEIs.length}, Requested: ${item.cantidad}`)
          }

          // Mark IMEIs as sold
          for (let i = 0; i < item.cantidad; i++) {
            const imei = availableIMEIs[i]
            const imeiIndex = updatedIMEIs.findIndex(pi => pi.id === imei.id)
            if (imeiIndex !== -1) {
              updatedIMEIs[imeiIndex] = {
                ...updatedIMEIs[imeiIndex],
                vendido: true,
                order_id: newOrderId
              }
            }
          }
        }

        // V2.0: Add Stock History
        newStockHistory.push({
          id: Math.max(0, ...stockHistory.map(h => h.id), ...newStockHistory.map(h => h.id)) + 1,
          product_id: item.product_id,
          tipo_cambio: 'venta',
          cantidad: -item.cantidad,
          stock_anterior: stockAnterior,
          stock_nuevo: stockNuevo,
          referencia_id: newOrderId,
          referencia_tipo: 'order',
          notas: `Venta Local - Cliente: ${request.customer_name}`,
          usuario: salesProfile?.name || profile?.name || 'Sistema Local',
          created_at: new Date().toISOString()
        })

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

      // Calculate trade-in total
      let tradeInTotal = 0
      const newTradeIns: TradeIn[] = []
      if (request.trade_ins) {
        for (const tradeIn of request.trade_ins) {
          tradeInTotal += Number(tradeIn.valor_estimado) || 0
          newTradeIns.push({
            ...tradeIn,
            id: Math.max(0, ...tradeIns.map(t => t.id || 0), ...newTradeIns.map(t => t.id || 0)) + 1,
            order_id: newOrderId,
            created_at: new Date().toISOString()
          })
        }
      }

      total = Math.max(0, total - tradeInTotal)

      const newOrder: Order = {
        id: newOrderId,
        profile_id: profile?.id,
        sales_profile_id: salesProfile?.id,
        source_location_id: request.source_location_id,
        customer_name: request.customer_name,
        customer_phone: phoneAsString,
        canal: request.canal,
        metodo_pago: request.metodo_pago,
        total,
        estado: 'pendiente',
        created_at: new Date().toISOString(),
        notas: request.notas,
        updated_at: new Date().toISOString(),
        trade_ins: newTradeIns
      }

      await this.setStock(stock)
      await this.setOrders([...orders, newOrder])
      await this.setOrderItems([...orderItems, ...newOrderItems])
      await this.setStockHistory([...stockHistory, ...newStockHistory])
      await this.setProductIMEIs(updatedIMEIs)
      await this.setTradeIns([...tradeIns, ...newTradeIns])

      const orderWithItems: OrderWithItems = {
        ...newOrder,
        items: newOrderItems.map(oi => ({
          ...oi,
          product: products.find(p => p.id === oi.product_id)
        })),
        trade_ins: newTradeIns
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
      const [orders, orderItems, products, profiles, salesProfiles] = await Promise.all([
        this.loadOrders(),
        this.getOrderItems(),
        this.loadProducts(),
        this.loadProfiles(),
        this.loadSalesProfiles()
      ])

      let filtered = orders

      if (salesProfileSlug) {
        const salesProfile = salesProfiles.find(sp => sp.slug === salesProfileSlug)
        if (salesProfile) {
          filtered = filtered.filter(o => o.sales_profile_id === salesProfile.id)
        } else {
          filtered = []
        }
      }

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
      const locationId = currentOrder.source_location_id
      if (!locationId) {
        throw new Error('Order does not have a source_location_id; cannot update stock by location')
      }

      if (updates.items) {
        // Devolver stock de los items actuales en la ubicación de origen
        for (const item of currentItems) {
          const stockEntry = stock.find(s => s.product_id === item.product_id && s.location_id === locationId)
          if (!stockEntry) {
            throw new Error(`Stock record not found for product ${item.product_id} at location ${locationId} while restoring`)  
          }
          stockEntry.cantidad_disponible += item.cantidad
        }

        // Validar stock libre por ubicación para los nuevos items
        for (const item of updates.items) {
          const product = products.find(p => p.id === item.product_id && p.activo)
          if (!product) {
            throw new Error(`Product with id ${item.product_id} not found or inactive`)
          }

          const stockEntry = stock.find(s => s.product_id === item.product_id && s.location_id === locationId)
          if (!stockEntry) {
            throw new Error(`No stock found for product "${product.nombre}" at location ${locationId}`)
          }

          const reservado = stockEntry.cantidad_reservada || 0
          const stockLibre = stockEntry.cantidad_disponible - reservado
          if (stockLibre < item.cantidad) {
            throw new Error(
              `Insufficient stock for product "${product.nombre}" at location ${locationId}. Free: ${stockLibre}, Reserved: ${reservado}, Requested: ${item.cantidad}`
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

          const stockEntry = stock.find(s => s.product_id === item.product_id && s.location_id === locationId)
          if (!stockEntry) {
            throw new Error(`Stock entry for product ${item.product_id} at location ${locationId} not found`)
          }
          stockEntry.cantidad_disponible -= item.cantidad
          if (stockEntry.cantidad_reservada && stockEntry.cantidad_disponible < stockEntry.cantidad_reservada) {
            throw new Error(`Stock for product ${item.product_id} at location ${locationId} cannot fall below reserved (${stockEntry.cantidad_reservada})`)
          }

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

  async addProduct(product: Omit<Product, 'id'>, initialStock: number, locationId?: number): Promise<ProductWithStock> {
    try {
      const [products, stock, locations] = await Promise.all([
        this.loadProducts(),
        this.getStock(),
        this.loadLocations()
      ])

      if (!locationId) {
        throw new Error('locationId is required to add products with stock in V2.0 local mode')
      }

      const locationExists = locations.some(l => l.id === locationId)
      if (!locationExists) {
        throw new Error(`Location ${locationId} not found; cannot assign initial stock`)
      }

      const newProduct: Product = {
        ...product,
        moneda: 'Lps', // Enforce Lps
        id: Math.max(0, ...products.map(p => p.id)) + 1
      }

      const newStock: Stock = {
        id: Math.max(0, ...stock.map(s => s.id)) + 1,
        product_id: newProduct.id,
        location_id: locationId,
        cantidad_disponible: initialStock,
        cantidad_reservada: 0
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
      return this.addProduct(productData as Omit<Product, 'id'>, stock_disponible, locationId)
    } catch (error) {
      console.error('Error creating product:', error)
      throw new Error(`Failed to create product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateStock(productId: number, cantidad: number, locationId: number): Promise<void> {
    try {
      // 🔒 Validar cantidad >= 0 (Bug #29 fix)
      if (cantidad < 0) {
        throw new Error('Stock no puede ser negativo')
      }

      if (!locationId) {
        throw new Error('locationId is required to update stock by location (V2.0)')
      }

      const [stock, locations] = await Promise.all([
        this.getStock(),
        this.loadLocations()
      ])

      const locationExists = locations.some(l => l.id === locationId)
      if (!locationExists) {
        throw new Error(`Location ${locationId} not found; cannot update stock`)
      }

      let stockEntry = stock.find(s => s.product_id === productId && s.location_id === locationId)

      if (!stockEntry) {
        // Crear registro de stock por ubicación si no existe aún
        stockEntry = {
          id: Math.max(0, ...stock.map(s => s.id)) + 1,
          product_id: productId,
          location_id: locationId,
          cantidad_disponible: 0,
          cantidad_reservada: 0
        }
        stock.push(stockEntry)
      }

      stockEntry.cantidad_disponible = cantidad
      const reservado = stockEntry.cantidad_reservada || 0
      if (stockEntry.cantidad_disponible < reservado) {
        throw new Error(
          `Stock for product ${productId} at location ${locationId} cannot be below reserved (${reservado})`
        )
      }
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
        const stockList = await this.getStock()
        const targetStock = stockList.find(s => s.product_id === productId)
        if (!targetStock || !targetStock.location_id) {
          throw new Error('No stock record found for this product. Use updateStock with a valid location first.')
        }
        await this.updateStock(productId, stock_disponible, targetStock.location_id)
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

      const order = orders.find(o => o.id === orderId)
      if (!order) {
        throw new Error('Orden no encontrada')
      }

      const locationId = order.source_location_id
      if (!locationId) {
        throw new Error('Orden sin source_location_id; no se puede reponer stock por ubicación')
      }

      const itemsToRestore = orderItems.filter(item => item.order_id === orderId)
      const updatedStock = [...stock]
      
      for (const item of itemsToRestore) {
        const stockItem = updatedStock.find(s => s.product_id === item.product_id && s.location_id === locationId)
        if (!stockItem) {
          throw new Error(`No se encontró stock para el producto ${item.product_id} en la ubicación ${locationId} al eliminar la orden`)
        }
        stockItem.cantidad_disponible += item.cantidad
      }

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

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[], locationId?: number): Promise<ProductWithStock[]> {
    try {
      const [products, stock, locations] = await Promise.all([
        this.loadProducts(),
        this.getStock(),
        this.loadLocations()
      ])

      if (!locationId) {
        throw new Error('locationId es obligatorio para carga masiva en modo local V2.0')
      }

      const locationExists = locations.some(l => l.id === locationId)
      if (!locationExists) {
        throw new Error(`Ubicación ${locationId} no encontrada; no se puede asignar stock inicial`)
      }

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
          location_id: locationId,
          cantidad_disponible: stock_disponible || 0,
          cantidad_reservada: 0
        }

        newProducts.push(newProduct)
        newStockEntries.push(newStockEntry)

        createdProducts.push({
          ...newProduct,
          stock_disponible: newStockEntry.cantidad_disponible,
          stock_items: [{
            id: newStockEntry.id,
            product_id: newProduct.id,
            location_id: locationId,
            cantidad_disponible: newStockEntry.cantidad_disponible,
            cantidad_reservada: 0,
            stock_libre: newStockEntry.cantidad_disponible,
            location: locations.find(l => l.id === locationId)
          }]
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

  async getStockByLocation(productId: number): Promise<StockByLocation[]> {
    try {
      const [stock, locations] = await Promise.all([
        this.getStock(),
        this.loadLocations()
      ])

      const productStock = stock.filter(s => s.product_id === productId)
      
      return productStock.map(s => {
        const location = locations.find(l => l.id === s.location_id)
        return {
          id: s.id,
          product_id: s.product_id,
          location_id: s.location_id!,
          cantidad_disponible: s.cantidad_disponible,
          cantidad_reservada: s.cantidad_reservada || 0,
          stock_libre: s.cantidad_disponible - (s.cantidad_reservada || 0),
          location
        }
      })
    } catch (error) {
      console.error('Error getting stock by location:', error)
      throw new Error(`Failed to get stock by location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // ============================================================================
  // V2.0: LOCATIONS (Ubicaciones)
  // ============================================================================

  private async loadLocations(): Promise<Location[]> {
    try {
      const kv = getKV()
      const data = await kv.get<Location[]>(STORAGE_KEYS.LOCATIONS)
      console.log('📂 Cargando ubicaciones desde KV:', data?.length || 0, 'ubicaciones')
      return data || []
    } catch (error) {
      console.error('❌ Error loading locations:', error)
      return []
    }
  }

  private async setLocations(locations: Location[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.LOCATIONS, locations)
    } catch (error) {
      console.error('Error saving locations:', error)
      throw new Error(`Failed to save locations: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getLocations(): Promise<Location[]> {
    return this.loadLocations()
  }

  async getLocation(id: number): Promise<Location> {
    const locations = await this.loadLocations()
    const location = locations.find(l => l.id === id)
    if (!location) throw new Error(`Location ${id} not found`)
    return location
  }

  async createLocation(location: Omit<Location, 'id' | 'created_at' | 'updated_at'>): Promise<Location> {
    try {
      const locations = await this.loadLocations()
      const nextId = locations.length > 0 ? Math.max(...locations.map(l => l.id)) + 1 : 1
      
      const now = new Date().toISOString()
      const newLocation: Location = {
        ...location,
        id: nextId,
        created_at: now,
        updated_at: now
      }

      const updatedLocations = [...locations, newLocation]
      console.log('💾 Guardando ubicación en localStorage:', newLocation)
      console.log('📍 Total ubicaciones:', updatedLocations.length)
      
      await this.setLocations(updatedLocations)
      
      // Verificar que se guardó
      const saved = await this.loadLocations()
      console.log('✅ Verificación - Ubicaciones guardadas:', saved.length)
      
      return newLocation
    } catch (error) {
      console.error('❌ Error creating location:', error)
      throw new Error(`Failed to create location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateLocation(id: number, updates: Partial<Location>): Promise<Location> {
    try {
      const locations = await this.loadLocations()
      const index = locations.findIndex(l => l.id === id)
      
      if (index === -1) {
        throw new Error(`Location with ID ${id} not found`)
      }

      const updatedLocation: Location = {
        ...locations[index],
        ...updates,
        id, // No permitir cambiar el ID
        updated_at: new Date().toISOString()
      }

      locations[index] = updatedLocation
      await this.setLocations(locations)
      return updatedLocation
    } catch (error) {
      console.error('Error updating location:', error)
      throw new Error(`Failed to update location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteLocation(id: number): Promise<void> {
    try {
      const locations = await this.loadLocations()
      const filtered = locations.filter(l => l.id !== id)
      await this.setLocations(filtered)
    } catch (error) {
      console.error('Error deleting location:', error)
      throw new Error(`Failed to delete location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // ============================================================================
  // V2.0: STOCK TRANSFERS
  // ============================================================================

  private async loadStockTransfers(): Promise<StockTransfer[]> {
    try {
      const kv = getKV()
      const data = await kv.get<StockTransfer[]>(STORAGE_KEYS.STOCK_TRANSFERS)
      return data || []
    } catch (error) {
      console.error('Error loading stock transfers:', error)
      return []
    }
  }

  private async setStockTransfers(transfers: StockTransfer[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.STOCK_TRANSFERS, transfers)
    } catch (error) {
      console.error('Error saving stock transfers:', error)
      throw new Error(`Failed to save stock transfers: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createStockTransfer(request: CreateStockTransferRequest): Promise<StockTransfer> {
    try {
      const [products, stock, locations, transfers] = await Promise.all([
        this.loadProducts(),
        this.getStock(),
        this.loadLocations(),
        this.loadStockTransfers()
      ])

      const product = products.find(p => p.id === request.product_id)
      if (!product) throw new Error(`Product ${request.product_id} not found`)

      const fromLocation = locations.find(l => l.id === request.from_location_id)
      if (!fromLocation) throw new Error(`Source location ${request.from_location_id} not found`)

      const toLocation = locations.find(l => l.id === request.to_location_id)
      if (!toLocation) throw new Error(`Destination location ${request.to_location_id} not found`)

      const stockEntry = stock.find(s => s.product_id === request.product_id && s.location_id === request.from_location_id)
      if (!stockEntry) throw new Error(`No stock entry for product ${request.product_id} at location ${request.from_location_id}`)

      const available = stockEntry.cantidad_disponible - (stockEntry.cantidad_reservada || 0)
      if (available < request.cantidad) {
        throw new Error(`Insufficient stock. Available: ${available}, Requested: ${request.cantidad}`)
      }

      // Reserve stock
      stockEntry.cantidad_reservada = (stockEntry.cantidad_reservada || 0) + request.cantidad
      
      // Reserve IMEIs (V2.0)
      const productIMEIs = await this.loadProductIMEIs()
      let imeisToReserve: ProductIMEI[] = []

      if (request.imeis && request.imeis.length > 0) {
        // Validate specific IMEIs
        if (request.imeis.length !== request.cantidad) {
          throw new Error(`Mismatch between quantity (${request.cantidad}) and provided IMEIs (${request.imeis.length})`)
        }
        
        imeisToReserve = productIMEIs.filter(
          pi => pi.product_id === request.product_id && 
                pi.location_id === request.from_location_id && 
                !pi.vendido &&
                !pi.transfer_id &&
                request.imeis!.includes(pi.imei)
        )

        if (imeisToReserve.length !== request.cantidad) {
           throw new Error(`Some requested IMEIs are not available at source location`)
        }
      } else {
        // Auto-select available IMEIs
        imeisToReserve = productIMEIs.filter(
          pi => pi.product_id === request.product_id && 
                pi.location_id === request.from_location_id && 
                !pi.vendido &&
                !pi.transfer_id
        ).slice(0, request.cantidad)
      }

      // Note: In local mode we don't enforce IMEI reservation if not enough found (legacy behavior),
      // but if found, we reserve them.
      
      const newTransfer: StockTransfer = {
        id: Math.max(0, ...transfers.map(t => t.id)) + 1,
        product_id: request.product_id,
        from_location_id: request.from_location_id,
        to_location_id: request.to_location_id,
        cantidad: request.cantidad,
        notas: request.notas,
        estado: 'pendiente',
        created_at: new Date().toISOString(),
        created_by: request.created_by,
        product: {
            id: product.id,
            nombre: product.nombre,
            sku: product.sku
        },
        from_location_name: fromLocation.nombre,
        to_location_name: toLocation.nombre
      }

      // Assign transfer_id to reserved IMEIs
      for (const imei of imeisToReserve) {
        imei.transfer_id = newTransfer.id
      }

      await Promise.all([
        this.setStock(stock),
        this.setStockTransfers([...transfers, newTransfer]),
        this.setProductIMEIs(productIMEIs)
      ])
      
      return newTransfer
    } catch (error) {
      console.error('Error creating stock transfer:', error)
      throw new Error(`Failed to create stock transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listStockTransfers(filters?: {
    product_id?: number
    from_location_id?: number
    to_location_id?: number
    location_id?: number
    estado?: 'pendiente' | 'confirmada' | 'rechazada' | 'cancelada'
  }): Promise<StockTransfer[]> {
    try {
      const transfers = await this.loadStockTransfers()
      
      return transfers.filter(t => {
        if (filters?.product_id && t.product_id !== filters.product_id) return false
        if (filters?.from_location_id && t.from_location_id !== filters.from_location_id) return false
        if (filters?.to_location_id && t.to_location_id !== filters.to_location_id) return false
        if (filters?.location_id && t.from_location_id !== filters.location_id && t.to_location_id !== filters.location_id) return false
        if (filters?.estado && t.estado !== filters.estado) return false
        return true
      }).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } catch (error) {
      console.error('Error listing stock transfers:', error)
      return []
    }
  }

  async confirmStockTransfer(id: number, confirmedBy: string): Promise<StockTransfer> {
    try {
      const [transfers, stock, productIMEIs] = await Promise.all([
        this.loadStockTransfers(),
        this.getStock(),
        this.loadProductIMEIs()
      ])

      const transferIndex = transfers.findIndex(t => t.id === id)
      if (transferIndex === -1) throw new Error(`Transfer ${id} not found`)
      
      const transfer = transfers[transferIndex]
      if (transfer.estado !== 'pendiente') throw new Error(`Transfer ${id} is not pending`)

      // Update stock
      const fromStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.from_location_id)
      if (!fromStock) throw new Error(`Source stock not found`)
      
      // Release reservation and decrease stock
      fromStock.cantidad_reservada = (fromStock.cantidad_reservada || 0) - transfer.cantidad
      fromStock.cantidad_disponible -= transfer.cantidad

      // Increase destination stock
      let toStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.to_location_id)
      if (!toStock) {
        toStock = {
          id: Math.max(0, ...stock.map(s => s.id)) + 1,
          product_id: transfer.product_id,
          location_id: transfer.to_location_id,
          cantidad_disponible: 0,
          cantidad_reservada: 0
        }
        stock.push(toStock)
      }
      toStock.cantidad_disponible += transfer.cantidad

      // Move IMEIs (V2.0 Fix with transfer_id)
      let imeisToMove = productIMEIs.filter(
        pi => pi.transfer_id === transfer.id
      )

      // Fallback for legacy transfers without transfer_id
      if (imeisToMove.length === 0) {
        imeisToMove = productIMEIs.filter(
          pi => pi.product_id === transfer.product_id && 
                pi.location_id === transfer.from_location_id && 
                !pi.vendido &&
                !pi.transfer_id
        ).slice(0, transfer.cantidad)
      }

      for (const imei of imeisToMove) {
        imei.location_id = transfer.to_location_id
        imei.transfer_id = undefined // Clear transfer_id
      }

      // Update transfer status
      const updatedTransfer = {
        ...transfer,
        estado: 'confirmada' as const,
        confirmed_at: new Date().toISOString(),
        confirmed_by: confirmedBy
      }
      transfers[transferIndex] = updatedTransfer

      await Promise.all([
        this.setStock(stock),
        this.setStockTransfers(transfers),
        this.setProductIMEIs(productIMEIs)
      ])

      return updatedTransfer
    } catch (error) {
      console.error('Error confirming transfer:', error)
      throw new Error(`Failed to confirm transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async rejectStockTransfer(id: number, rejectedBy: string, rejectionReason?: string): Promise<StockTransfer> {
    try {
      const [transfers, stock, productIMEIs] = await Promise.all([
        this.loadStockTransfers(),
        this.getStock(),
        this.loadProductIMEIs()
      ])

      const transferIndex = transfers.findIndex(t => t.id === id)
      if (transferIndex === -1) throw new Error(`Transfer ${id} not found`)
      
      const transfer = transfers[transferIndex]
      if (transfer.estado !== 'pendiente') throw new Error(`Transfer ${id} is not pending`)

      // Release reservation
      const fromStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.from_location_id)
      if (fromStock) {
        fromStock.cantidad_reservada = Math.max(0, (fromStock.cantidad_reservada || 0) - transfer.cantidad)
      }

      // Release IMEIs
      const imeisReserved = productIMEIs.filter(pi => pi.transfer_id === id)
      for (const imei of imeisReserved) {
        imei.transfer_id = undefined
      }

      // Update transfer status
      const updatedTransfer = {
        ...transfer,
        estado: 'rechazada' as const,
        rejection_reason: rejectionReason,
        confirmed_by: rejectedBy // Using confirmed_by field for rejecter too
      }
      transfers[transferIndex] = updatedTransfer

      await Promise.all([
        this.setStock(stock),
        this.setStockTransfers(transfers),
        this.setProductIMEIs(productIMEIs)
      ])

      return updatedTransfer
    } catch (error) {
      console.error('Error rejecting transfer:', error)
      throw new Error(`Failed to reject transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async cancelStockTransfer(id: number): Promise<void> {
    try {
      const [transfers, stock, productIMEIs] = await Promise.all([
        this.loadStockTransfers(),
        this.getStock(),
        this.loadProductIMEIs()
      ])

      const transferIndex = transfers.findIndex(t => t.id === id)
      if (transferIndex === -1) throw new Error(`Transfer ${id} not found`)
      
      const transfer = transfers[transferIndex]
      if (transfer.estado !== 'pendiente') throw new Error(`Transfer ${id} is not pending`)

      // Release reservation
      const fromStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.from_location_id)
      if (fromStock) {
        fromStock.cantidad_reservada = Math.max(0, (fromStock.cantidad_reservada || 0) - transfer.cantidad)
      }

      // Release IMEIs
      const imeisReserved = productIMEIs.filter(pi => pi.transfer_id === id)
      for (const imei of imeisReserved) {
        imei.transfer_id = undefined
      }

      // Update transfer status
      const updatedTransfer = {
        ...transfer,
        estado: 'cancelada' as const
      }
      transfers[transferIndex] = updatedTransfer

      await Promise.all([
        this.setStock(stock),
        this.setStockTransfers(transfers),
        this.setProductIMEIs(productIMEIs)
      ])
    } catch (error) {
      console.error('Error canceling transfer:', error)
      throw new Error(`Failed to cancel transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // ============================================================================
  // V2.0: SUPPLIERS
  // ============================================================================

  private async loadSuppliers(): Promise<Supplier[]> {
    try {
      const kv = getKV()
      const data = await kv.get<Supplier[]>(STORAGE_KEYS.SUPPLIERS)
      return data || []
    } catch (error) {
      console.error('Error loading suppliers:', error)
      return []
    }
  }

  async listSuppliers(includeInactive = false): Promise<Supplier[]> {
    const suppliers = await this.loadSuppliers()
    if (includeInactive) return suppliers
    return suppliers.filter(s => s.activo)
  }

  // ============================================================================
  // V2.0: SALES PROFILES (Perfiles de Ventas)
  // ============================================================================

  private async loadSalesProfiles(): Promise<SalesProfile[]> {
    try {
      const kv = getKV()
      const data = await kv.get<SalesProfile[]>(STORAGE_KEYS.SALES_PROFILES)
      return data || []
    } catch (error) {
      console.error('Error loading sales profiles:', error)
      return []
    }
  }

  private async setSalesProfiles(profiles: SalesProfile[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.SALES_PROFILES, profiles)
    } catch (error) {
      console.error('Error saving sales profiles:', error)
      throw new Error(`Failed to save sales profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getSalesProfiles(): Promise<SalesProfile[]> {
    return this.loadSalesProfiles()
  }

  async getSalesProfile(id: number): Promise<SalesProfile> {
    const profiles = await this.loadSalesProfiles()
    const profile = profiles.find(p => p.id === id)
    if (!profile) throw new Error(`Sales profile ${id} not found`)
    return profile
  }

  async createSalesProfile(profile: Omit<SalesProfile, 'id' | 'created_at' | 'updated_at'>): Promise<SalesProfile> {
    try {
      const profiles = await this.loadSalesProfiles()
      const nextId = profiles.length > 0 ? Math.max(...profiles.map(p => p.id)) + 1 : 1
      
      const now = new Date().toISOString()
      const newProfile: SalesProfile = {
        ...profile,
        id: nextId,
        created_at: now,
        updated_at: now
      }

      await this.setSalesProfiles([...profiles, newProfile])
      return newProfile
    } catch (error) {
      console.error('Error creating sales profile:', error)
      throw new Error(`Failed to create sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateSalesProfile(id: number, updates: Partial<SalesProfile>): Promise<SalesProfile> {
    try {
      const profiles = await this.loadSalesProfiles()
      const index = profiles.findIndex(p => p.id === id)
      
      if (index === -1) {
        throw new Error(`Sales profile with ID ${id} not found`)
      }

      const updatedProfile: SalesProfile = {
        ...profiles[index],
        ...updates,
        id,
        updated_at: new Date().toISOString()
      }

      profiles[index] = updatedProfile
      await this.setSalesProfiles(profiles)
      return updatedProfile
    } catch (error) {
      console.error('Error updating sales profile:', error)
      throw new Error(`Failed to update sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteSalesProfile(id: number): Promise<void> {
    try {
      const profiles = await this.loadSalesProfiles()
      const filtered = profiles.filter(p => p.id !== id)
      await this.setSalesProfiles(filtered)
    } catch (error) {
      console.error('Error deleting sales profile:', error)
      throw new Error(`Failed to delete sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

}

export const inventoryService = new InventoryService()
