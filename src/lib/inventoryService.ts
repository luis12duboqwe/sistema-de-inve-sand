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
  TradeIn,
  CreateReturnRequest,
  Return,
  IMEIHistory,
  TrainingQueueItem,
  Customer,
  AIProfileConfig,
  Bank,
  FinancingOption,
  TradeInPolicy,
  WarrantyStatus,
  DashboardStats,
  SalesReport,
  InventoryAlert,
  StockSummaryByLocation,
  SalesSummaryByLocation,
  TopProductByLocationEntry,
  CustomerStats,
  CustomerHistory,
  OrderSummary,
  StockHistoryStats,
  StockHistoryCreateRequest,
  AIContextPayload,
  AIContextResponse,
  AIReplyPayload,
  AIReplyResponse,
  AIInteractionLogPayload,
  TrainingSubmissionPayload,
  FlagTrollResponse,
  PublicProduct,
  PublicCatalogFilters,
  PaginatedResponse,
  BusinessInsightsResponse,
  BusinessInsightTopSeller,
  BusinessInsightSlowMover,
  BusinessInsightStockAlert,
  BusinessInsightTrendPoint,
  AIStatusResponse,
  ForecastingAlertItem,
  Permission,
  Role,
  User,
  CreateUserRequest,
  SyncEventInput
} from './types'
import { generateAIForecasts, generateRestockAlerts, SalesForecast } from './aiForecasting'
import { getKV } from './kvStorage'
import { analyzePricing, analyzeInventory, analyzeCustomers } from './optimizationAnalytics'
import { buildBusinessInsightRecommendations } from './businessInsightsFallback'
import { syncJournal } from './syncJournal'

// Simple Async Lock to prevent race conditions in Local Mode
class AsyncLock {
  private promise: Promise<void> = Promise.resolve()

  async acquire(): Promise<() => void> {
    let release: () => void
    const nextPromise = new Promise<void>(resolve => {
      release = resolve
    })
    const previousPromise = this.promise
    this.promise = previousPromise.then(() => nextPromise)
    await previousPromise
    return release!
  }
}

const inventoryLock = new AsyncLock()
const MS_PER_DAY = 24 * 60 * 60 * 1000

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
  PRODUCT_IMEIS: 'inventory-product-imeis',   // V2.0
  RETURNS: 'inventory-returns',               // V2.0
  RETURN_ITEMS: 'inventory-return-items',     // V2.0
  IMEI_HISTORY: 'inventory-imei-history',      // V2.0
  TRAINING_QUEUE: 'inventory-training-queue', // V2.1
  CUSTOMERS: 'inventory-customers',           // V2.1
  AI_CONFIG: 'inventory-ai-config',           // V2.1
  BANKS: 'inventory-banks',                   // V2.1
  FINANCING_OPTIONS: 'inventory-financing-options', // V2.1
  TRADE_IN_POLICIES: 'inventory-trade-in-policies', // V2.1
  FAQS: 'inventory-faqs',                     // V2.1: FAQs local mode
  USERS: 'inventory-users',                   // V2.1: RBAC local mode
  ROLES: 'inventory-roles',                   // V2.1: RBAC local mode
  PERMISSIONS: 'inventory-permissions'        // V2.1: RBAC local mode
}

type PermissionSeedDefinition = {
  slug: string
  module: string
  description: string
}

type RoleSeedDefinition = {
  name: string
  description: string
  is_system_role: boolean
  permissionSlugs: string[]
}

const PERMISSION_SEED_DATA: PermissionSeedDefinition[] = [
  { slug: 'users:manage', module: 'usuarios', description: 'Administrar usuarios, roles y permisos' },
  { slug: 'inventory:read', module: 'inventario', description: 'Consultar el inventario y niveles de stock' },
  { slug: 'inventory:write', module: 'inventario', description: 'Crear o actualizar productos y existencias' },
  { slug: 'orders:read', module: 'ordenes', description: 'Ver órdenes y su progreso' },
  { slug: 'orders:write', module: 'ordenes', description: 'Crear, actualizar o cancelar órdenes' },
  { slug: 'settings:edit', module: 'configuracion', description: 'Cambiar la configuración avanzada de la app' }
]

const ROLE_SEED_DATA: RoleSeedDefinition[] = [
  {
    name: 'Super Admin',
    description: 'Control total del sistema en modo local',
    is_system_role: true,
    permissionSlugs: PERMISSION_SEED_DATA.map(permission => permission.slug)
  },
  {
    name: 'Admin',
    description: 'Gestiona inventario, órdenes y configuraciones básicas',
    is_system_role: true,
    permissionSlugs: ['inventory:read', 'inventory:write', 'orders:read', 'orders:write']
  },
  {
    name: 'Vendedor',
    description: 'Opera ventas y consulta inventario',
    is_system_role: true,
    permissionSlugs: ['inventory:read', 'orders:read']
  }
]

const DEFAULT_RBAC_USER = {
  username: 'admin',
  email: 'admin@local.dev',
  full_name: 'Administrador Local'
}

export class InventoryService {

  private async recordSyncEvent(event: SyncEventInput): Promise<void> {
    try {
      await syncJournal.recordEvent({
        ...event,
        origin: event.origin ?? 'local',
        metadata: {
          ...(event.metadata ?? {}),
          source: 'inventoryService'
        }
      })
    } catch (error) {
      console.warn('[InventoryService] No se pudo registrar evento de sincronización', event, error)
    }
  }

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

  private async loadIMEIHistory(): Promise<IMEIHistory[]> {
    try {
      const kv = getKV()
      const data = await kv.get<IMEIHistory[]>(STORAGE_KEYS.IMEI_HISTORY)
      return data || []
    } catch (error) {
      console.error('Error loading IMEI history:', error)
      return []
    }
  }

  private async setIMEIHistory(history: IMEIHistory[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.IMEI_HISTORY, history)
    } catch (error) {
      console.error('Error saving IMEI history:', error)
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

  private async loadOrdersWithItems(): Promise<Array<Order & { items: OrderItem[] }>> {
    const [orders, orderItems] = await Promise.all([
      this.loadOrders(),
      this.getOrderItems()
    ])

    const itemsByOrder = new Map<number, OrderItem[]>()
    for (const item of orderItems) {
      if (!itemsByOrder.has(item.order_id)) {
        itemsByOrder.set(item.order_id, [])
      }
      itemsByOrder.get(item.order_id)!.push(item)
    }

    return orders.map(order => ({
      ...order,
      items: itemsByOrder.get(order.id) || []
    }))
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

  private async ensureRbacSeeded(): Promise<void> {
    const release = await inventoryLock.acquire()
    try {
      const kv = getKV()
      let permissions = await kv.get<Permission[]>(STORAGE_KEYS.PERMISSIONS) || []
      if (!permissions.length) {
        permissions = PERMISSION_SEED_DATA.map((definition, index) => ({
          id: index + 1,
          slug: definition.slug,
          module: definition.module,
          description: definition.description
        }))
        await kv.set(STORAGE_KEYS.PERMISSIONS, permissions)
      }

      let roles = await kv.get<Role[]>(STORAGE_KEYS.ROLES) || []
      if (!roles.length) {
        roles = ROLE_SEED_DATA.map((definition, index) => ({
          id: index + 1,
          name: definition.name,
          description: definition.description,
          is_system_role: definition.is_system_role,
          permissions: definition.permissionSlugs
            .map(slug => permissions.find(permission => permission.slug === slug))
            .filter((permission): permission is Permission => Boolean(permission))
        }))
        await kv.set(STORAGE_KEYS.ROLES, roles)
      }

      let users = await kv.get<User[]>(STORAGE_KEYS.USERS) || []
      if (!users.length) {
        const now = new Date().toISOString()
        const adminRole = roles[0]
        users = [{
          id: 1,
          username: DEFAULT_RBAC_USER.username,
          email: DEFAULT_RBAC_USER.email,
          full_name: DEFAULT_RBAC_USER.full_name,
          is_active: true,
          is_superuser: true,
          role_id: adminRole?.id,
          role: adminRole,
          created_at: now,
          updated_at: now
        }]
        await kv.set(STORAGE_KEYS.USERS, users)
      }
    } finally {
      release()
    }
  }

  private async loadPermissions(): Promise<Permission[]> {
    try {
      const kv = getKV()
      return (await kv.get<Permission[]>(STORAGE_KEYS.PERMISSIONS)) || []
    } catch (error) {
      console.error('Error loading permissions:', error)
      return []
    }
  }

  private async setPermissions(permissions: Permission[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.PERMISSIONS, permissions)
    } catch (error) {
      console.error('Error saving permissions:', error)
      throw error
    }
  }

  private async loadRoles(): Promise<Role[]> {
    try {
      const kv = getKV()
      return (await kv.get<Role[]>(STORAGE_KEYS.ROLES)) || []
    } catch (error) {
      console.error('Error loading roles:', error)
      return []
    }
  }

  private async setRoles(roles: Role[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.ROLES, roles)
    } catch (error) {
      console.error('Error saving roles:', error)
      throw error
    }
  }

  private async loadUsers(): Promise<User[]> {
    try {
      const kv = getKV()
      return (await kv.get<User[]>(STORAGE_KEYS.USERS)) || []
    } catch (error) {
      console.error('Error loading users:', error)
      return []
    }
  }

  private async setUsers(users: User[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.USERS, users)
    } catch (error) {
      console.error('Error saving users:', error)
      throw error
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
      const [products, stock, , locations, imeis] = await Promise.all([
        this.loadProducts(),
        this.getStock(),
        this.loadProfiles(),
        this.loadLocations(),
        this.loadProductIMEIs()
      ])

      let filtered = includeInactive ? products : products.filter(p => p.activo)

      // V2.0 CHANGE: Products are global. Do not filter by profile_id even if slug is provided.
      // Keeping this commented out for reference or legacy fallback if absolutely needed.
      /*
      if (profileSlug) {
        const profile = profiles.find(pr => pr.slug === profileSlug)
        if (profile) {
          filtered = filtered.filter(p => p.profile_id === profile.id)
        }
      }
      */

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
        
        // V2.0: Attach available IMEIs
        const productImeis = imeis
          .filter(i => i.product_id === product.id && !i.vendido && !i.transfer_id)
          .map(i => i.imei)

        return {
          ...product,
          stock_disponible: stockTotal,
          stock_items: stockItems,
          imeis: productImeis.length > 0 ? productImeis : undefined
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

  async getAvailableIMEIs(productId: number, locationId: number): Promise<string[]> {
    try {
      const imeis = await this.loadProductIMEIs()
      return imeis
        .filter(i => i.product_id === productId && i.location_id === locationId && !i.vendido && !i.transfer_id)
        .map(i => i.imei)
    } catch (error) {
      console.error('Error fetching IMEIs locally:', error)
      return []
    }
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    const release = await inventoryLock.acquire()
    try {
      const [profiles, products, stock, orders, orderItems, salesProfiles, locations, stockHistory, productIMEIs, tradeIns, imeiHistory] = await Promise.all([
        this.loadProfiles(),
        this.loadProducts(),
        this.getStock(),
        this.loadOrders(),
        this.getOrderItems(),
        this.loadSalesProfiles(),
        this.loadLocations(),
        this.loadStockHistory(),
        this.loadProductIMEIs(),
        this.loadTradeIns(),
        this.loadIMEIHistory()
      ])

      if (!request.source_location_id) {
        throw new Error('source_location_id is required in V2.0')
      }

      // 🔒 BUG #4 FIX: Validar ubicación existente
      const existingLocation = locations.find(loc => loc.id === request.source_location_id)
      if (!existingLocation) {
        throw new Error(`Location with ID ${request.source_location_id} not found.`)
      }
      if (!existingLocation.activo) {
        throw new Error(`Location ${existingLocation.nombre} is inactive.`)
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
      
      // ✅ VALIDACIÓN DE TELÉFONO
      const phoneRegex = /^[0-9\s\-+()]{7,20}$/
      
      if (!phoneAsString) {
        throw new Error('El número de teléfono es requerido')
      }

      if (!phoneRegex.test(phoneAsString)) {
        throw new Error(
          `Teléfono inválido: "${phoneAsString}". ` +
          `Debe tener entre 7 y 20 caracteres (números, espacios, guiones, paréntesis, +)`
        )
      }
      
      const digitCount = (phoneAsString.match(/\d/g) || []).length
      if (digitCount < 7) {
        throw new Error(
          `Teléfono debe contener al menos 7 dígitos. ` +
          `Recibido: ${digitCount} dígitos`
        )
      }

      for (const item of request.items) {
        // ✅ VALIDACIÓN DE CANTIDAD
        if (!item.cantidad || item.cantidad <= 0) {
          throw new Error(`La cantidad debe ser mayor a 0 para el producto ID ${item.product_id}`)
        }
        if (item.cantidad > 9999) {
          throw new Error(`La cantidad máxima por item es 9999.`)
        }
        if (!Number.isInteger(item.cantidad)) {
          throw new Error(`La cantidad debe ser un número entero.`)
        }

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

      // ✅ VALIDACIÓN DE MÉTODO DE PAGO Y CANAL
      const METODOS_PAGO_VALIDOS = ['efectivo', 'transferencia', 'tarjeta', 'financiamiento']
      if (!request.metodo_pago || !METODOS_PAGO_VALIDOS.includes(request.metodo_pago)) {
        throw new Error(
          `Método de pago inválido: "${request.metodo_pago}". ` +
          `Válidos: ${METODOS_PAGO_VALIDOS.join(', ')}`
        )
      }

      const CANALES_VALIDOS = ['whatsapp', 'facebook', 'instagram']
      if (!request.canal || !CANALES_VALIDOS.includes(request.canal)) {
        throw new Error(
          `Canal inválido: "${request.canal}". ` +
          `Válidos: ${CANALES_VALIDOS.join(', ')}`
        )
      }

      if (request.financing_data && !['financiamiento', 'tarjeta'].includes(request.metodo_pago)) {
        throw new Error(
          `Financiamiento solo es compatible con metodo_pago='financiamiento' o 'tarjeta'.`
        )
      }

      let total = 0
      const newOrderItems: OrderItem[] = []
      const stockAdjustments: Array<{
        product_id: number
        location_id?: number
        delta: number
        stock_anterior: number
        stock_nuevo: number
        reason: string
        reference_id: number
      }> = []
      const imeiEvents: Array<{
        imei: string
        product_id: number
        location_id?: number
        type: 'sold' | 'released' | 'trade_in_intake'
        reference_id: number
      }> = []
      const newOrderId = Math.max(0, ...orders.map(o => o.id)) + 1
      const newStockHistory: StockHistory[] = []
      const newIMEIHistory: IMEIHistory[] = []
      const updatedIMEIs: ProductIMEI[] = [...productIMEIs]

      // Clone stock to avoid partial mutations on error
      const updatedStock = stock.map(s => ({...s}))

      for (const item of request.items) {
        const product = products.find(p => p.id === item.product_id)!
        // V2.0: Intentar obtener tasa de cambio del SalesProfile primero
           let TASA_CAMBIO = 25.0 // Default fallback
           
           if (salesProfile && salesProfile.configuracion) {
             try {
               const config = salesProfile.configuracion
               if (config.exchange_rate) {
                 TASA_CAMBIO = Number(config.exchange_rate)
               }
             } catch (e) {
               console.warn('Error parsing sales profile config for exchange rate', e)
             }
           } else if (profile?.settings?.exchangeRate) {
             // Legacy fallback
             TASA_CAMBIO = profile.settings.exchangeRate
           }
          
        // Fix 2: Currency Conversion
        let precioFinal = product.precio
        
        // V2.1: Usar precio personalizado si existe
        if (item.precio_unitario !== undefined) {
           precioFinal = item.precio_unitario
           
           // --- VALIDACIONES DE SEGURIDAD (Local Mode) ---
           let costoLocal = product.costo
           if (product.moneda === 'USD') {
              costoLocal = product.costo * TASA_CAMBIO
           }
           
           // 1. No vender bajo costo
           if (precioFinal < costoLocal) {
              throw new Error(`El precio negociado (${precioFinal}) para '${product.nombre}' es menor al costo. Operación no permitida.`)
           }
           
           // 2. Reglas para Bots
           if (salesProfile && salesProfile.tipo === 'bot_ia') {
              let precioBaseLocal = product.precio
              if (product.moneda === 'USD') {
                 precioBaseLocal = product.precio * TASA_CAMBIO
              }
              
              // REGLA 1: Límite de descuento dinámico (5% normal, 2% con regalías)
              const hasGifts = request.items.some(i => i.es_regalo_promocion)
              const MAX_DISCOUNT_PERCENT = hasGifts ? 0.02 : 0.05
              
              const minPriceAllowed = precioBaseLocal * (1 - MAX_DISCOUNT_PERCENT)
              
              if (precioFinal < minPriceAllowed) {
                 throw new Error(`El bot no está autorizado a dar descuentos mayores al ${MAX_DISCOUNT_PERCENT*100}%${hasGifts ? ' (por incluir regalías)' : ''}. Precio mínimo: ${minPriceAllowed}`)
              }

              // REGLA 2: Números cerrados
              const remainder = precioFinal % 100
              if (Math.abs(remainder) > 0.01 && Math.abs(remainder - 100) > 0.01) {
                  throw new Error(`El bot solo puede negociar números cerrados (ej. 21500). Precio inválido: ${precioFinal}`)
              }
           }
           // ----------------------------------------------
           
        } else {
           if (product.moneda === 'USD') {
              // Use the TASA_CAMBIO calculated above
              precioFinal = product.precio * TASA_CAMBIO
           } else if (product.moneda !== 'HNL') {
              console.warn(`Producto ${product.nombre} tiene moneda ${product.moneda}, se asume HNL para totalización`)
           }
        }
        
        const esRegalo = item.es_regalo_promocion === true || precioFinal === 0

        if (!esRegalo) {
          total += precioFinal * item.cantidad
        }

        const stockEntry = updatedStock.find(
          s => s.product_id === item.product_id && s.location_id === request.source_location_id
        )!
        
        const stockAnterior = stockEntry.cantidad_disponible
        stockEntry.cantidad_disponible -= item.cantidad
        const stockNuevo = stockEntry.cantidad_disponible

        stockAdjustments.push({
          product_id: item.product_id,
          location_id: request.source_location_id,
          delta: -item.cantidad,
          stock_anterior: stockAnterior,
          stock_nuevo: stockNuevo,
          reason: 'order_sale',
          reference_id: newOrderId
        })

        if (stockEntry.cantidad_reservada && stockEntry.cantidad_disponible < stockEntry.cantidad_reservada) {
          throw new Error(
            `Critical stock error for product ${item.product_id}: available below reserved after sale`
          )
        }

        // V2.0: Handle IMEIs
        // Check if product is serialized (explicit flag OR has IMEIs registered)
        const isSerialized = product.is_serialized || updatedIMEIs.some(pi => pi.product_id === item.product_id)
        
        if (isSerialized) {
          let imeisToSell: ProductIMEI[] = []

          if (item.imeis && item.imeis.length > 0) {
             // ✅ VALIDACIÓN DE IMEIS DUPLICADOS
             for (const imeiStr of item.imeis) {
               const alreadySold = updatedIMEIs.find(i => 
                 i.imei === imeiStr && 
                 i.product_id === item.product_id && 
                 i.vendido
               )
               if (alreadySold) {
                 throw new Error(
                   `IMEI "${imeiStr}" ya fue vendido en orden #${alreadySold.order_id}.`
                 )
               }
               const isInTransfer = updatedIMEIs.find(i =>
                 i.imei === imeiStr &&
                 i.product_id === item.product_id &&
                 i.transfer_id
               )
               if (isInTransfer) {
                 throw new Error(
                   `IMEI "${imeiStr}" está reservado para transferencia #${isInTransfer.transfer_id}.`
                 )
               }
             }

             // Use provided IMEIs
             if (item.imeis.length !== item.cantidad) {
                throw new Error(`Mismatch between quantity and selected IMEIs for ${product.nombre}`)
             }
             
             imeisToSell = updatedIMEIs.filter(
                pi => pi.product_id === item.product_id &&
                      pi.location_id === request.source_location_id &&
                      !pi.vendido &&
                      item.imeis!.includes(pi.imei)
             )

             if (imeisToSell.length !== item.cantidad) {
                throw new Error(`Some selected IMEIs are not available for ${product.nombre}`)
             }
          } else {
             // STRICT MODE: Require IMEIs
             throw new Error(`El producto '${product.nombre}' es serializado. Debe seleccionar los IMEIs a vender.`)
          }

          // Mark IMEIs as sold
          for (const imei of imeisToSell) {
            const imeiIndex = updatedIMEIs.findIndex(pi => pi.id === imei.id)
            if (imeiIndex !== -1) {
              updatedIMEIs[imeiIndex] = {
                ...updatedIMEIs[imeiIndex],
                vendido: true,
                order_id: newOrderId
              }

              // V2.0: Add IMEI History (Sale)
              newIMEIHistory.push({
                id: Math.max(0, ...imeiHistory.map(h => h.id), ...newIMEIHistory.map(h => h.id)) + 1,
                imei: imei.imei,
                product_id: item.product_id,
                location_id: request.source_location_id,
                event_type: 'venta',
                reference_id: newOrderId,
                reference_type: 'order',
                notes: `Venta en orden #${newOrderId}`,
                created_by: salesProfile?.name || profile?.name || 'Sistema Local',
                created_at: new Date().toISOString()
              })

              imeiEvents.push({
                imei: imei.imei,
                product_id: item.product_id,
                location_id: request.source_location_id,
                type: 'sold',
                reference_id: newOrderId
              })
            }
          }
        }

        // V2.0: Add Stock History
        newStockHistory.push({
          id: Math.max(0, ...stockHistory.map(h => h.id), ...newStockHistory.map(h => h.id)) + 1,
          product_id: item.product_id,
          location_id: request.source_location_id, // V2.0: Add location_id
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
          precio_unitario: precioFinal,
          es_regalo_promocion: esRegalo
        }
        newOrderItems.push(newOrderItem)
      }

      // Calculate trade-in total
      let tradeInTotal = 0
      const newTradeIns: TradeIn[] = []
      const tradeInProducts: Product[] = []
      const tradeInStock: Stock[] = []
      const tradeInIMEIs: ProductIMEI[] = []
      const tradeInStockHistory: StockHistory[] = []

      // NOTE: This logic is duplicated from backend/app/routers/orders.py.
      // Any changes here must be reflected in the backend and vice-versa.
      // ⚠️ CRITICAL: KEEP IN SYNC WITH BACKEND LOGIC ⚠️
      if (request.trade_ins) {
        // Load policies
        const policies = await this.getTradeInPolicies()
        const activePolicies = policies.filter(p => p.is_active)

        for (const tradeIn of request.trade_ins) {
          // VALIDATION: Trade-In Condition
          const validConditions = ['usado', 'dañado', 'para_repuestos', 'nuevo']
          if (!validConditions.includes(tradeIn.condicion)) {
             throw new Error(`Condición de trade-in inválida: ${tradeIn.condicion}. Permitidos: ${validConditions.join(', ')}`)
          }

          // VALIDATION: Policies (V2.1)
          for (const policy of activePolicies) {
             if (policy.rule_type === 'model_rejection' && tradeIn.modelo.toLowerCase().includes(policy.pattern.toLowerCase())) {
                if (policy.action === 'reject') {
                   throw new Error(`Trade-in rechazado por política: ${policy.reason || 'Modelo no aceptado'}`)
                }
             }
             if (policy.rule_type === 'brand_rejection' && tradeIn.marca.toLowerCase().includes(policy.pattern.toLowerCase())) {
                if (policy.action === 'reject') {
                   throw new Error(`Trade-in rechazado por política: ${policy.reason || 'Marca no aceptada'}`)
                }
             }
             if (policy.rule_type === 'condition_rejection' && tradeIn.condicion === policy.pattern) {
                if (policy.action === 'reject') {
                   throw new Error(`Trade-in rechazado por política: ${policy.reason || 'Condición no aceptada'}`)
                }
             }
          }

          tradeInTotal += Number(tradeIn.valor_estimado) || 0
          newTradeIns.push({
            ...tradeIn,
            id: Math.max(0, ...tradeIns.map(t => t.id || 0), ...newTradeIns.map(t => t.id || 0)) + 1,
            order_id: newOrderId,
            created_at: new Date().toISOString()
          })

          // 🔴 LOGICA NUEVA: Ingresar Trade-In al inventario automáticamente
          // 1. Buscar si ya existe un producto compatible (mismo modelo/condición)
          const existingProduct = products.find(p => 
            p.marca === tradeIn.marca && 
            p.modelo === tradeIn.modelo && 
            p.condicion === tradeIn.condicion &&
            (tradeIn.color ? p.color === tradeIn.color : true) &&
            (tradeIn.capacidad ? p.capacidad === tradeIn.capacidad : true) &&
            p.activo
          )

          let newProduct: Product

          if (existingProduct) {
             newProduct = existingProduct
             // No actualizamos precio ni costo del producto existente
          } else {
             // Crear Producto Nuevo si no existe
             const nextProductId = Math.max(0, ...products.map(p => p.id), ...tradeInProducts.map(p => p.id)) + 1
             const skuSuffix = tradeIn.imei ? tradeIn.imei.slice(-6) : crypto.randomUUID().substring(0, 6)
             // V2.0: Asegurar formato consistente con backend RET-{suffix}-{uuid}
             const uuidPart = crypto.randomUUID().substring(0, 4)
             const newSku = `RET-${skuSuffix}-${uuidPart}`

             newProduct = {
                id: nextProductId,
                profile_id: profile?.id,
                sku: newSku,
               nombre: `RETOMA: ${tradeIn.marca} ${tradeIn.modelo}`,
                categoria: 'pendiente_revision', // V2.2 Match backend logic
                marca: tradeIn.marca,
                modelo: tradeIn.modelo,
               color: tradeIn.color,
               capacidad: tradeIn.capacidad,
                condicion: tradeIn.condicion as any,
                precio: tradeIn.precio_venta ? Number(tradeIn.precio_venta) : Number(tradeIn.valor_estimado) * 1.3,
                costo: Number(tradeIn.valor_estimado),
                moneda: 'HNL',
               activo: false, // V2.2 Match backend logic (requires review)
                garantia_meses: 0,
               is_serialized: true
             }
             tradeInProducts.push(newProduct)
          }

          // 2. Crear o Actualizar Stock (SYNC con backend)
          // Buscar en updatedStock (puede contener cambios previos de este mismo loop)
          let stockEntry = updatedStock.find(s => s.product_id === newProduct.id && s.location_id === request.source_location_id)
          const stockAnterior = stockEntry?.cantidad_disponible || 0
          
          if (stockEntry) {
            // Actualizar cantidad disponible
            stockEntry.cantidad_disponible += 1
          } else {
            // Crear nueva entrada de stock
            const nextStockId = Math.max(0, ...updatedStock.map(s => s.id)) + 1
            stockEntry = {
              id: nextStockId,
              product_id: newProduct.id,
              location_id: request.source_location_id,
              cantidad_disponible: 1,
              cantidad_reservada: 0
            }
            updatedStock.push(stockEntry)
          }
          const stockNuevo = stockEntry.cantidad_disponible

          stockAdjustments.push({
            product_id: newProduct.id,
            location_id: request.source_location_id,
            delta: 1,
            stock_anterior,
            stock_nuevo: stockNuevo,
            reason: 'trade_in_intake',
            reference_id: newOrderId
          })

          // 3. Registrar IMEI
          if (tradeIn.imei) {
            // Check if IMEI exists
            const existingImei = updatedIMEIs.find(i => i.imei === tradeIn.imei)
            
            if (existingImei) {
               // Reactivate existing IMEI
               existingImei.product_id = newProduct.id
               existingImei.location_id = request.source_location_id
               existingImei.vendido = false
               existingImei.order_id = undefined
            } else {
                const nextImeiId = Math.max(0, ...updatedIMEIs.map(i => i.id), ...tradeInIMEIs.map(i => i.id)) + 1
                const newImei: ProductIMEI = {
                id: nextImeiId,
                product_id: newProduct.id,
                location_id: request.source_location_id,
                imei: tradeIn.imei,
                vendido: false,
                created_at: new Date().toISOString()
                }
                tradeInIMEIs.push(newImei)
            }

            imeiEvents.push({
              imei: tradeIn.imei,
              product_id: newProduct.id,
              location_id: request.source_location_id,
              type: 'trade_in_intake',
              reference_id: newOrderId
            })

            // V2.0: Add IMEI History (Trade-In)
            newIMEIHistory.push({
              id: Math.max(0, ...imeiHistory.map(h => h.id), ...newIMEIHistory.map(h => h.id)) + 1,
              imei: tradeIn.imei,
              product_id: newProduct.id,
              location_id: request.source_location_id,
              event_type: 'retoma',
              reference_id: newOrderId,
              reference_type: 'order',
              notes: `Ingreso por retoma en orden #${newOrderId}`,
              created_by: salesProfile?.name || profile?.name || 'Sistema Local',
              created_at: new Date().toISOString()
            })
          }

          // 4. Historial Stock
          const nextHistoryId = Math.max(0, ...stockHistory.map(h => h.id), ...newStockHistory.map(h => h.id), ...tradeInStockHistory.map(h => h.id)) + 1
          tradeInStockHistory.push({
            id: nextHistoryId,
            product_id: newProduct.id,
            location_id: request.source_location_id,
            tipo_cambio: 'retoma',
            cantidad: 1,
            stock_anterior: stockAnterior,
            stock_nuevo: stockAnterior + 1,
            referencia_id: newOrderId,
            referencia_tipo: 'order',
            notas: `Ingreso por retoma de ${tradeIn.marca} ${tradeIn.modelo}`,
            usuario: salesProfile?.name || profile?.name || 'Sistema Local',
            created_at: new Date().toISOString()
          })
        }
      }

      // Aplicar retomas
      total = Math.max(0, total - tradeInTotal)

      // Financiamiento (SYNC con backend).
      let financingDetailsString: string | undefined
      if (request.financing_data) {
        const downPayment = Number(request.financing_data.down_payment || 0)
        const amountToFinance = Math.max(0, total - downPayment)
        const months = request.financing_data.months || 0
        const bankId = request.financing_data.bank_id

        // Load banks to get real rates
        const banks = await this.getBanks(true)
        const bank = banks.find(b => b.id === bankId)
        
        if (!bank) {
           throw new Error(`Banco con ID ${bankId} no encontrado o inactivo`)
        }

        let rate = bank.normal_card_rate || 0.04 // Default fallback
        const bankName = bank.name

        if (months > 0) {
           const option = bank.financing_options.find(o => o.months === months && o.active)
           if (!option) {
              throw new Error(`Opción de financiamiento de ${months} meses no encontrada para ${bank.name}`)
           }
           rate = option.rate
        }
        
        const surcharge = amountToFinance * rate
        const totalWithSurcharge = amountToFinance + surcharge
        const monthlyPayment = months > 0 ? totalWithSurcharge / months : totalWithSurcharge

        // Total final = prima + (monto a financiar + recargo)
        total = downPayment + totalWithSurcharge

        financingDetailsString = JSON.stringify({
          bank_id: bankId,
          bank_name: bankName,
          months,
          rate: Number(rate.toFixed(4)),
          surcharge: Number(surcharge.toFixed(2)),
          monthly_payment: Number(monthlyPayment.toFixed(2)),
          original_total: Number((total + tradeInTotal).toFixed(2)),
          down_payment: downPayment,
          financed_amount: Number(amountToFinance.toFixed(2))
        })
      }

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
        financing_details: financingDetailsString,
        estado: 'pendiente',
        created_at: new Date().toISOString(),
        notas: request.notas,
        updated_at: new Date().toISOString(),
        trade_ins: newTradeIns
      }

      await this.setProducts([...products, ...tradeInProducts])
      await this.setStock([...updatedStock, ...tradeInStock])
      await this.setOrders([...orders, newOrder])
      await this.setOrderItems([...orderItems, ...newOrderItems])
      await this.setStockHistory([...stockHistory, ...newStockHistory, ...tradeInStockHistory])
      await this.setProductIMEIs([...updatedIMEIs, ...tradeInIMEIs])
      await this.setTradeIns([...tradeIns, ...newTradeIns])
      await this.setIMEIHistory([...imeiHistory, ...newIMEIHistory])

      await this.recordSyncEvent({
        entity: 'order',
        action: 'create',
        entityId: newOrderId,
        payload: {
          order: newOrder,
          items: newOrderItems,
          trade_ins: newTradeIns,
          trade_in_products: tradeInProducts,
          trade_in_imeis: tradeInIMEIs,
          stock_adjustments: stockAdjustments,
          imei_events: imeiEvents,
          financing_data: request.financing_data ?? null,
          source_location_id: request.source_location_id
        }
      })

      if (imeiEvents.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'update',
          entityId: null,
          payload: {
            order_id: newOrderId,
            source_location_id: request.source_location_id ?? null,
            events: imeiEvents
          }
        })
      }

      if (tradeInIMEIs.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'assign',
          entityId: null,
          payload: {
            order_id: newOrderId,
            source_location_id: request.source_location_id ?? null,
            imeis: tradeInIMEIs
          }
        })
      }

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
    } finally {
      release()
    }
  }

  async fetchOrders(salesProfileSlug?: string): Promise<OrderWithItems[]> {
    try {
      const [orders, orderItems, products, , salesProfiles] = await Promise.all([
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

      await this.recordSyncEvent({
        entity: 'profile',
        action: 'create',
        entityId: newProfile.id,
        payload: {
          profile: newProfile
        }
      })
      return newProfile
    } catch (error) {
      console.error('Error creating profile:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to create profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
      if (imeiEvents.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'update',
          entityId: null,
          payload: {
            order_id: newOrderId,
            source_location_id: request.source_location_id ?? null,
            events: imeiEvents
          }
        })
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

      const previousProfile = { ...profiles[profileIndex] }

      profiles[profileIndex] = {
        ...previousProfile,
        ...updates
      }

      await this.setProfiles(profiles)

      await this.recordSyncEvent({
        entity: 'profile',
        action: 'update',
        entityId: profileId,
        payload: {
          before: previousProfile,
          after: profiles[profileIndex],
          updates
        }
      })
      return profiles[profileIndex]
    } catch (error) {
      console.error('Error updating profile:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to update profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async cancelOrder(orderId: number, reason?: string): Promise<OrderWithItems> {
    const release = await inventoryLock.acquire()
    try {
      const [orders, orderItems, stock, imeis, stockHistory] = await Promise.all([
        this.loadOrders(),
        this.getOrderItems(),
        this.getStock(),
        this.loadProductIMEIs(),
        this.loadStockHistory()
      ])

      const orderIndex = orders.findIndex(o => o.id === orderId)
      if (orderIndex === -1) {
        throw new Error(`Order with id ${orderId} not found`)
      }

      const order = orders[orderIndex]
      const orderBefore = { ...order }
      if (order.estado === 'cancelada') {
        throw new Error('Order is already cancelled')
      }

      const items = orderItems.filter(oi => oi.order_id === orderId)
      const locationId = order.source_location_id

      if (!locationId) {
         console.warn(`Order ${orderId} has no source_location_id. Stock restoration might be inaccurate.`)
      }

      const stockRestorations: Array<{
        product_id: number
        location_id?: number
        cantidad: number
        stock_anterior: number
        stock_nuevo: number
      }> = []
      const imeiEvents: Array<{
        imei: string
        product_id: number
        location_id?: number
        type: 'released'
        reference_id: number
      }> = []

      // 1. Restore Stock
      for (const item of items) {
        // Determine location (fallback to first available if legacy)
        let targetLocationId = locationId
        if (!targetLocationId) {
           // Try to find where stock exists for this product
           const stockEntry = stock.find(s => s.product_id === item.product_id && s.cantidad_disponible > 0)
           targetLocationId = stockEntry?.location_id
        }

        if (targetLocationId) {
          const stockEntry = stock.find(s => s.product_id === item.product_id && s.location_id === targetLocationId)
          if (stockEntry) {
            const stockAnterior = stockEntry.cantidad_disponible
            stockEntry.cantidad_disponible += item.cantidad
            
            // Record History
            stockHistory.push({
              id: Math.max(0, ...stockHistory.map(h => h.id)) + 1,
              product_id: item.product_id,
              location_id: targetLocationId,
              tipo_cambio: 'devolucion', 
              cantidad: item.cantidad,
              stock_anterior: stockAnterior,
              stock_nuevo: stockEntry.cantidad_disponible,
              referencia_id: orderId,
              referencia_tipo: 'order_cancelled',
              notas: `Cancelación de orden #${orderId}: ${reason || 'Sin razón'}`,
              usuario: 'Sistema Local',
              created_at: new Date().toISOString()
            })

            stockRestorations.push({
              product_id: item.product_id,
              location_id: targetLocationId,
              cantidad: item.cantidad,
              stock_anterior,
              stock_nuevo: stockEntry.cantidad_disponible
            })
          } else {
            console.error(`Stock entry not found for product ${item.product_id} at location ${targetLocationId}`)
          }
        }
      }

      // 2. Release IMEIs
      for (let i = 0; i < imeis.length; i++) {
        if (imeis[i].order_id === orderId && imeis[i].vendido) {
            imeis[i] = { ...imeis[i], vendido: false, order_id: undefined }
                imeiEvents.push({
                  imei: imeis[i].imei,
                  product_id: imeis[i].product_id,
                  location_id: imeis[i].location_id,
                  type: 'released',
                  reference_id: orderId
                })
        }
      }

      // 3. Update Order Status
      orders[orderIndex] = {
        ...order,
        estado: 'cancelada',
        notes: reason ? (order.notes ? `${order.notes}\nCancelación: ${reason}` : `Cancelación: ${reason}`) : order.notes,
        updated_at: new Date().toISOString()
      }

      const updatedOrder = orders[orderIndex]

      // 4. Save All
      await this.setOrders(orders)
      await this.setStock(stock)
      await this.setProductIMEIs(imeis)
      await this.setStockHistory(stockHistory)

      await this.recordSyncEvent({
        entity: 'order',
        action: 'cancel',
        entityId: orderId,
        payload: {
          reason: reason ?? null,
          order_before: orderBefore,
          order_after: updatedOrder,
          stock_restored: stockRestorations,
          imei_events: imeiEvents
        }
      })

      if (imeiEvents.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'cancel',
          entityId: null,
          payload: {
            order_id: orderId,
            reason: reason ?? null,
            events: imeiEvents
          }
        })
      }

      // 5. Return updated order
      // We need to release the lock before calling fetchOrders because fetchOrders might try to acquire it?
      // No, fetchOrders calls loadOrders which uses getKV, which is fine.
      // But fetchOrders is public and doesn't acquire lock.
      
    } catch (error) {
      console.error('Error cancelling order:', error)
      throw error instanceof Error ? error : new Error(`Failed to cancel order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      release()
    }

    // Fetch updated order outside the lock to avoid potential issues if fetchOrders grew complex
    return this.fetchOrders().then(orders => {
        const found = orders.find(o => o.id === orderId)
        if (!found) throw new Error('Order not found after update')
        return found
    })
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

      const previousStatus = orders[orderIndex].estado
      orders[orderIndex].estado = estado
      await this.setOrders(orders)

      await this.recordSyncEvent({
        entity: 'order',
        action: 'update',
        entityId: orderId,
        payload: {
          field: 'estado',
          previous: previousStatus,
          next: estado
        }
      })

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
        imeis?: string[]
        es_regalo_promocion?: boolean
      }>
    }
  ): Promise<OrderWithItems> {
    const release = await inventoryLock.acquire()
    try {
      const [orders, orderItems, products, stock, imeis, stockHistory] = await Promise.all([
        this.loadOrders(),
        this.getOrderItems(),
        this.loadProducts(),
        this.getStock(),
        this.loadProductIMEIs(),
        this.loadStockHistory()
      ])

      const orderIndex = orders.findIndex(o => o.id === orderId)
      if (orderIndex === -1) {
        throw new Error(`Order with id ${orderId} not found`)
      }

      const currentOrder = orders[orderIndex]
      
      // VALIDATION: Phone Format
      if (updates.customer_phone) {
        const phoneRegex = /^\+?[0-9]{8,15}$/
        const phoneAsString = String(updates.customer_phone).trim()
        if (!phoneRegex.test(phoneAsString)) {
          throw new Error('El número de teléfono debe tener entre 8 y 15 dígitos.')
        }
      }

      // VALIDATION: Payment Method
      if (updates.metodo_pago) {
        const validPaymentMethods = ['efectivo', 'transferencia', 'tarjeta', 'financiamiento']
        if (!validPaymentMethods.includes(updates.metodo_pago)) {
          throw new Error(`Método de pago inválido: ${updates.metodo_pago}`)
        }
      }

      // VALIDATION: Channel
      if (updates.canal) {
        const validChannels = ['whatsapp', 'facebook', 'instagram']
        if (!validChannels.includes(updates.canal)) {
          throw new Error(`Canal inválido: ${updates.canal}`)
        }
      }

      const currentItems = orderItems.filter(oi => oi.order_id === orderId)
      const locationId = currentOrder.source_location_id
      if (!locationId) {
        throw new Error('Order does not have a source_location_id; cannot update stock by location')
      }

      const orderBeforeSnapshot = {
        ...currentOrder,
        items: currentItems.map(item => ({ ...item }))
      }

      const restoredStockEvents: Array<{
        product_id: number
        location_id: number
        cantidad: number
        stock_anterior: number
        stock_nuevo: number
      }> = []

      const appliedStockEvents: Array<{
        product_id: number
        location_id: number
        cantidad: number
        stock_anterior: number
        stock_nuevo: number
      }> = []

      const imeiEvents: Array<{
        imei: string
        product_id: number
        location_id: number
        type: 'released' | 'sold'
        reference_id: number
      }> = []

      if (updates.items) {
        // VALIDATION: Items Quantity
        for (const item of updates.items) {
           if (item.cantidad <= 0) {
             throw new Error(`La cantidad para el producto ID ${item.product_id} debe ser mayor a 0.`)
           }
           if (item.cantidad > 9999) {
             throw new Error(`La cantidad para el producto ID ${item.product_id} no puede exceder 9999.`)
           }
           if (!Number.isInteger(item.cantidad)) {
             throw new Error(`La cantidad para el producto ID ${item.product_id} debe ser un número entero.`)
           }
        }

        // 1. Restaurar stock de los items actuales
        for (const item of currentItems) {
          const stockEntry = stock.find(s => s.product_id === item.product_id && s.location_id === locationId)
          if (!stockEntry) {
            throw new Error(`Stock record not found for product ${item.product_id} at location ${locationId} while restoring`)  
          }
          const stockAnterior = stockEntry.cantidad_disponible
          stockEntry.cantidad_disponible += item.cantidad

          // Record History
          stockHistory.push({
            id: Math.max(0, ...stockHistory.map(h => h.id)) + 1,
            product_id: item.product_id,
            location_id: locationId,
            tipo_cambio: 'devolucion',
            cantidad: item.cantidad,
            stock_anterior: stockAnterior,
            stock_nuevo: stockEntry.cantidad_disponible,
            referencia_id: orderId,
            referencia_tipo: 'order_update',
            notas: `Actualización de orden #${orderId} - Restauración de items`,
            usuario: 'Sistema Local',
            created_at: new Date().toISOString()
          })

          restoredStockEvents.push({
            product_id: item.product_id,
            location_id: locationId,
            cantidad: item.cantidad,
            stock_anterior,
            stock_nuevo: stockEntry.cantidad_disponible
          })
        }

        // 2. Liberar IMEIs asociados a esta orden (marcarlos como no vendidos)
        // Esto permite que sean re-seleccionados si se mantienen en la orden, o liberados si se quitan
        for (let i = 0; i < imeis.length; i++) {
          if (imeis[i].order_id === orderId) {
            imeis[i] = { ...imeis[i], vendido: false, order_id: undefined }
            imeiEvents.push({
              imei: imeis[i].imei,
              product_id: imeis[i].product_id,
              location_id: imeis[i].location_id!,
              type: 'released',
              reference_id: orderId
            })
          }
        }

        // 3. Validar stock libre por ubicación para los nuevos items
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

          // Validación de IMEIs para productos serializados
          if (item.imeis && item.imeis.length > 0) {
             if (item.imeis.length !== item.cantidad) {
                throw new Error(`Mismatch between quantity and selected IMEIs for ${product.nombre}`)
             }
             
             // Verificar disponibilidad de IMEIs (ahora que liberamos los de la orden actual, deberían estar disponibles)
             const unavailableImeis = item.imeis.filter(imeiStr => {
               const imeiRecord = imeis.find(i => i.imei === imeiStr && i.product_id === item.product_id)
               // Debe existir, estar en la ubicación correcta, y NO estar vendido (o haber sido liberado recién)
               return !imeiRecord || imeiRecord.location_id !== locationId || imeiRecord.vendido
             })

             if (unavailableImeis.length > 0) {
               throw new Error(`Some selected IMEIs are not available for ${product.nombre}: ${unavailableImeis.join(', ')}`)
             }
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
          const esRegalo = item.es_regalo_promocion === true
          if (!esRegalo) {
            total += product.precio * item.cantidad
          }

          const stockEntry = stock.find(s => s.product_id === item.product_id && s.location_id === locationId)
          if (!stockEntry) {
            throw new Error(`Stock entry for product ${item.product_id} at location ${locationId} not found`)
          }
          const stockAnterior = stockEntry.cantidad_disponible
          stockEntry.cantidad_disponible -= item.cantidad
          if (stockEntry.cantidad_reservada && stockEntry.cantidad_disponible < stockEntry.cantidad_reservada) {
            throw new Error(`Stock for product ${item.product_id} at location ${locationId} cannot fall below reserved (${stockEntry.cantidad_reservada})`)
          }

          // Record History
          stockHistory.push({
            id: Math.max(0, ...stockHistory.map(h => h.id)) + 1,
            product_id: item.product_id,
            location_id: locationId,
            tipo_cambio: 'venta',
            cantidad: -item.cantidad,
            stock_anterior: stockAnterior,
            stock_nuevo: stockEntry.cantidad_disponible,
            referencia_id: orderId,
            referencia_tipo: 'order_update',
            notas: `Actualización de orden #${orderId} - Nuevos items`,
            usuario: 'Sistema Local',
            created_at: new Date().toISOString()
          })

          appliedStockEvents.push({
            product_id: item.product_id,
            location_id: locationId,
            cantidad: item.cantidad,
            stock_anterior,
            stock_nuevo: stockEntry.cantidad_disponible
          })

          // Marcar IMEIs como vendidos
          if (item.imeis && item.imeis.length > 0) {
            for (const imeiStr of item.imeis) {
              const imeiIndex = imeis.findIndex(i => i.imei === imeiStr && i.product_id === item.product_id)
              if (imeiIndex !== -1) {
                imeis[imeiIndex] = { ...imeis[imeiIndex], vendido: true, order_id: orderId }
                imeiEvents.push({
                  imei: imeis[imeiIndex].imei,
                  product_id: item.product_id,
                  location_id: locationId,
                  type: 'sold',
                  reference_id: orderId
                })
              }
            }
          }

          const newOrderItem: OrderItem = {
            id: item.id || nextItemId++,
            order_id: orderId,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: product.precio,
            es_regalo_promocion: esRegalo,
            imeis: item.imeis // Guardar IMEIs en el item para referencia local si es soportado
          }
          newOrderItems.push(newOrderItem)
        }

        await this.setOrderItems([...updatedOrderItems, ...newOrderItems])
        await this.setStock(stock)
        await this.setProductIMEIs(imeis)
        await this.setStockHistory(stockHistory)

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

      const updatedOrder = orders[orderIndex]

      await this.recordSyncEvent({
        entity: 'order',
        action: 'update',
        entityId: orderId,
        payload: {
          updates,
          order_before: orderBeforeSnapshot,
          order_after: updatedOrder,
          stock_restored: restoredStockEvents,
          stock_applied: appliedStockEvents,
          imei_events: imeiEvents
        }
      })

      if (imeiEvents.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'update',
          entityId: null,
          payload: {
            order_id: orderId,
            events: imeiEvents
          }
        })
      }

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
    } finally {
      release()
    }
  }

  async addProduct(product: Omit<Product, 'id'>, initialStock: number, locationId?: number): Promise<ProductWithStock> {
    const release = await inventoryLock.acquire()
    try {
      const [products, stock, locations, stockHistory] = await Promise.all([
        this.loadProducts(),
        this.getStock(),
        this.loadLocations(),
        this.loadStockHistory()
      ])

      if (!locationId) {
        throw new Error('locationId is required to add products with stock in V2.0 local mode')
      }

      const locationExists = locations.some(l => l.id === locationId)
      if (!locationExists) {
        throw new Error(`Location ${locationId} not found; cannot assign initial stock`)
      }

      // V2.0 FIX: Validar que SKU no sea duplicado
      const skuLower = (product.sku || '').toLowerCase().trim()
      if (skuLower && products.some(p => p.sku && p.sku.toLowerCase() === skuLower)) {
        throw new Error(`SKU '${product.sku}' ya existe. Los SKUs deben ser únicos.`)
      }

      // V2.0 FIX: Enforce IMEIs for serialized products if stock > 0 (Match backend logic)
      let isSerialized = product.is_serialized
      if (product.categoria === 'celular' && !isSerialized) {
         isSerialized = true
      }

      if (isSerialized && initialStock > 0) {
          if (!product.imeis || product.imeis.length === 0) {
              throw new Error("Para productos serializados con stock inicial, debe proporcionar los IMEIs.")
          }
          if (product.imeis.length !== initialStock) {
              throw new Error(`La cantidad de IMEIs proporcionados (${product.imeis.length}) no coincide con el stock inicial (${initialStock})`)
          }
      }

      const newProduct: Product = {
        ...product,
        is_serialized: isSerialized, // Ensure flag is set
        moneda: product.moneda || 'HNL', // Respect provided currency or default to HNL
        id: Math.max(0, ...products.map(p => p.id)) + 1
      }

      const newStock: Stock = {
        id: Math.max(0, ...stock.map(s => s.id)) + 1,
        product_id: newProduct.id,
        location_id: locationId,
        cantidad_disponible: initialStock,
        cantidad_reservada: 0
      }

      // Register IMEIs if provided
      const productIMEIs = await this.loadProductIMEIs()
      const newIMEIs: ProductIMEI[] = []
      
      if (newProduct.imeis && newProduct.imeis.length > 0) {
          let nextImeiId = Math.max(0, ...productIMEIs.map(i => i.id)) + 1
          for (const imeiStr of newProduct.imeis) {
              // Check for duplicates globally
              if (productIMEIs.some(pi => pi.imei === imeiStr)) {
                  throw new Error(`El IMEI ${imeiStr} ya existe en el sistema.`)
              }
              
              newIMEIs.push({
                  id: nextImeiId++,
                  product_id: newProduct.id,
                  location_id: locationId,
                  imei: imeiStr,
                  vendido: false,
                  created_at: new Date().toISOString()
              })
          }
      }

      if (initialStock > 0) {
        stockHistory.push({
          id: Math.max(0, ...stockHistory.map(h => h.id)) + 1,
          product_id: newProduct.id,
          location_id: locationId,
          tipo_cambio: 'compra',
          cantidad: initialStock,
          stock_anterior: 0,
          stock_nuevo: initialStock,
          referencia_id: 0,
          referencia_tipo: 'initial_stock',
          notas: 'Stock inicial al crear producto',
          usuario: 'Sistema Local',
          created_at: new Date().toISOString()
        })
      }

      await this.setProducts([...products, newProduct])
      await this.setStock([...stock, newStock])
      await this.setStockHistory(stockHistory)
      if (newIMEIs.length > 0) {
          await this.setProductIMEIs([...productIMEIs, ...newIMEIs])
      }

      await this.recordSyncEvent({
        entity: 'product',
        action: 'create',
        entityId: newProduct.id,
        payload: {
          product: newProduct,
          stock: newStock,
          initialStock,
          location_id: locationId ?? null,
          imeis: newIMEIs
        }
      })

      if (newIMEIs.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'assign',
          entityId: null,
          payload: {
            product_id: newProduct.id,
            location_id: locationId ?? null,
            imeis: newIMEIs
          }
        })
      }

      return {
        ...newProduct,
        stock_disponible: initialStock,
        imeis: newProduct.imeis // Return IMEIs in response
      }
    } catch (error) {
      console.error('Error adding product:', error)
      throw new Error(`Failed to add product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      release()
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
    const release = await inventoryLock.acquire()
    try {
      // 🔒 Validar cantidad >= 0 (Bug #29 fix)
      if (cantidad < 0) {
        throw new Error('Stock no puede ser negativo')
      }

      if (!locationId) {
        throw new Error('locationId is required to update stock by location (V2.0)')
      }

      const [stock, locations, stockHistory] = await Promise.all([
        this.getStock(),
        this.loadLocations(),
        this.loadStockHistory()
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

      const stockAnterior = stockEntry.cantidad_disponible
      stockEntry.cantidad_disponible = cantidad
      const reservado = stockEntry.cantidad_reservada || 0
      if (stockEntry.cantidad_disponible < reservado) {
        throw new Error(
          `Stock for product ${productId} at location ${locationId} cannot be below reserved (${reservado})`
        )
      }

      stockHistory.push({
        id: Math.max(0, ...stockHistory.map(h => h.id)) + 1,
        product_id: productId,
        location_id: locationId,
        tipo_cambio: 'ajuste',
        cantidad: cantidad - stockAnterior,
        stock_anterior: stockAnterior,
        stock_nuevo: cantidad,
        referencia_id: 0,
        referencia_tipo: 'manual_adjustment',
        notas: 'Ajuste manual de stock',
        usuario: 'Sistema Local',
        created_at: new Date().toISOString()
      })

      await this.setStock(stock)
      await this.setStockHistory(stockHistory)

      await this.recordSyncEvent({
        entity: 'stock',
        action: 'update',
        entityId: `${productId}:${locationId}`,
        payload: {
          product_id: productId,
          location_id: locationId,
          cantidad,
          stock_anterior: stockAnterior,
          stock_nuevo: cantidad
        }
      })
    } catch (error) {
      console.error('Error updating stock:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to update stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      release()
    }
  }

  async updateStockByLocation(productId: number, locationId: number, cantidad: number): Promise<void> {
    // Paridad con API: endpoint POST /products/{product_id}/stock/location/{location_id}
    return this.updateStock(productId, cantidad, locationId)
  }

  async updateProduct(productId: number, updates: Partial<ProductWithStock>): Promise<ProductWithStock> {
    const release = await inventoryLock.acquire()
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

      // V2.0 FIX: Do NOT update stock implicitly from updateProduct.
      // Stock updates must be explicit via updateStock with locationId.
      if (stock_disponible !== undefined) {
         console.warn('updateProduct: stock_disponible ignored in V2.0. Use updateStock(productId, quantity, locationId) instead.')
      }

      await this.recordSyncEvent({
        entity: 'product',
        action: 'update',
        entityId: productId,
        payload: {
          updates: productUpdates,
          stock_disponible: stock_disponible ?? undefined
        }
      })

      const stock = await this.getStock()
      // Calculate total stock across all locations for the return value
      const totalStock = stock
        .filter(s => s.product_id === productId)
        .reduce((sum, s) => sum + s.cantidad_disponible, 0)

      return {
        ...products[productIndex],
        stock_disponible: totalStock
      }
    } catch (error) {
      console.error('Error updating product:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to update product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      release()
    }
  }

  async deleteProduct(productId: number): Promise<void> {
    const release = await inventoryLock.acquire()
    try {
      const [products, stock, orderItems, transfers] = await Promise.all([
        this.loadProducts(),
        this.getStock(),
        this.getOrderItems(),
        this.loadStockTransfers()
      ])

      // Verificar si el producto está en alguna orden
      const isInOrder = orderItems.some(item => item.product_id === productId)
      if (isInOrder) {
        throw new Error('No se puede eliminar el producto porque está referenciado en órdenes existentes')
      }

      // Bloquear eliminación si hay stock reservado o transferencias pendientes
      const productStock = stock.filter(s => s.product_id === productId)
      const hasReserved = productStock.some(s => (s.cantidad_reservada || 0) > 0)
      if (hasReserved) {
        throw new Error('No se puede eliminar el producto porque tiene stock reservado en transferencias pendientes')
      }

      const pendingTransfer = transfers.find(t => t.product_id === productId && t.estado === 'pendiente')
      if (pendingTransfer) {
        throw new Error(`No se puede eliminar el producto porque tiene una transferencia pendiente (#${pendingTransfer.id})`)
      }

      // Eliminar producto y su stock
      const updatedProducts = products.filter(p => p.id !== productId)
      const updatedStock = stock.filter(s => s.product_id !== productId)

      await Promise.all([
        this.setProducts(updatedProducts),
        this.setStock(updatedStock)
      ])

      await this.recordSyncEvent({
        entity: 'product',
        action: 'delete',
        entityId: productId,
        payload: {
          product_id: productId
        }
      })
    } catch (error) {
      console.error('Error deleting product:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to delete product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      release()
    }
  }

  async deleteOrder(orderId: number): Promise<void> {
    const release = await inventoryLock.acquire()
    try {
      const [orders, orderItems, stock, productIMEIs, stockHistory] = await Promise.all([
        this.loadOrders(),
        this.getOrderItems(),
        this.getStock(),
        this.loadProductIMEIs(),
        this.loadStockHistory()
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
      const updatedIMEIs = [...productIMEIs]
      const newStockHistory: StockHistory[] = []
      const stockRestorations: Array<{
        product_id: number
        location_id: number
        cantidad: number
        stock_anterior: number
        stock_nuevo: number
      }> = []
      const imeiEvents: Array<{
        imei: string
        product_id: number
        location_id: number
        type: 'released'
        reference_id: number
      }> = []
      
      for (const item of itemsToRestore) {
        const stockItem = updatedStock.find(s => s.product_id === item.product_id && s.location_id === locationId)
        if (!stockItem) {
          throw new Error(`No se encontró stock para el producto ${item.product_id} en la ubicación ${locationId} al eliminar la orden`)
        }
        
        const stockAnterior = stockItem.cantidad_disponible
        stockItem.cantidad_disponible += item.cantidad
        
        // Registrar en historial de stock (reversión)
        newStockHistory.push({
          id: Math.max(0, ...stockHistory.map(h => h.id), ...newStockHistory.map(h => h.id)) + 1,
          product_id: item.product_id,
          location_id: locationId,
          tipo_cambio: 'reversa_venta',
          cantidad: item.cantidad,
          stock_anterior: stockAnterior,
          stock_nuevo: stockItem.cantidad_disponible,
          referencia_id: orderId,
          referencia_tipo: 'order_deleted',
          notas: `Reversión de orden #${orderId} eliminada`,
          usuario: 'Sistema Local',
          created_at: new Date().toISOString()
        })

        stockRestorations.push({
          product_id: item.product_id,
          location_id,
          cantidad: item.cantidad,
          stock_anterior,
          stock_nuevo: stockItem.cantidad_disponible
        })
        
        // Liberar IMEIs vendidos en esta orden (marcar como no vendidos)
        if (item.imeis && item.imeis.length > 0) {
          for (const imeiStr of item.imeis) {
            const imeiIndex = updatedIMEIs.findIndex(i => 
              i.imei === imeiStr && 
              i.product_id === item.product_id && 
              i.vendido && 
              i.order_id === orderId
            )
            if (imeiIndex !== -1) {
              updatedIMEIs[imeiIndex] = {
                ...updatedIMEIs[imeiIndex],
                vendido: false,
                order_id: undefined
              }
              imeiEvents.push({
                imei: updatedIMEIs[imeiIndex].imei,
                product_id: updatedIMEIs[imeiIndex].product_id,
                location_id: updatedIMEIs[imeiIndex].location_id!,
                type: 'released',
                reference_id: orderId
              })
            }
          }
        }
      }

      const updatedOrders = orders.filter(o => o.id !== orderId)
      const updatedOrderItems = orderItems.filter(item => item.order_id !== orderId)

      await Promise.all([
        this.setOrders(updatedOrders),
        this.setOrderItems(updatedOrderItems),
        this.setStock(updatedStock),
        this.setProductIMEIs(updatedIMEIs),
        this.setStockHistory([...stockHistory, ...newStockHistory])
      ])

      await this.recordSyncEvent({
        entity: 'order',
        action: 'delete',
        entityId: orderId,
        payload: {
          order,
          items: itemsToRestore,
          stock_restored: stockRestorations,
          imei_events: imeiEvents
        }
      })

      if (imeiEvents.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'update',
          entityId: null,
          payload: {
            order_id: orderId,
            events: imeiEvents
          }
        })
      }
    } catch (error) {
      console.error('Error deleting order:', error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Failed to delete order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      release()
    }
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[], locationId?: number): Promise<ProductWithStock[]> {
    const release = await inventoryLock.acquire()
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
          moneda: 'Lps', // Force Lps
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

      await this.recordSyncEvent({
        entity: 'product',
        action: 'create',
        entityId: null,
        payload: {
          products: newProducts,
          stock_entries: newStockEntries,
          location_id: locationId,
          count: newProducts.length
        },
        metadata: {
          mode: 'bulk_create'
        }
      })

      return createdProducts
    } catch (error) {
      console.error('Error bulk creating products:', error)
      throw new Error(`Failed to bulk create products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      release()
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

  async getStockHistory(productId: number, params?: { limit?: number; tipo_cambio?: string; date_from?: string; date_to?: string }): Promise<StockHistory[]> {
    const history = await this.loadStockHistory()
    let filtered = history.filter(h => h.product_id === productId)

    if (params?.tipo_cambio) {
      filtered = filtered.filter(h => h.tipo_cambio === params.tipo_cambio)
    }
    if (params?.date_from) {
      const fromTs = new Date(params.date_from).getTime()
      filtered = filtered.filter(h => new Date(h.created_at).getTime() >= fromTs)
    }
    if (params?.date_to) {
      const toTs = new Date(params.date_to).getTime()
      filtered = filtered.filter(h => new Date(h.created_at).getTime() <= toTs)
    }

    filtered = filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    if (params?.limit) {
      filtered = filtered.slice(0, params.limit)
    }

    return filtered
  }

  async getLocationStockHistory(locationId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]> {
    const [history, locations] = await Promise.all([
      this.loadStockHistory(),
      this.loadLocations()
    ])

    const locationExists = locations.some(location => location.id === locationId)
    if (!locationExists) {
      throw new Error(`La ubicación ${locationId} no existe en modo local`)
    }

    const days = params?.days ?? 30
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - days)

    let filtered = history.filter(entry => entry.location_id === locationId && this.parseDate(entry.created_at) >= cutoff)
    if (params?.tipo_cambio) {
      filtered = filtered.filter(entry => entry.tipo_cambio === params.tipo_cambio)
    }
    filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    if (params?.limit) {
      filtered = filtered.slice(0, params.limit)
    }
    return filtered
  }

  async getProfileStockHistory(profileId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]> {
    const [history, products] = await Promise.all([
      this.loadStockHistory(),
      this.loadProducts()
    ])

    const productIds = new Set(products.filter(product => product.profile_id === profileId).map(product => product.id))
    if (productIds.size === 0) {
      return []
    }

    const days = params?.days ?? 30
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - days)

    let filtered = history.filter(entry => productIds.has(entry.product_id) && this.parseDate(entry.created_at) >= cutoff)
    if (params?.tipo_cambio) {
      filtered = filtered.filter(entry => entry.tipo_cambio === params.tipo_cambio)
    }
    filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    if (params?.limit) {
      filtered = filtered.slice(0, params.limit)
    }
    return filtered
  }

  async createStockHistoryEntry(entry: StockHistoryCreateRequest): Promise<StockHistory> {
    const [history, products] = await Promise.all([
      this.loadStockHistory(),
      this.loadProducts()
    ])

    const product = products.find(p => p.id === entry.product_id)
    if (!product) {
      throw new Error(`Producto ${entry.product_id} no encontrado en modo local`)
    }

    const nextId = Math.max(0, ...history.map(h => h.id)) + 1
    const createdEntry: StockHistory = {
      id: nextId,
      created_at: entry.created_at || new Date().toISOString(),
      ...entry
    }

    history.push(createdEntry)
    await this.setStockHistory(history)
    await this.recordSyncEvent({
      entity: 'stock_history',
      action: 'create',
      entityId: createdEntry.id,
      payload: {
        entry: createdEntry,
        product_id: createdEntry.product_id,
        location_id: createdEntry.location_id ?? null,
        tipo_cambio: createdEntry.tipo_cambio
      }
    })
    return createdEntry
  }

  async getProductStockStats(productId: number, days = 30): Promise<StockHistoryStats> {
    const [history, products, stock] = await Promise.all([
      this.loadStockHistory(),
      this.loadProducts(),
      this.getStock()
    ])

    const product = products.find(p => p.id === productId)
    if (!product) {
      throw new Error(`Producto ${productId} no encontrado en modo local`)
    }

    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - days)

    const relevantHistory = history.filter(entry => entry.product_id === productId && this.parseDate(entry.created_at) >= cutoff)
    const movementsByType: Record<string, number> = {}
    let totalEntrada = 0
    let totalSalida = 0

    for (const record of relevantHistory) {
      movementsByType[record.tipo_cambio] = (movementsByType[record.tipo_cambio] || 0) + 1
      if (record.cantidad >= 0) {
        totalEntrada += record.cantidad
      } else {
        totalSalida += Math.abs(record.cantidad)
      }
    }

    const stockEntry = stock.find(s => s.product_id === productId)

    return {
      product_id: productId,
      product_name: product.nombre,
      period_days: days,
      total_movements: relevantHistory.length,
      movements_by_type: movementsByType,
      total_entrada: totalEntrada,
      total_salida: totalSalida,
      stock_actual: stockEntry?.cantidad_disponible || 0
    }
  }

  async getProductByIMEI(imei: string): Promise<ProductWithStock> {
    try {
      const [products, imeis] = await Promise.all([
        this.loadProducts(),
        this.loadProductIMEIs()
      ])

      const foundImei = imeis.find(i => i.imei === imei)
      if (!foundImei) {
        throw new Error(`IMEI ${imei} no encontrado`)
      }

      const product = products.find(p => p.id === foundImei.product_id)
      if (!product) {
        throw new Error(`Producto asociado al IMEI no encontrado`)
      }

      // Enriquecer con stock (simplificado para local mode)
      const stock = await this.getStock()
      const productStock = stock.filter(s => s.product_id === product.id)
      const totalStock = productStock.reduce((acc, s) => acc + s.cantidad_disponible, 0)

      return {
        ...product,
        stock_disponible: totalStock,
        stock_items: productStock
      }
    } catch (error) {
      console.error('Error getting product by IMEI:', error)
      throw error
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
    const locations = await this.loadLocations()
    if (locations.length === 0) {
      const now = new Date().toISOString()
      // BUG #4: Auto-create default location in local mode to ensure V2.0 flows work without manual setup
      const newLocation = {
        id: 1,
        nombre: 'Ubicación Principal',
        tipo: 'tienda',
        direccion: 'Por definir',
        telefono: '',
        activo: true,
        created_at: now,
        updated_at: now
      }
      await this.setLocations([newLocation])
      return [newLocation]
    }
    return locations
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

      await this.recordSyncEvent({
        entity: 'location',
        action: 'create',
        entityId: newLocation.id,
        payload: {
          location: newLocation
        }
      })
      
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

      const previousLocation = { ...locations[index] }

      const updatedLocation: Location = {
        ...locations[index],
        ...updates,
        id, // No permitir cambiar el ID
        updated_at: new Date().toISOString()
      }

      locations[index] = updatedLocation
      await this.setLocations(locations)

      await this.recordSyncEvent({
        entity: 'location',
        action: 'update',
        entityId: id,
        payload: {
          before: previousLocation,
          after: updatedLocation,
          updates
        }
      })
      return updatedLocation
    } catch (error) {
      console.error('Error updating location:', error)
      throw new Error(`Failed to update location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteLocation(id: number): Promise<void> {
    try {
      const locations = await this.loadLocations()
      const locationToDelete = locations.find(l => l.id === id)
      if (!locationToDelete) {
        console.warn(`Location ${id} not found; nothing to delete`)
        return
      }

      const filtered = locations.filter(l => l.id !== id)
      await this.setLocations(filtered)

      await this.recordSyncEvent({
        entity: 'location',
        action: 'delete',
        entityId: id,
        payload: {
          location: locationToDelete
        }
      })
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

  // FAQs (local parity for API-only feature)
  private async loadFaqs(): Promise<import('./types').FAQEntry[]> {
    try {
      const kv = getKV()
      return (await kv.get<import('./types').FAQEntry[]>(STORAGE_KEYS.FAQS)) || []
    } catch (error) {
      console.error('Error loading FAQs:', error)
      return []
    }
  }

  private async setFaqs(faqs: import('./types').FAQEntry[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.FAQS, faqs)
    } catch (error) {
      console.error('Error saving FAQs:', error)
      throw error
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
      if (!fromLocation.activo) throw new Error(`Source location ${fromLocation.nombre} is inactive`)

      const toLocation = locations.find(l => l.id === request.to_location_id)
      if (!toLocation) throw new Error(`Destination location ${request.to_location_id} not found`)
      if (!toLocation.activo) throw new Error(`Destination location ${toLocation.nombre} is inactive`)

      const stockEntry = stock.find(s => s.product_id === request.product_id && s.location_id === request.from_location_id)
      if (!stockEntry) throw new Error(`No stock entry for product ${request.product_id} at location ${request.from_location_id}`)

      const available = stockEntry.cantidad_disponible - (stockEntry.cantidad_reservada || 0)
      if (available < request.cantidad) {
        throw new Error(`Insufficient stock. Available: ${available}, Requested: ${request.cantidad}`)
      }

      // Reserve stock
      stockEntry.cantidad_reservada = (stockEntry.cantidad_reservada || 0) + request.cantidad
      const stockReservation = {
        product_id: request.product_id,
        from_location_id: request.from_location_id,
        cantidad: request.cantidad,
        stock_libre_antes: available,
        stock_libre_despues: available - request.cantidad
      }
      
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
        // V2.0 Strict Mode: If product is serialized, IMEIs MUST be specified
        // Check explicit flag first, then fallback to checking if any IMEIs exist
        if (product.is_serialized || productIMEIs.some(pi => pi.product_id === request.product_id)) {
             throw new Error("Este producto es serializado. Debe especificar los IMEIs a transferir.")
        }
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
      const imeiReservationPayload = imeisToReserve.map(imei => ({
        id: imei.id,
        imei: imei.imei,
        product_id: imei.product_id,
        location_id: imei.location_id
      }))

      // V2.0: Add Stock History (Reservation)
      const stockHistory = await this.loadStockHistory()
      const nextHistoryId = Math.max(0, ...stockHistory.map(h => h.id)) + 1
      
      const historyReserva: StockHistory = {
        id: nextHistoryId,
        product_id: request.product_id,
        location_id: request.from_location_id, // V2.0: Location ID
        tipo_cambio: 'transferencia_reserva',
        cantidad: -request.cantidad, // Negative because it reduces free stock
        stock_anterior: available,
        stock_nuevo: available - request.cantidad,
        referencia_id: newTransfer.id,
        referencia_tipo: 'transfer_pending',
        notas: `Stock reservado para transferencia a '${toLocation.nombre}': ${request.notas || 'Sin notas'}`,
        usuario: request.created_by || 'Sistema Local',
        created_at: new Date().toISOString()
      }

      await Promise.all([
        this.setStock(stock),
        this.setStockTransfers([...transfers, newTransfer]),
        this.setProductIMEIs(productIMEIs),
        this.setStockHistory([...stockHistory, historyReserva])
      ])

      await this.recordSyncEvent({
        entity: 'stock_transfer',
        action: 'create',
        entityId: newTransfer.id,
        payload: {
          transfer: newTransfer,
          stock_reservation: stockReservation,
          imeis_reserved: imeiReservationPayload,
          created_by: request.created_by || 'Sistema Local'
        }
      })

      if (imeiReservationPayload.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'assign',
          entityId: null,
          payload: {
            transfer_id: newTransfer.id,
            from_location_id: request.from_location_id,
            to_location_id: request.to_location_id,
            imeis: imeiReservationPayload
          }
        })
      }
      
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

  async confirmStockTransfer(id: number, confirmedBy: string, scannedImeis?: string[]): Promise<StockTransfer> {
    try {
      const [transfers, stock, productIMEIs, imeiHistory, stockHistory] = await Promise.all([
        this.loadStockTransfers(),
        this.getStock(),
        this.loadProductIMEIs(),
        this.loadIMEIHistory(),
        this.loadStockHistory()
      ])

      const transferIndex = transfers.findIndex(t => t.id === id)
      if (transferIndex === -1) throw new Error(`Transfer ${id} not found`)
      
      const transfer = transfers[transferIndex]
      if (transfer.estado !== 'pendiente') throw new Error(`Transfer ${id} is not pending`)

      // V2.0: Validate IMEIs if provided
      const imeisEnTransito = productIMEIs.filter(pi => pi.transfer_id === id)
      
      if (imeisEnTransito.length > 0) {
          if (scannedImeis && scannedImeis.length > 0) {
              // Verify all scanned IMEIs are in the transfer
              const transferImeiSet = new Set(imeisEnTransito.map(pi => pi.imei))
              for (const scanned of scannedImeis) {
                  if (!transferImeiSet.has(scanned)) {
                      throw new Error(`IMEI ${scanned} no es parte de esta transferencia`)
                  }
              }
              
              // Verify all transfer IMEIs are scanned
              if (scannedImeis.length !== imeisEnTransito.length) {
                   throw new Error(`Debe escanear todos los IMEIs (${imeisEnTransito.length}) para confirmar`)
              }
          } else {
              // If serialized (has imeis in transfer) and no scanned imeis provided
              throw new Error("Este producto es serializado. Debe escanear los IMEIs recibidos para confirmar la transferencia.")
          }
      }

      // Update stock
      const fromStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.from_location_id)
      if (!fromStock) throw new Error(`Source stock not found`)

      const sourceReservadaAntes = fromStock.cantidad_reservada || 0
      const sourceDisponibleAntes = fromStock.cantidad_disponible
      const stockLibreOrigenAntes = sourceDisponibleAntes - sourceReservadaAntes

      // Release reservation and decrease stock
      fromStock.cantidad_reservada = sourceReservadaAntes - transfer.cantidad
      fromStock.cantidad_disponible = sourceDisponibleAntes - transfer.cantidad

      const stockLibreOrigenDespues = fromStock.cantidad_disponible - (fromStock.cantidad_reservada || 0)

      // Increase destination stock
      let toStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.to_location_id)
      let destinationDisponibleAntes = 0
      let destinationReservadaAntes = 0

      if (!toStock) {
        toStock = {
          id: Math.max(0, ...stock.map(s => s.id)) + 1,
          product_id: transfer.product_id,
          location_id: transfer.to_location_id,
          cantidad_disponible: 0,
          cantidad_reservada: 0
        }
        stock.push(toStock)
      } else {
        destinationDisponibleAntes = toStock.cantidad_disponible
        destinationReservadaAntes = toStock.cantidad_reservada || 0
      }

      const stockLibreDestinoAntes = destinationDisponibleAntes - destinationReservadaAntes
      toStock.cantidad_disponible += transfer.cantidad
      const stockLibreDestinoDespues = toStock.cantidad_disponible - (toStock.cantidad_reservada || 0)

      const nextHistoryId = Math.max(0, ...stockHistory.map(h => h.id)) + 1
      
      const historySalida: StockHistory = {
        id: nextHistoryId,
        product_id: transfer.product_id,
        location_id: transfer.from_location_id,
        tipo_cambio: 'transferencia_salida',
        cantidad: -transfer.cantidad,
        stock_anterior: stockLibreOrigenAntes,
        stock_nuevo: stockLibreOrigenDespues,
        referencia_id: transfer.id,
        referencia_tipo: 'transfer',
        notas: `Transferencia a ${transfer.to_location_name}: ${transfer.notas || ''}`,
        usuario: confirmedBy,
        created_at: new Date().toISOString()
      }

      const historyEntrada: StockHistory = {
        id: nextHistoryId + 1,
        product_id: transfer.product_id,
        location_id: transfer.to_location_id,
        tipo_cambio: 'transferencia_entrada',
        cantidad: transfer.cantidad,
        stock_anterior: stockLibreDestinoAntes,
        stock_nuevo: stockLibreDestinoDespues,
        referencia_id: transfer.id,
        referencia_tipo: 'transfer',
        notas: `Transferencia desde ${transfer.from_location_name}: ${transfer.notas || ''}`,
        usuario: confirmedBy,
        created_at: new Date().toISOString()
      }

      const newIMEIHistory: IMEIHistory[] = []

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

        // V2.0: Add IMEI History (Transfer)
        newIMEIHistory.push({
            id: Math.max(0, ...imeiHistory.map(h => h.id), ...newIMEIHistory.map(h => h.id)) + 1,
            imei: imei.imei,
            product_id: transfer.product_id,
            location_id: transfer.to_location_id,
            event_type: 'transferencia',
            reference_id: transfer.id,
            reference_type: 'transfer',
            notes: `Transferencia confirmada de ${transfer.from_location_name} a ${transfer.to_location_name}`,
            created_by: confirmedBy,
            created_at: new Date().toISOString()
        })
      }

      // Update transfer status
      const updatedTransfer = {
        ...transfer,
        estado: 'confirmada' as const,
        confirmed_at: new Date().toISOString(),
        confirmed_by: confirmedBy
      }
      transfers[transferIndex] = updatedTransfer

      const stockAdjustments = [
        {
          type: 'source',
          location_id: transfer.from_location_id,
          cantidad: -transfer.cantidad,
          stock_libre_antes: stockLibreOrigenAntes,
          stock_libre_despues: stockLibreOrigenDespues
        },
        {
          type: 'destination',
          location_id: transfer.to_location_id,
          cantidad: transfer.cantidad,
          stock_libre_antes: stockLibreDestinoAntes,
          stock_libre_despues: stockLibreDestinoDespues
        }
      ]

      const imeiMovementPayload = imeisToMove.map(imei => ({
        imei: imei.imei,
        product_id: imei.product_id,
        from_location_id: transfer.from_location_id,
        to_location_id: transfer.to_location_id
      }))

      await Promise.all([
        this.setStock(stock),
        this.setStockTransfers(transfers),
        this.setProductIMEIs(productIMEIs),
        this.setIMEIHistory([...imeiHistory, ...newIMEIHistory]),
        this.setStockHistory([...stockHistory, historySalida, historyEntrada])
      ])

      await this.recordSyncEvent({
        entity: 'stock_transfer',
        action: 'confirm',
        entityId: id,
        payload: {
          transfer: updatedTransfer,
          stock_adjustments: stockAdjustments,
          imei_movements: imeiMovementPayload,
          scanned_imeis: scannedImeis || null,
          confirmed_by: confirmedBy
        }
      })

      if (imeiMovementPayload.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'transfer',
          entityId: null,
          payload: {
            transfer_id: id,
            movements: imeiMovementPayload,
            confirmed_by: confirmedBy
          }
        })
      }

      return updatedTransfer
    } catch (error) {
      console.error('Error confirming transfer:', error)
      throw new Error(`Failed to confirm transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async rejectStockTransfer(id: number, rejectedBy: string, rejectionReason?: string): Promise<StockTransfer> {
    try {
      const [transfers, stock, productIMEIs, stockHistory] = await Promise.all([
        this.loadStockTransfers(),
        this.getStock(),
        this.loadProductIMEIs(),
        this.loadStockHistory()
      ])

      const transferIndex = transfers.findIndex(t => t.id === id)
      if (transferIndex === -1) throw new Error(`Transfer ${id} not found`)
      
      const transfer = transfers[transferIndex]
      if (transfer.estado !== 'pendiente') throw new Error(`Transfer ${id} is not pending`)

      // Release reservation
      const fromStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.from_location_id)
      let stockRelease: {
        location_id: number
        cantidad: number
        stock_libre_antes: number
        stock_libre_despues: number
      } | null = null

      if (fromStock) {
        const stockLibreAntes = fromStock.cantidad_disponible - (fromStock.cantidad_reservada || 0)
        fromStock.cantidad_reservada = Math.max(0, (fromStock.cantidad_reservada || 0) - transfer.cantidad)
        const stockLibreDespues = fromStock.cantidad_disponible - (fromStock.cantidad_reservada || 0)

        stockHistory.push({
          id: Math.max(0, ...stockHistory.map(h => h.id)) + 1,
          product_id: transfer.product_id,
          location_id: transfer.from_location_id,
          tipo_cambio: 'transferencia_rechazada',
          cantidad: transfer.cantidad,
          stock_anterior: stockLibreAntes,
          stock_nuevo: stockLibreDespues,
          referencia_id: transfer.id,
          referencia_tipo: 'transfer_rejected',
          notas: `Transferencia rechazada: ${rejectionReason || 'Sin motivo'}`,
          usuario: rejectedBy,
          created_at: new Date().toISOString()
        })

        stockRelease = {
          location_id: transfer.from_location_id,
          cantidad: transfer.cantidad,
          stock_libre_antes: stockLibreAntes,
          stock_libre_despues: stockLibreDespues
        }
      }

      // Release IMEIs
      const imeisReserved = productIMEIs.filter(pi => pi.transfer_id === id)
      for (const imei of imeisReserved) {
        imei.transfer_id = undefined
      }
      const imeiReleasePayload = imeisReserved.map(imei => ({
        imei: imei.imei,
        product_id: imei.product_id,
        location_id: imei.location_id
      }))

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
        this.setProductIMEIs(productIMEIs),
        this.setStockHistory(stockHistory)
      ])

      await this.recordSyncEvent({
        entity: 'stock_transfer',
        action: 'reject',
        entityId: id,
        payload: {
          transfer: updatedTransfer,
          stock_release: stockRelease,
          imeis_released: imeiReleasePayload,
          rejected_by: rejectedBy,
          rejection_reason: rejectionReason || null
        }
      })

      if (imeiReleasePayload.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'cancel',
          entityId: null,
          payload: {
            transfer_id: id,
            imeis: imeiReleasePayload,
            rejected_by: rejectedBy,
            reason: rejectionReason || null
          }
        })
      }

      return updatedTransfer
    } catch (error) {
      console.error('Error rejecting transfer:', error)
      throw new Error(`Failed to reject transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async cancelStockTransfer(id: number): Promise<void> {
    try {
      const [transfers, stock, productIMEIs, stockHistory] = await Promise.all([
        this.loadStockTransfers(),
        this.getStock(),
        this.loadProductIMEIs(),
        this.loadStockHistory()
      ])

      const transferIndex = transfers.findIndex(t => t.id === id)
      if (transferIndex === -1) throw new Error(`Transfer ${id} not found`)
      
      const transfer = transfers[transferIndex]
      if (transfer.estado !== 'pendiente') throw new Error(`Transfer ${id} is not pending`)

      // Release reservation
      const fromStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.from_location_id)
      let stockRelease: {
        location_id: number
        cantidad: number
        stock_libre_antes: number
        stock_libre_despues: number
      } | null = null

      if (fromStock) {
        const stockLibreAntes = fromStock.cantidad_disponible - (fromStock.cantidad_reservada || 0)
        fromStock.cantidad_reservada = Math.max(0, (fromStock.cantidad_reservada || 0) - transfer.cantidad)
        const stockLibreDespues = fromStock.cantidad_disponible - (fromStock.cantidad_reservada || 0)

        stockHistory.push({
          id: Math.max(0, ...stockHistory.map(h => h.id)) + 1,
          product_id: transfer.product_id,
          location_id: transfer.from_location_id,
          tipo_cambio: 'transferencia_cancelada',
          cantidad: transfer.cantidad,
          stock_anterior: stockLibreAntes,
          stock_nuevo: stockLibreDespues,
          referencia_id: transfer.id,
          referencia_tipo: 'transfer_cancelled',
          notas: `Transferencia cancelada: ${transfer.notas || 'Sin notas'}`,
          usuario: 'Sistema Local',
          created_at: new Date().toISOString()
        })

        stockRelease = {
          location_id: transfer.from_location_id,
          cantidad: transfer.cantidad,
          stock_libre_antes: stockLibreAntes,
          stock_libre_despues: stockLibreDespues
        }
      }

      // Release IMEIs
      const imeisReserved = productIMEIs.filter(pi => pi.transfer_id === id)
      for (const imei of imeisReserved) {
        imei.transfer_id = undefined
      }
      const imeiReleasePayload = imeisReserved.map(imei => ({
        imei: imei.imei,
        product_id: imei.product_id,
        location_id: imei.location_id
      }))

      // Update transfer status
      const updatedTransfer = {
        ...transfer,
        estado: 'cancelada' as const
      }
      transfers[transferIndex] = updatedTransfer

      await Promise.all([
        this.setStock(stock),
        this.setStockTransfers(transfers),
        this.setProductIMEIs(productIMEIs),
        this.setStockHistory(stockHistory)
      ])

      await this.recordSyncEvent({
        entity: 'stock_transfer',
        action: 'cancel',
        entityId: id,
        payload: {
          transfer: updatedTransfer,
          stock_release: stockRelease,
          imeis_released: imeiReleasePayload
        }
      })

      if (imeiReleasePayload.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'cancel',
          entityId: null,
          payload: {
            transfer_id: id,
            imeis: imeiReleasePayload
          }
        })
      }
    } catch (error) {
      console.error('Error canceling transfer:', error)
      throw new Error(`Failed to cancel transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listFAQs(params?: { activa?: boolean, categoria?: string, page?: number, per_page?: number }): Promise<{ items: import('./types').FAQEntry[], total: number, pages: number }> {
    const faqs = await this.loadFaqs()
    let filtered = [...faqs]

    if (params?.activa !== undefined) {
      filtered = filtered.filter(f => f.activa === params.activa)
    }
    if (params?.categoria) {
      const categoryLower = params.categoria.toLowerCase()
      filtered = filtered.filter(f => (f.categoria || '').toLowerCase() === categoryLower)
    }

    const perPage = params?.per_page || filtered.length || 1
    const page = params?.page || 1
    const start = (page - 1) * perPage
    const items = filtered.slice(start, start + perPage)

    return {
      items,
      total: filtered.length,
      pages: Math.max(1, Math.ceil(filtered.length / perPage))
    }
  }

  async createFAQ(faq: Omit<import('./types').FAQEntry, 'id' | 'created_at' | 'updated_at' | 'veces_usada'>): Promise<import('./types').FAQEntry> {
    const faqs = await this.loadFaqs()
    const now = new Date().toISOString()
    const newFaq = {
      ...faq,
      id: Math.max(0, ...faqs.map(f => f.id || 0)) + 1,
      created_at: now,
      updated_at: now,
      veces_usada: 0
    }
    await this.setFaqs([...faqs, newFaq])

    await this.recordSyncEvent({
      entity: 'faq',
      action: 'create',
      entityId: newFaq.id,
      payload: {
        faq: newFaq
      }
    })
    return newFaq
  }

  async updateFAQ(id: number, updates: Partial<import('./types').FAQEntry>): Promise<import('./types').FAQEntry> {
    const faqs = await this.loadFaqs()
    const index = faqs.findIndex(f => f.id === id)
    if (index === -1) {
      throw new Error(`FAQ ${id} no encontrada`)
    }
    const previousFaq = { ...faqs[index] }
    const updated = {
      ...previousFaq,
      ...updates,
      id,
      updated_at: new Date().toISOString()
    }
    faqs[index] = updated
    await this.setFaqs(faqs)

    await this.recordSyncEvent({
      entity: 'faq',
      action: 'update',
      entityId: id,
      payload: {
        before: previousFaq,
        after: updated,
        updates
      }
    })
    return updated
  }

  async deleteFAQ(id: number): Promise<void> {
    const faqs = await this.loadFaqs()
    const faqToDelete = faqs.find(f => f.id === id)
    const filtered = faqs.filter(f => f.id !== id)
    await this.setFaqs(filtered)

    if (faqToDelete) {
      await this.recordSyncEvent({
        entity: 'faq',
        action: 'delete',
        entityId: id,
        payload: {
          faq: faqToDelete
        }
      })
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

  private async setSuppliers(suppliers: Supplier[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.SUPPLIERS, suppliers)
    } catch (error) {
      console.error('Error saving suppliers:', error)
      throw new Error(`Failed to save suppliers: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createSupplier(supplier: Omit<Supplier, 'id' | 'created_at' | 'updated_at'>): Promise<Supplier> {
    try {
      const suppliers = await this.loadSuppliers()
      const nextId = suppliers.length > 0 ? Math.max(...suppliers.map(s => s.id)) + 1 : 1
      
      const now = new Date().toISOString()
      const newSupplier: Supplier = {
        ...supplier,
        id: nextId,
        created_at: now,
        updated_at: now
      }

      await this.setSuppliers([...suppliers, newSupplier])
      await this.recordSyncEvent({
        entity: 'supplier',
        action: 'create',
        entityId: newSupplier.id,
        payload: {
          supplier: newSupplier
        }
      })
      return newSupplier
    } catch (error) {
      console.error('Error creating supplier:', error)
      throw new Error(`Failed to create supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateSupplier(id: number, updates: Partial<Supplier>): Promise<Supplier> {
    try {
      const suppliers = await this.loadSuppliers()
      const index = suppliers.findIndex(s => s.id === id)
      
      if (index === -1) {
        throw new Error(`Supplier with ID ${id} not found`)
      }

      const previousSupplier = { ...suppliers[index] }
      const updatedSupplier: Supplier = {
        ...previousSupplier,
        ...updates,
        id,
        updated_at: new Date().toISOString()
      }

      suppliers[index] = updatedSupplier
      await this.setSuppliers(suppliers)
      await this.recordSyncEvent({
        entity: 'supplier',
        action: 'update',
        entityId: id,
        payload: {
          before: previousSupplier,
          after: updatedSupplier,
          updates
        }
      })
      return updatedSupplier
    } catch (error) {
      console.error('Error updating supplier:', error)
      throw new Error(`Failed to update supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteSupplier(id: number): Promise<void> {
    try {
      const suppliers = await this.loadSuppliers()
      const supplierToDelete = suppliers.find(s => s.id === id)
      const filtered = suppliers.filter(s => s.id !== id)
      await this.setSuppliers(filtered)

      if (supplierToDelete) {
        await this.recordSyncEvent({
          entity: 'supplier',
          action: 'delete',
          entityId: id,
          payload: {
            supplier: supplierToDelete
          }
        })
      }
    } catch (error) {
      console.error('Error deleting supplier:', error)
      throw new Error(`Failed to delete supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
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

      await this.recordSyncEvent({
        entity: 'sales_profile',
        action: 'create',
        entityId: newProfile.id,
        payload: {
          profile: newProfile
        }
      })
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

      const previousProfile = { ...profiles[index] }

      const updatedProfile: SalesProfile = {
        ...profiles[index],
        ...updates,
        id,
        updated_at: new Date().toISOString()
      }

      profiles[index] = updatedProfile
      await this.setSalesProfiles(profiles)

      await this.recordSyncEvent({
        entity: 'sales_profile',
        action: 'update',
        entityId: id,
        payload: {
          before: previousProfile,
          after: updatedProfile,
          updates
        }
      })
      return updatedProfile
    } catch (error) {
      console.error('Error updating sales profile:', error)
      throw new Error(`Failed to update sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteSalesProfile(id: number): Promise<void> {
    try {
      const profiles = await this.loadSalesProfiles()
      const profileToDelete = profiles.find(p => p.id === id)
      if (!profileToDelete) {
        console.warn(`Sales profile ${id} not found; nothing to delete`)
        return
      }

      const filtered = profiles.filter(p => p.id !== id)
      await this.setSalesProfiles(filtered)

      await this.recordSyncEvent({
        entity: 'sales_profile',
        action: 'delete',
        entityId: id,
        payload: {
          profile: profileToDelete
        }
      })
    } catch (error) {
      console.error('Error deleting sales profile:', error)
      throw new Error(`Failed to delete sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  private async loadReturns(): Promise<Return[]> {
    try {
      const kv = getKV()
      const data = await kv.get<Return[]>(STORAGE_KEYS.RETURNS)
      return data || []
    } catch (error) {
      console.error('Error loading returns:', error)
      return []
    }
  }

  private async setReturns(returns: Return[]): Promise<void> {
    try {
      const kv = getKV()
      await kv.set(STORAGE_KEYS.RETURNS, returns)
    } catch (error) {
      console.error('Error saving returns:', error)
      throw error
    }
  }

  async getReturns(): Promise<Return[]> {
    return this.loadReturns()
  }

  async createReturn(request: CreateReturnRequest): Promise<Return> {
    try {
      const [returns, orders, stock, stockHistory, imeis, imeiHistory] = await Promise.all([
        this.loadReturns(),
        this.loadOrders(),
        this.getStock(),
        this.loadStockHistory(),
        this.loadProductIMEIs(),
        this.loadIMEIHistory()
      ])

      const order = orders.find(o => o.id === request.order_id)
      if (!order) {
        throw new Error(`Order ${request.order_id} not found`)
      }

      const nextReturnId = Math.max(0, ...returns.map(r => r.id)) + 1
      const now = new Date().toISOString()

      const newReturn: Return = {
        id: nextReturnId,
        order_id: request.order_id,
        created_at: now,
        reason: request.reason,
        status: 'completed',
        created_by: request.created_by,
        items: request.items.map((item, index) => ({
          ...item,
          id: index + 1
        }))
      }

      // Process stock updates
      const updatedStock = [...stock]
      const newStockHistory = [...stockHistory]
      const updatedIMEIs = [...imeis]
      const updatedIMEIHistory = [...imeiHistory]
      const stockAdjustments: Array<{
        product_id: number
        location_id: number
        field: 'cantidad_disponible' | 'cantidad_defectuosa'
        cantidad: number
        stock_anterior: number
        stock_nuevo: number
        condition: ReturnItem['condition']
      }> = []
      const imeiEvents: Array<{
        imei: string
        product_id: number
        location_id: number
        condition: ReturnItem['condition']
        action: ReturnItem['action']
      }> = []

      for (const item of request.items) {
        if (item.action === 'refund' || item.action === 'warranty_exchange') {
          const locationId = order.source_location_id
          if (!locationId) continue

          const stockEntry = updatedStock.find(s => s.product_id === item.product_id && s.location_id === locationId)
          
          const isDefective = item.condition === 'defectuoso'
          const stockField: 'cantidad_disponible' | 'cantidad_defectuosa' = isDefective
            ? 'cantidad_defectuosa'
            : 'cantidad_disponible'

          let stockAnterior = 0
          let stockNuevo = item.quantity

          if (stockEntry) {
            stockAnterior = stockEntry[stockField] || 0
            stockEntry[stockField] = (stockEntry[stockField] || 0) + item.quantity
            stockNuevo = stockEntry[stockField]
          } else {
            const nextStockId = Math.max(0, ...updatedStock.map(s => s.id)) + 1
            const newEntry: Stock = {
              id: nextStockId,
              product_id: item.product_id,
              location_id: locationId,
              cantidad_disponible: isDefective ? 0 : item.quantity,
              cantidad_reservada: 0,
              cantidad_defectuosa: isDefective ? item.quantity : 0
            }
            updatedStock.push(newEntry)
            stockNuevo = newEntry[stockField]
          }

          stockAdjustments.push({
            product_id: item.product_id,
            location_id,
            field: stockField,
            cantidad: item.quantity,
            stock_anterior: stockAnterior,
            stock_nuevo: stockNuevo,
            condition: item.condition
          })

          const nextHistoryId = Math.max(0, ...newStockHistory.map(h => h.id)) + 1
          newStockHistory.push({
            id: nextHistoryId,
            product_id: item.product_id,
            location_id: locationId,
            tipo_cambio: 'devolucion',
            cantidad: item.quantity,
            stock_anterior: stockAnterior,
            stock_nuevo: stockNuevo,
            referencia_id: nextReturnId,
            referencia_tipo: 'return',
            notas: `Devolución orden #${order.id}: ${item.condition}`,
            usuario: request.created_by || 'Sistema Local',
            created_at: now
          })

          // Update IMEI if present
          if (item.imei) {
            const imeiRecord = updatedIMEIs.find(i => i.imei === item.imei)
            if (imeiRecord) {
              imeiRecord.vendido = false
              imeiRecord.order_id = undefined

              // Add IMEI History
              const nextIMEIHistoryId = Math.max(0, ...updatedIMEIHistory.map(h => h.id)) + 1
              updatedIMEIHistory.push({
                id: nextIMEIHistoryId,
                imei: item.imei,
                product_id: item.product_id,
                location_id: locationId,
                event_type: 'devolucion',
                reference_id: nextReturnId,
                reference_type: 'return',
                notes: `Devolución orden #${order.id}: ${item.condition}`,
                created_at: now,
                created_by: request.created_by || 'Sistema Local'
              })

              imeiEvents.push({
                imei: item.imei,
                product_id: item.product_id,
                location_id,
                condition: item.condition,
                action: item.action
              })
            }
          }
        }
      }

      await this.setReturns([...returns, newReturn])
      await this.setStock(updatedStock)
      await this.setStockHistory(newStockHistory)
      await this.setProductIMEIs(updatedIMEIs)
      await this.setIMEIHistory(updatedIMEIHistory)

      await this.recordSyncEvent({
        entity: 'return',
        action: 'create',
        entityId: nextReturnId,
        payload: {
          return: newReturn,
          order_id: order.id,
          stock_adjustments: stockAdjustments,
          imei_events: imeiEvents
        }
      })

      if (imeiEvents.length > 0) {
        await this.recordSyncEvent({
          entity: 'imei',
          action: 'update',
          entityId: null,
          payload: {
            return_id: nextReturnId,
            order_id: order.id,
            events: imeiEvents
          }
        })
      }

      return newReturn
    } catch (error) {
      console.error('Error creating return:', error)
      throw new Error(`Failed to create return: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getIMEIHistory(imei: string): Promise<IMEIHistory[]> {
    try {
      const history = await this.loadIMEIHistory()
      return history.filter(h => h.imei === imei).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } catch (error) {
      console.error('Error getting IMEI history:', error)
      return []
    }
  }

  async checkWarrantyStatus(imei: string): Promise<WarrantyStatus> {
    return {
      imei,
      status: 'sin_garantia',
      detail: 'Funcionalidad solo disponible en modo API'
    }
  }

  // --- Reports & Analytics (Local Mode Fallback) ---

  private parseDate(value?: string): Date {
    if (!value) return new Date()
    const parsed = new Date(value)
    return Number.isNaN(parsed.getTime()) ? new Date() : parsed
  }

  private toOrderSummary(order: Order): OrderSummary {
    return {
      id: order.id,
      profile_id: order.profile_id,
      sales_profile_id: order.sales_profile_id,
      source_location_id: order.source_location_id,
      customer_name: order.customer_name,
      customer_phone: order.customer_phone,
      canal: order.canal,
      metodo_pago: order.metodo_pago,
      total: order.total,
      estado: order.estado,
      notes: order.notes ?? order.notas,
      delivery_date: order.delivery_date,
      created_at: order.created_at
    }
  }

  private aggregateCustomerStats(orders: Order[]): Map<string, {
    phone: string
    name: string
    totalOrders: number
    totalSpent: number
    completedOrders: number
    firstOrder?: string
    lastOrder?: string
  }> {
    const stats = new Map<string, {
      phone: string
      name: string
      totalOrders: number
      totalSpent: number
      completedOrders: number
      firstOrder?: string
      lastOrder?: string
    }>()

    for (const order of orders) {
      const phone = order.customer_phone
      if (!stats.has(phone)) {
        stats.set(phone, {
          phone,
          name: order.customer_name,
          totalOrders: 0,
          totalSpent: 0,
          completedOrders: 0,
          firstOrder: order.created_at,
          lastOrder: order.created_at
        })
      }

      const entry = stats.get(phone)!
      entry.totalOrders += 1
      if (order.estado !== 'cancelada') {
        entry.totalSpent += order.total || 0
        entry.completedOrders += 1
      }

      const createdAt = this.parseDate(order.created_at).toISOString()
      if (!entry.firstOrder || createdAt < entry.firstOrder) {
        entry.firstOrder = createdAt
      }
      if (!entry.lastOrder || createdAt > entry.lastOrder) {
        entry.lastOrder = createdAt
      }
      if (!entry.name && order.customer_name) {
        entry.name = order.customer_name
      }
    }

    return stats
  }

  async getDashboardStats(params?: { sales_profile_slug?: string; location_id?: number }): Promise<DashboardStats> {
    const [products, stock, ordersWithItems, salesProfiles, locations] = await Promise.all([
      this.loadProducts(),
      this.getStock(),
      this.loadOrdersWithItems(),
      this.getSalesProfiles(),
      this.loadLocations()
    ])

    const productMap = new Map(products.map(product => [product.id, product]))
    let stockEntries = stock.filter(entry => {
      const product = productMap.get(entry.product_id)
      return product?.activo
    })

    if (params?.location_id) {
      const locationExists = locations.some(location => location.id === params.location_id)
      if (!locationExists) {
        throw new Error(`La ubicación ${params.location_id} no existe en modo local`)
      }
      stockEntries = stockEntries.filter(entry => entry.location_id === params.location_id)
    }

    let filteredOrders = [...ordersWithItems]
    if (params?.sales_profile_slug) {
      const profile = salesProfiles.find(sp => sp.slug === params.sales_profile_slug && sp.active)
      if (!profile) {
        throw new Error(`El perfil de ventas ${params.sales_profile_slug} no existe o está inactivo en modo local`)
      }
      filteredOrders = filteredOrders.filter(order => order.sales_profile_id === profile.id)
    }

    const now = new Date()
    const startOfToday = new Date(now)
    startOfToday.setHours(0, 0, 0, 0)
    const endOfToday = new Date(now)
    endOfToday.setHours(23, 59, 59, 999)
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
    const startOfLastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const endOfLastMonth = new Date(now.getFullYear(), now.getMonth(), 0)
    endOfLastMonth.setHours(23, 59, 59, 999)

    const nonCancelledOrders = filteredOrders.filter(order => order.estado !== 'cancelada')
    const getOrderDate = (order: Order): Date => this.parseDate(order.created_at)

    const ordersToday = nonCancelledOrders.filter(order => {
      const createdAt = getOrderDate(order)
      return createdAt >= startOfToday && createdAt <= endOfToday
    })

    const ordersThisMonth = nonCancelledOrders.filter(order => getOrderDate(order) >= startOfMonth)
    const ordersLastMonth = nonCancelledOrders.filter(order => {
      const createdAt = getOrderDate(order)
      return createdAt >= startOfLastMonth && createdAt <= endOfLastMonth
    })

    const totalRevenueToday = ordersToday.reduce((sum, order) => sum + (order.total || 0), 0)
    const totalRevenueMonth = ordersThisMonth.reduce((sum, order) => sum + (order.total || 0), 0)
    const totalRevenueLastMonth = ordersLastMonth.reduce((sum, order) => sum + (order.total || 0), 0)

    let totalCostMonth = 0
    for (const order of ordersThisMonth) {
      for (const item of order.items) {
        const product = productMap.get(item.product_id)
        const unitCost = product?.costo && product.costo > 0 ? product.costo : 0
        totalCostMonth += unitCost * item.cantidad
      }
    }

    const grossMarginMonth = totalRevenueMonth > 0
      ? Number((((totalRevenueMonth - totalCostMonth) / totalRevenueMonth) * 100).toFixed(2))
      : 0

    const averageTicketMonth = ordersThisMonth.length > 0
      ? Number((totalRevenueMonth / ordersThisMonth.length).toFixed(2))
      : 0

    const low_stock_count = stockEntries.filter(entry => entry.cantidad_disponible > 0 && entry.cantidad_disponible < 10).length
    const out_of_stock_count = stockEntries.filter(entry => entry.cantidad_disponible === 0).length

    const total_inventory_value = stockEntries.reduce((sum, entry) => {
      const product = productMap.get(entry.product_id)
      if (!product) return sum
      const unitValue = product.costo && product.costo > 0 ? product.costo : product.precio
      return sum + unitValue * entry.cantidad_disponible
    }, 0)

    return {
      active_products: products.filter(product => product.activo).length,
      total_products: products.length,
      low_stock_count,
      out_of_stock_count,
      total_inventory_value,
      pending_orders: filteredOrders.filter(order => order.estado === 'pendiente').length,
      total_orders_today: ordersToday.length,
      total_revenue_today: totalRevenueToday,
      total_revenue_month: totalRevenueMonth,
      total_revenue_last_month: totalRevenueLastMonth,
      gross_margin_month: grossMarginMonth,
      average_ticket_month: averageTicketMonth
    }
  }

  async getSalesReport(params?: {
    sales_profile_slug?: string
    date_from?: string
    date_to?: string
    top_limit?: number
  }): Promise<SalesReport> {
    const [ordersWithItems, salesProfiles, products] = await Promise.all([
      this.loadOrdersWithItems(),
      this.getSalesProfiles(),
      this.loadProducts()
    ])

    const productMap = new Map(products.map(product => [product.id, product]))

    let filteredOrders = ordersWithItems.filter(order => order.estado !== 'cancelada')

    if (params?.sales_profile_slug) {
      const profile = salesProfiles.find(sp => sp.slug === params.sales_profile_slug && sp.active)
      if (!profile) {
        throw new Error(`El perfil de ventas ${params.sales_profile_slug} no existe o está inactivo en modo local`)
      }
      filteredOrders = filteredOrders.filter(order => order.sales_profile_id === profile.id)
    }

    const endDate = params?.date_to ? this.parseDate(params.date_to) : new Date()
    endDate.setHours(23, 59, 59, 999)
    const defaultStart = new Date(endDate)
    defaultStart.setDate(defaultStart.getDate() - 30)
    defaultStart.setHours(0, 0, 0, 0)
    const startDate = params?.date_from ? this.parseDate(params.date_from) : defaultStart
    startDate.setHours(0, 0, 0, 0)

    filteredOrders = filteredOrders.filter(order => {
      const createdAt = this.parseDate(order.created_at)
      return createdAt >= startDate && createdAt <= endDate
    })

    const totalRevenue = filteredOrders.reduce((sum, order) => sum + (order.total || 0), 0)
    const totalOrders = filteredOrders.length
    const averageOrderValue = totalOrders > 0 ? Number((totalRevenue / totalOrders).toFixed(2)) : 0

    const productAggregates = new Map<number, { units: number; revenue: number; product: Product | undefined }>()
    for (const order of filteredOrders) {
      for (const item of order.items) {
        if (!productAggregates.has(item.product_id)) {
          productAggregates.set(item.product_id, {
            units: 0,
            revenue: 0,
            product: productMap.get(item.product_id)
          })
        }
        const aggregate = productAggregates.get(item.product_id)!
        aggregate.units += item.cantidad
        if (!item.es_regalo_promocion) {
          aggregate.revenue += item.precio_unitario * item.cantidad
        }
      }
    }

    const topLimit = params?.top_limit ? Math.min(Math.max(params.top_limit, 1), 50) : 10
    const topProducts = Array.from(productAggregates.values())
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, topLimit)
      .map(entry => ({
        product_id: entry.product?.id || 0,
        product_name: entry.product?.nombre || 'Producto desconocido',
        units_sold: entry.units,
        total_revenue: entry.revenue
      }))

    return {
      period_start: startDate.toISOString(),
      period_end: endDate.toISOString(),
      total_orders: totalOrders,
      total_revenue: totalRevenue,
      average_order_value: averageOrderValue,
      top_products: topProducts
    }
  }

  async getInventoryAlerts(params?: { location_id?: number }): Promise<InventoryAlert[]> {
    const [stock, products, locations] = await Promise.all([
      this.getStock(),
      this.loadProducts(),
      this.loadLocations()
    ])

    const productMap = new Map(products.map(product => [product.id, product]))
    let stockEntries = stock.filter(entry => {
      const product = productMap.get(entry.product_id)
      return product?.activo
    })

    if (params?.location_id) {
      const locationExists = locations.some(location => location.id === params.location_id)
      if (!locationExists) {
        throw new Error(`La ubicación ${params.location_id} no existe en modo local`)
      }
      stockEntries = stockEntries.filter(entry => entry.location_id === params.location_id)
    }

    const alerts: InventoryAlert[] = []
    for (const entry of stockEntries) {
      const product = productMap.get(entry.product_id)
      if (!product) continue

      let alert_level: InventoryAlert['alert_level'] | null = null
      if (entry.cantidad_disponible === 0) {
        alert_level = 'out_of_stock'
      } else if (entry.cantidad_disponible < 5) {
        alert_level = 'critical'
      } else if (entry.cantidad_disponible < 10) {
        alert_level = 'low'
      }

      if (alert_level) {
        alerts.push({
          product_id: product.id,
          product_name: product.nombre,
          sku: product.sku,
          current_stock: entry.cantidad_disponible,
          category: product.categoria,
          alert_level
        })
      }
    }

    const severityOrder: Record<InventoryAlert['alert_level'], number> = {
      out_of_stock: 0,
      critical: 1,
      low: 2
    }

    alerts.sort((a, b) => severityOrder[a.alert_level] - severityOrder[b.alert_level])
    return alerts
  }

  async getStockSummaryByLocation(activeOnly = true): Promise<StockSummaryByLocation[]> {
    const [locations, stock, products] = await Promise.all([
      this.loadLocations(),
      this.getStock(),
      this.loadProducts()
    ])

    const productMap = new Map(products.map(product => [product.id, product]))
    const summaries = new Map<number, {
      uniqueProducts: Set<number>
      totalUnits: number
      inventoryValue: number
    }>()

    for (const entry of stock) {
      const product = productMap.get(entry.product_id)
      if (!product || !product.activo) continue
      const locationId = entry.location_id
      if (!locationId) continue
      const location = locations.find(loc => loc.id === locationId)
      if (!location) continue
      if (activeOnly && !location.activo) continue

      if (!summaries.has(locationId)) {
        summaries.set(locationId, {
          uniqueProducts: new Set<number>(),
          totalUnits: 0,
          inventoryValue: 0
        })
      }

      const summary = summaries.get(locationId)!
      summary.uniqueProducts.add(entry.product_id)
      summary.totalUnits += entry.cantidad_disponible
      const unitValue = product.precio
      summary.inventoryValue += unitValue * entry.cantidad_disponible
    }

    return Array.from(summaries.entries()).map(([locationId, summary]) => {
      const location = locations.find(loc => loc.id === locationId)!
      return {
        location_id: locationId,
        location_nombre: location.nombre,
        location_tipo: location.tipo,
        total_productos: summary.uniqueProducts.size,
        total_unidades: summary.totalUnits,
        valor_inventario: summary.inventoryValue
      }
    })
  }

  async getSalesSummaryByLocation(params?: { start_date?: string; end_date?: string }): Promise<SalesSummaryByLocation[]> {
    const [ordersWithItems, locations] = await Promise.all([
      this.loadOrdersWithItems(),
      this.loadLocations()
    ])

    const completedOrders = ordersWithItems.filter(order => order.estado === 'completada')
    const startDate = params?.start_date ? this.parseDate(params.start_date) : undefined
    const endDate = params?.end_date ? this.parseDate(`${params.end_date}T23:59:59`) : undefined

    const relevantOrders = completedOrders.filter(order => {
      const createdAt = this.parseDate(order.created_at)
      if (startDate && createdAt < startDate) return false
      if (endDate && createdAt > endDate) return false
      return Boolean(order.source_location_id)
    })

    const summaries = new Map<number, {
      orderIds: Set<number>
      units: number
      revenue: number
    }>()

    for (const order of relevantOrders) {
      const locationId = order.source_location_id!
      if (!summaries.has(locationId)) {
        summaries.set(locationId, {
          orderIds: new Set<number>(),
          units: 0,
          revenue: 0
        })
      }

      const summary = summaries.get(locationId)!
      summary.orderIds.add(order.id)
      for (const item of order.items) {
        summary.units += item.cantidad
        summary.revenue += item.precio_unitario * item.cantidad
      }
    }

    return Array.from(summaries.entries()).map(([locationId, summary]) => {
      const location = locations.find(loc => loc.id === locationId)
      return {
        location_id: locationId,
        location_nombre: location?.nombre || 'Ubicación desconocida',
        total_ordenes: summary.orderIds.size,
        total_unidades_vendidas: summary.units,
        total_ingresos: summary.revenue,
        ticket_promedio: summary.orderIds.size > 0 ? Number((summary.revenue / summary.orderIds.size).toFixed(2)) : 0
      }
    })
  }

  async getTopProductsByLocation(
    locationId: number,
    params?: { start_date?: string; end_date?: string; limit?: number }
  ): Promise<TopProductByLocationEntry[]> {
    const [ordersWithItems, locations, products] = await Promise.all([
      this.loadOrdersWithItems(),
      this.loadLocations(),
      this.loadProducts()
    ])

    const location = locations.find(loc => loc.id === locationId)
    if (!location) {
      throw new Error(`La ubicación ${locationId} no existe en modo local`)
    }

    const startDate = params?.start_date ? this.parseDate(params.start_date) : undefined
    const endDate = params?.end_date ? this.parseDate(`${params.end_date}T23:59:59`) : undefined
    const limit = params?.limit ? Math.min(Math.max(params.limit, 1), 50) : 10

    const productMap = new Map(products.map(product => [product.id, product]))

    const aggregates = new Map<number, { units: number; revenue: number }>()
    for (const order of ordersWithItems) {
      if (order.estado !== 'completada') continue
      if (order.source_location_id !== locationId) continue

      const createdAt = this.parseDate(order.created_at)
      if (startDate && createdAt < startDate) continue
      if (endDate && createdAt > endDate) continue

      for (const item of order.items) {
        if (!aggregates.has(item.product_id)) {
          aggregates.set(item.product_id, { units: 0, revenue: 0 })
        }
        const aggregate = aggregates.get(item.product_id)!
        aggregate.units += item.cantidad
        aggregate.revenue += item.precio_unitario * item.cantidad
      }
    }

    return Array.from(aggregates.entries())
      .sort((a, b) => b[1].units - a[1].units)
      .slice(0, limit)
      .map(([productId, aggregate]) => {
        const product = productMap.get(productId)
        return {
          product_id: productId,
          product_nombre: product?.nombre || 'Producto desconocido',
          product_categoria: product?.categoria || 'celular',
          cantidad_vendida: aggregate.units,
          ingresos_totales: aggregate.revenue
        }
      })
  }

  async generateBusinessInsights(params: {
    sales_profile_slug?: string
    sales_profile_id?: number
    location_id?: number
    days?: number
    use_cache?: boolean
    force_refresh?: boolean
  } = {}): Promise<BusinessInsightsResponse> {
    const [ordersWithItems, products, locations, salesProfiles] = await Promise.all([
      this.loadOrdersWithItems(),
      this.loadProducts(),
      this.loadLocations(),
      this.getSalesProfiles()
    ])

    let resolvedProfileId = params.sales_profile_id
    if (params.sales_profile_slug) {
      const profile = salesProfiles.find(sp => sp.slug === params.sales_profile_slug)
      if (!profile) {
        throw new Error(`El perfil de ventas ${params.sales_profile_slug} no existe en modo local`)
      }
      resolvedProfileId = profile.id
    }

    if (params.location_id) {
      const exists = locations.some(location => location.id === params.location_id)
      if (!exists) {
        throw new Error(`La ubicación ${params.location_id} no existe en modo local`)
      }
    }

    const days = params.days && params.days > 0 ? params.days : 45
    const periodStart = new Date()
    periodStart.setDate(periodStart.getDate() - days)
    periodStart.setHours(0, 0, 0, 0)

    let relevantOrders = ordersWithItems.filter(order => order.estado === 'completada')
    if (resolvedProfileId) {
      relevantOrders = relevantOrders.filter(order => order.sales_profile_id === resolvedProfileId)
    }
    if (params.location_id) {
      relevantOrders = relevantOrders.filter(order => order.source_location_id === params.location_id)
    }
    relevantOrders = relevantOrders.filter(order => this.parseDate(order.created_at) >= periodStart)

    const productMap = new Map(products.map(product => [product.id, product]))
    let totalRevenue = 0
    let totalCost = 0
    const salesStats = new Map<number, { units: number; revenue: number; cost: number; lastSale?: Date }>()

    for (const order of relevantOrders) {
      const createdAt = this.parseDate(order.created_at)
      totalRevenue += order.total || 0
      for (const item of order.items) {
        const product = productMap.get(item.product_id)
        const unitCost = product?.costo ?? (product ? product.precio * 0.7 : item.precio_unitario * 0.6)
        totalCost += unitCost * item.cantidad

        if (!salesStats.has(item.product_id)) {
          salesStats.set(item.product_id, { units: 0, revenue: 0, cost: 0, lastSale: undefined })
        }
        const stat = salesStats.get(item.product_id)!
        stat.units += item.cantidad
        stat.revenue += item.precio_unitario * item.cantidad
        stat.cost += unitCost * item.cantidad
        if (!stat.lastSale || createdAt > stat.lastSale) {
          stat.lastSale = createdAt
        }
      }
    }

    const ordersCount = relevantOrders.length
    const avgOrderValue = ordersCount > 0 ? Number((totalRevenue / ordersCount).toFixed(2)) : 0
    const grossMargin = totalRevenue > 0 ? Number((((totalRevenue - totalCost) / totalRevenue) * 100).toFixed(2)) : 0

    const topSellers: BusinessInsightTopSeller[] = Array.from(salesStats.entries())
      .sort((a, b) => b[1].revenue - a[1].revenue)
      .slice(0, 5)
      .map(([productId, stat]) => {
        const product = productMap.get(productId)
        return {
          product_id: productId,
          product_name: product?.nombre || 'Producto',
          units_sold: stat.units,
          revenue: Number(stat.revenue.toFixed(2)),
          gross_profit: Number((stat.revenue - stat.cost).toFixed(2))
        }
      })

    const now = new Date()
    const slowMovers: BusinessInsightSlowMover[] = products
      .filter(product => product.activo && (product.stock_disponible || 0) > 0)
      .map(product => {
        const stat = salesStats.get(product.id)
        const lastSale = stat?.lastSale
        const daysWithoutSales = lastSale ? Math.round((now.getTime() - lastSale.getTime()) / MS_PER_DAY) : days
        return {
          product_id: product.id,
          product_name: product.nombre,
          stock_available: product.stock_disponible || 0,
          days_without_sales: daysWithoutSales,
          last_sale_at: lastSale?.toISOString() ?? null,
          unitsSold: stat?.units ?? 0
        }
      })
      .filter(entry => entry.unitsSold <= 1)
      .sort((a, b) => b.days_without_sales - a.days_without_sales)
      .slice(0, 5)
      .map(({ unitsSold: _unitsSold, ...rest }) => rest)

    const rawAlerts = await this.getInventoryAlerts(params.location_id ? { location_id: params.location_id } : undefined)
    const stockAlerts: BusinessInsightStockAlert[] = rawAlerts.map(alert => {
      const stat = salesStats.get(alert.product_id)
      const avgDailyDemand = stat ? Number((stat.units / days).toFixed(2)) : 0
      const daysUntilStockout = avgDailyDemand > 0 ? Number((alert.current_stock / avgDailyDemand).toFixed(1)) : null
      return {
        product_id: alert.product_id,
        product_name: alert.product_name,
        stock_available: alert.current_stock,
        avg_daily_demand: avgDailyDemand,
        days_until_stockout: daysUntilStockout
      }
    })

    const trendWindow = Math.min(Math.max(days, 1), 14)
    const revenueTrends: BusinessInsightTrendPoint[] = []
    for (let offset = trendWindow - 1; offset >= 0; offset--) {
      const dayStart = new Date()
      dayStart.setDate(dayStart.getDate() - offset)
      dayStart.setHours(0, 0, 0, 0)
      const dayEnd = new Date(dayStart)
      dayEnd.setHours(23, 59, 59, 999)
      const dayRevenue = relevantOrders
        .filter(order => {
          const createdAt = this.parseDate(order.created_at)
          return createdAt >= dayStart && createdAt <= dayEnd
        })
        .reduce((sum, order) => sum + (order.total || 0), 0)
      revenueTrends.push({ date: dayStart.toISOString(), revenue: Number(dayRevenue.toFixed(2)) })
    }

    const pricingInsights = analyzePricing(products, relevantOrders)
    const inventoryInsights = analyzeInventory(products, relevantOrders)
    const customerInsights = analyzeCustomers(relevantOrders)
    const recommendations = buildBusinessInsightRecommendations(pricingInsights, inventoryInsights, customerInsights)

    return {
      generated_at: new Date().toISOString(),
      period_days: days,
      filters: {
        location_id: params.location_id ?? null,
        sales_profile_id: resolvedProfileId ?? null,
        sales_profile_slug: params.sales_profile_slug ?? null
      },
      metrics: {
        kpis: {
          total_revenue: Number(totalRevenue.toFixed(2)),
          orders_count: ordersCount,
          avg_order_value: avgOrderValue,
          gross_margin_estimate: grossMargin
        },
        top_sellers: topSellers,
        slow_movers: slowMovers,
        stock_alerts: stockAlerts,
        revenue_trends: revenueTrends
      },
      recommendations,
      ai_summary: `Informe local (${ordersCount} órdenes, L ${totalRevenue.toFixed(2)} en ${days} días).`,
      tokens_used: 0,
      raw_response: null
    }
  }

  async getForecasting(): Promise<SalesForecast[]> {
    try {
      const [products, orders] = await Promise.all([
        this.fetchProducts(undefined, undefined, true),
        this.loadOrdersWithItems()
      ])

      const { forecasts } = await generateAIForecasts(products, orders)
      return forecasts
    } catch (error) {
      console.error('Error generating local forecasts:', error)
      throw new Error('No se pudieron generar los pronósticos en modo local')
    }
  }

  async getLocationStock(locationId: number): Promise<StockByLocation[]> {
    const [stock, locations] = await Promise.all([
      this.getStock(),
      this.loadLocations()
    ])

    const location = locations.find(loc => loc.id === locationId)
    if (!location) {
      throw new Error(`La ubicación ${locationId} no existe en modo local`)
    }

    return stock
      .filter(entry => entry.location_id === locationId)
      .map(entry => {
        const cantidadReservada = entry.cantidad_reservada || 0
        return {
          ...entry,
          cantidad_reservada: cantidadReservada,
          stock_libre: entry.cantidad_disponible - cantidadReservada,
          location
        }
      })
  }

  async getPublicCatalog(filters?: PublicCatalogFilters): Promise<PaginatedResponse<PublicProduct>> {
    const [products, stock] = await Promise.all([
      this.loadProducts(),
      this.getStock()
    ])

    const stockByProduct = stock.reduce<Record<number, number>>((map, entry) => {
      map[entry.product_id] = (map[entry.product_id] || 0) + entry.cantidad_disponible
      return map
    }, {})

    const search = filters?.search?.toLowerCase().trim()
    const category = filters?.category

    const filtered = products.filter(product => {
      if (!product.activo) return false
      if (category && product.categoria !== category) return false
      if (search) {
        const haystack = [
          product.nombre,
          product.marca,
          product.modelo,
          product.sku,
          product.color,
          product.capacidad
        ].filter(Boolean).join(' ').toLowerCase()
        if (!haystack.includes(search)) return false
      }
      return true
    })

    const perPage = filters?.per_page && filters.per_page > 0 ? filters.per_page : 20
    const page = filters?.page && filters.page > 0 ? filters.page : 1
    const start = (page - 1) * perPage
    const paginated = filtered.slice(start, start + perPage)

    const items: PublicProduct[] = paginated.map(product => ({
      id: product.id,
      nombre: product.nombre,
      marca: product.marca,
      modelo: product.modelo,
      categoria: product.categoria,
      condicion: product.condicion,
      precio: product.precio,
      moneda: product.moneda,
      capacidad: product.capacidad,
      color: product.color,
      in_stock: (stockByProduct[product.id] || 0) > 0
    }))

    return {
      items,
      total: filtered.length,
      page,
      per_page: perPage,
      pages: Math.max(1, Math.ceil(filtered.length / perPage))
    }
  }

  async getAIStatus(alertsLimit = 5): Promise<AIStatusResponse> {
    try {
      const now = new Date()
      const last24h = new Date(now.getTime() - MS_PER_DAY)
      const last7d = new Date(now.getTime() - 7 * MS_PER_DAY)

      const [salesProfiles, ordersWithItems, pendingQueue, customers, products, profiles] = await Promise.all([
        this.getSalesProfiles(),
        this.loadOrdersWithItems(),
        this.listTrainingQueue('pending'),
        this.getCustomers(),
        this.fetchProducts(undefined, undefined, true),
        this.loadProfiles()
      ])

      const interactionsLast24h = ordersWithItems.filter(order => this.parseDate(order.created_at) >= last24h).length
      const tokensLast24h = interactionsLast24h * 120
      const avgTokens = interactionsLast24h > 0 ? Math.round(tokensLast24h / interactionsLast24h) : 0

      const pendingByProfile = new Map<number, number>()
      for (const item of pendingQueue) {
        if (!item.sales_profile_id) continue
        pendingByProfile.set(item.sales_profile_id, (pendingByProfile.get(item.sales_profile_id) || 0) + 1)
      }

      const aiProfiles = salesProfiles.map(profile => {
        const profileOrders = ordersWithItems.filter(order => order.sales_profile_id === profile.id)
        const interactionsLast7Days = profileOrders.filter(order => this.parseDate(order.created_at) >= last7d).length
        const lastInteractionDate = profileOrders.reduce<Date | null>((latest, order) => {
          const createdAt = this.parseDate(order.created_at)
          if (!latest || createdAt > latest) {
            return createdAt
          }
          return latest
        }, null)

        return {
          sales_profile_id: profile.id,
          sales_profile_name: profile.name,
          slug: profile.slug,
          is_ai_active: profile.tipo === 'bot_ia' && profile.active,
          last_interaction_at: lastInteractionDate ? lastInteractionDate.toISOString() : undefined,
          interactions_last_7_days: interactionsLast7Days,
          tokens_last_7_days: interactionsLast7Days * 120,
          pending_training_items: pendingByProfile.get(profile.id) || 0
        }
      })

      let forecastingAlerts: ForecastingAlertItem[] = []
      try {
        if (products.length > 0) {
          const { forecasts } = await generateAIForecasts(products, ordersWithItems)
          const baseProfile = profiles[0] ?? { id: 0, name: 'Operación Local', slug: 'local', active: true }
          const restockAlerts = await generateRestockAlerts(forecasts, baseProfile)
          forecastingAlerts = restockAlerts.slice(0, alertsLimit).map(alert => {
            const relatedForecast = forecasts.find(f => f.productId === alert.productId)
            return {
              product_id: alert.productId,
              product_name: alert.productName,
              days_until_stockout: relatedForecast?.daysUntilStockout ?? alert.daysUntilStockout,
              restock_recommendation: relatedForecast?.restockRecommendation ?? alert.recommendedOrderQuantity,
              trend: relatedForecast?.trend ?? 'stable'
            }
          })
        }
      } catch (forecastError) {
        console.warn('AI status: forecasting alerts unavailable in local mode', forecastError)
      }

      return {
        snapshot_generated_at: now.toISOString(),
        total_sales_profiles: salesProfiles.length,
        ai_profiles_active: salesProfiles.filter(p => p.tipo === 'bot_ia' && p.active).length,
        ai_profiles_inactive: salesProfiles.filter(p => p.tipo === 'bot_ia' && !p.active).length,
        interactions_last_24h: interactionsLast24h,
        tokens_last_24h: tokensLast24h,
        avg_tokens_per_response: avgTokens,
        customers_flagged: customers.filter(c => c.is_troll || c.is_blocked).length,
        training_backlog: pendingQueue.length,
        ai_profiles: aiProfiles,
        forecasting_alerts: forecastingAlerts
      }
    } catch (error) {
      console.error('Error building AI status (local):', error)
      throw new Error('No se pudo generar el estado de IA en modo local')
    }
  }

  // --- AI & Customer Methods (V2.1) ---

  async listTrainingQueue(status: string = 'pending'): Promise<TrainingQueueItem[]> {
    try {
      const kv = getKV()
      const items = await kv.get<TrainingQueueItem[]>(STORAGE_KEYS.TRAINING_QUEUE) || []
      return items.filter(i => i.status === status).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } catch (error) {
      console.error('Error listing training queue:', error)
      return []
    }
  }

  async updateTrainingQueueItem(id: number, updates: Partial<TrainingQueueItem>): Promise<TrainingQueueItem> {
    try {
      const kv = getKV()
      const items = await kv.get<TrainingQueueItem[]>(STORAGE_KEYS.TRAINING_QUEUE) || []
      const index = items.findIndex(i => i.id === id)
      if (index === -1) throw new Error(`Training queue item ${id} not found`)
      
      const previousItem = { ...items[index] }
      const updatedItem = { ...previousItem, ...updates, updated_at: new Date().toISOString() }
      items[index] = updatedItem
      await kv.set(STORAGE_KEYS.TRAINING_QUEUE, items)
      await this.recordSyncEvent({
        entity: 'ai_profile',
        action: 'update',
        entityId: id,
        payload: {
          before: previousItem,
          after: updatedItem,
          updates
        }
      })
      return updatedItem
    } catch (error) {
      console.error('Error updating training queue item:', error)
      throw error
    }
  }

  async getCustomers(search?: string): Promise<Customer[]> {
    try {
      const kv = getKV()
      const customers = await kv.get<Customer[]>(STORAGE_KEYS.CUSTOMERS) || []

      if (!search?.trim()) {
        return customers
      }

      const term = search.trim().toLowerCase()
      return customers.filter(customer => {
        const phoneMatch = customer.phone_number?.toLowerCase().includes(term)
        const nameMatch = customer.name?.toLowerCase().includes(term)
        return phoneMatch || nameMatch
      })
    } catch (error) {
      console.error('Error getting customers:', error)
      return []
    }
  }

  async updateCustomer(id: number, updates: Partial<Customer>): Promise<Customer> {
    try {
      const kv = getKV()
      const customers = await kv.get<Customer[]>(STORAGE_KEYS.CUSTOMERS) || []
      const index = customers.findIndex(c => c.id === id)
      if (index === -1) throw new Error(`Customer ${id} not found`)
      
      const previousCustomer = { ...customers[index] }
      const updatedCustomer = { ...previousCustomer, ...updates }
      customers[index] = updatedCustomer
      await kv.set(STORAGE_KEYS.CUSTOMERS, customers)
      await this.recordSyncEvent({
        entity: 'customer',
        action: 'update',
        entityId: id,
        payload: {
          before: previousCustomer,
          after: updatedCustomer,
          updates
        }
      })
      return updatedCustomer
    } catch (error) {
      console.error('Error updating customer:', error)
      throw error
    }
  }

  async listCustomerStats(params?: { sales_profile_slug?: string; page?: number; per_page?: number }): Promise<CustomerStats[]> {
    const [orders, aiCustomers, salesProfiles] = await Promise.all([
      this.loadOrders(),
      this.getCustomers(),
      this.getSalesProfiles()
    ])

    let filteredOrders = [...orders]
    if (params?.sales_profile_slug) {
      const profile = salesProfiles.find(sp => sp.slug === params.sales_profile_slug && sp.active)
      if (!profile) {
        throw new Error(`El perfil de ventas ${params.sales_profile_slug} no existe en modo local`)
      }
      filteredOrders = filteredOrders.filter(order => order.sales_profile_id === profile.id)
    }

    const statsMap = this.aggregateCustomerStats(filteredOrders)
    const aiDataMap = new Map(aiCustomers.map(customer => [customer.phone_number, customer]))

    const sorted = Array.from(statsMap.values()).sort((a, b) => b.totalSpent - a.totalSpent)
    const perPage = params?.per_page && params.per_page > 0 ? params.per_page : 50
    const page = params?.page && params.page > 0 ? params.page : 1
    const start = (page - 1) * perPage
    const paginated = sorted.slice(start, start + perPage)

    return paginated.map(entry => {
      const aiData = aiDataMap.get(entry.phone)
      const averageOrder = entry.completedOrders > 0 ? Number((entry.totalSpent / entry.completedOrders).toFixed(2)) : 0
      return {
        customer_phone: entry.phone,
        customer_name: entry.name || 'Cliente sin nombre',
        total_orders: entry.totalOrders,
        total_spent: Number(entry.totalSpent.toFixed(2)),
        average_order: averageOrder,
        first_order_date: entry.firstOrder || new Date().toISOString(),
        last_order_date: entry.lastOrder || new Date().toISOString(),
        id: aiData?.id,
        is_troll: aiData?.is_troll ?? false,
        is_blocked: aiData?.is_blocked ?? false,
        reputation_score: aiData?.reputation_score ?? 100,
        daily_message_count: aiData?.daily_message_count ?? 0
      }
    })
  }

  async getCustomerStatsByPhone(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerStats> {
    const [orders, aiCustomers, salesProfiles] = await Promise.all([
      this.loadOrders(),
      this.getCustomers(),
      this.getSalesProfiles()
    ])

    let filteredOrders = orders.filter(order => order.customer_phone === customerPhone)
    if (params?.sales_profile_slug) {
      const profile = salesProfiles.find(sp => sp.slug === params.sales_profile_slug && sp.active)
      if (!profile) {
        throw new Error(`El perfil de ventas ${params.sales_profile_slug} no existe en modo local`)
      }
      filteredOrders = filteredOrders.filter(order => order.sales_profile_id === profile.id)
    }

    if (filteredOrders.length === 0) {
      throw new Error(`No se encontraron órdenes para el cliente ${customerPhone}`)
    }

    const stats = this.aggregateCustomerStats(filteredOrders).get(customerPhone)!
    const aiData = aiCustomers.find(c => c.phone_number === customerPhone)
    const averageOrder = stats.completedOrders > 0 ? Number((stats.totalSpent / stats.completedOrders).toFixed(2)) : 0

    return {
      customer_phone: customerPhone,
      customer_name: stats.name || 'Cliente sin nombre',
      total_orders: stats.totalOrders,
      total_spent: Number(stats.totalSpent.toFixed(2)),
      average_order: averageOrder,
      first_order_date: stats.firstOrder || new Date().toISOString(),
      last_order_date: stats.lastOrder || new Date().toISOString(),
      id: aiData?.id,
      is_troll: aiData?.is_troll ?? false,
      is_blocked: aiData?.is_blocked ?? false,
      reputation_score: aiData?.reputation_score ?? 100,
      daily_message_count: aiData?.daily_message_count ?? 0
    }
  }

  async getCustomerHistory(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerHistory> {
    const [orders, aiCustomers, salesProfiles] = await Promise.all([
      this.loadOrders(),
      this.getCustomers(),
      this.getSalesProfiles()
    ])

    let filteredOrders = orders.filter(order => order.customer_phone === customerPhone)
    if (params?.sales_profile_slug) {
      const profile = salesProfiles.find(sp => sp.slug === params.sales_profile_slug && sp.active)
      if (!profile) {
        throw new Error(`El perfil de ventas ${params.sales_profile_slug} no existe en modo local`)
      }
      filteredOrders = filteredOrders.filter(order => order.sales_profile_id === profile.id)
    }

    if (filteredOrders.length === 0) {
      throw new Error(`No se encontraron órdenes para el cliente ${customerPhone}`)
    }

    const stats = this.aggregateCustomerStats(filteredOrders).get(customerPhone)!
    const aiData = aiCustomers.find(c => c.phone_number === customerPhone)
    const averageOrder = stats.completedOrders > 0 ? Number((stats.totalSpent / stats.completedOrders).toFixed(2)) : 0

    const ordersSummary = filteredOrders
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .map(order => this.toOrderSummary(order))

    return {
      customer_phone: customerPhone,
      customer_name: stats.name || 'Cliente sin nombre',
      total_orders: stats.totalOrders,
      total_spent: Number(stats.totalSpent.toFixed(2)),
      average_order: averageOrder,
      first_order_date: stats.firstOrder || new Date().toISOString(),
      last_order_date: stats.lastOrder || new Date().toISOString(),
      id: aiData?.id,
      is_troll: aiData?.is_troll ?? false,
      is_blocked: aiData?.is_blocked ?? false,
      reputation_score: aiData?.reputation_score ?? 100,
      daily_message_count: aiData?.daily_message_count ?? 0,
      orders: ordersSummary
    }
  }

  async getAIContext(payload: AIContextPayload): Promise<AIContextResponse> {
    const [salesProfiles, products, customers] = await Promise.all([
      this.getSalesProfiles(),
      this.loadProducts(),
      this.getCustomers()
    ])

    const profile = salesProfiles.find(sp => sp.slug === payload.sales_profile_slug)
    if (!profile) {
      throw new Error(`Perfil de ventas ${payload.sales_profile_slug} no disponible en modo local`)
    }

    const customer = customers.find(c => c.phone_number === payload.customer_phone)
    const inventoryPreview = products
      .filter(product => product.activo)
      .slice(0, 8)
      .map(product => `• ${product.nombre} (${product.marca}) - ${product.precio} ${product.moneda}`)
      .join('\n') || 'Inventario local no inicializado'

    return {
      system_prompt: `Modo local: responde como ${profile.name} (${profile.tipo}).`,
      bot_config: {
        model_name: 'local-mock',
        temperature: 0.7,
        voice_tone: profile.tipo === 'bot_ia' ? 'amigable y ágil' : 'profesional'
      },
      customer_info: {
        name: customer?.name || payload.customer_name || 'Cliente',
        reputation_score: customer?.reputation_score ?? 100,
        notes: customer?.notes
      },
      relevant_inventory: inventoryPreview,
      relevant_faqs: 'FAQ offline: Consulta documentación local.',
      financing_info: 'Financiamiento disponible solo en modo API.',
      previous_context: []
    }
  }

  async generateAIReply(payload: AIReplyPayload): Promise<AIReplyResponse> {
    const context = await this.getAIContext(payload)
    const reply = `⚠️ Modo offline: No se pudo contactar a la IA. Mensaje del cliente: "${payload.message_content}"`
    return {
      reply,
      tokens_used: payload.message_content.length,
      model: 'local-mock',
      context
    }
  }

  async logAIInteraction(payload: AIInteractionLogPayload): Promise<{ status: string }> {
    console.info('Registro IA (local):', payload)
    return { status: 'stored_locally' }
  }

  async submitAITrainingExample(payload: TrainingSubmissionPayload): Promise<{ status: string }> {
    const kv = getKV()
    const queue = await kv.get<TrainingQueueItem[]>(STORAGE_KEYS.TRAINING_QUEUE) || []
    const salesProfiles = await this.getSalesProfiles()
    const profile = salesProfiles.find(sp => sp.slug === payload.sales_profile_slug)
    const nextId = queue.length > 0 ? Math.max(...queue.map(item => item.id)) + 1 : 1

    const newItem: TrainingQueueItem = {
      id: nextId,
      sales_profile_id: profile?.id,
      customer_question: payload.customer_question,
      ai_proposed_answer: payload.ai_proposed_answer,
      admin_correction: undefined,
      status: 'pending',
      created_at: new Date().toISOString(),
      sales_profile: profile
    }

    queue.push(newItem)
    await kv.set(STORAGE_KEYS.TRAINING_QUEUE, queue)
    await this.recordSyncEvent({
      entity: 'ai_profile',
      action: 'create',
      entityId: newItem.id,
      payload: {
        training_item: newItem,
        source: 'training_queue_submission'
      }
    })
    return { status: 'queued_local' }
  }

  async flagCustomerAsTroll(phoneNumber: string, reason: string): Promise<FlagTrollResponse> {
    const kv = getKV()
    const customers = await kv.get<Customer[]>(STORAGE_KEYS.CUSTOMERS) || []
    let customer = customers.find(c => c.phone_number === phoneNumber)
    let action: import('./types').SyncActionType = 'update'
    if (!customer) {
      const nextId = customers.length > 0 ? Math.max(...customers.map(c => c.id)) + 1 : 1
      customer = {
        id: nextId,
        phone_number: phoneNumber,
        is_troll: true,
        is_blocked: true,
        reputation_score: 0,
        daily_message_count: 0,
        notes: reason,
        created_at: new Date().toISOString()
      }
      customers.push(customer)
      action = 'create'
    } else {
      customer.is_troll = true
      customer.is_blocked = true
      customer.notes = reason
    }

    await kv.set(STORAGE_KEYS.CUSTOMERS, customers)
    if (customer) {
      await this.recordSyncEvent({
        entity: 'customer',
        action,
        entityId: customer.id,
        payload: {
          customer,
          reason
        }
      })
    }
    return {
      status: 'flagged',
      customer: phoneNumber
    }
  }

  // --- RBAC Methods (Local Mode) ---

  async listPermissions(): Promise<Permission[]> {
    await this.ensureRbacSeeded()
    return this.loadPermissions()
  }

  async listRoles(): Promise<Role[]> {
    await this.ensureRbacSeeded()
    return this.loadRoles()
  }

  async listUsers(): Promise<User[]> {
    await this.ensureRbacSeeded()
    const [users, roles] = await Promise.all([this.loadUsers(), this.loadRoles()])
    const rolesById = new Map(roles.map(role => [role.id, role] as const))
    return users.map(user => ({
      ...user,
      role: user.role_id ? rolesById.get(user.role_id) || user.role : user.role
    }))
  }

  async createUser(payload: CreateUserRequest): Promise<User> {
    await this.ensureRbacSeeded()
    const release = await inventoryLock.acquire()
    try {
      const [users, roles] = await Promise.all([this.loadUsers(), this.loadRoles()])
      if (users.some(user => user.username.toLowerCase() === payload.username.toLowerCase())) {
        throw new Error(`Ya existe un usuario con el nombre ${payload.username}`)
      }
      const role = roles.find(entry => entry.id === payload.role_id)
      if (!role) {
        throw new Error('Rol no disponible en modo local')
      }
      const nextId = users.length > 0 ? Math.max(...users.map(user => user.id)) + 1 : 1
      const timestamp = new Date().toISOString()
      const newUser: User = {
        id: nextId,
        username: payload.username,
        email: payload.email,
        full_name: payload.full_name,
        is_active: true,
        is_superuser: role.name.toLowerCase().includes('super') || (role.permissions?.length || 0) === PERMISSION_SEED_DATA.length,
        role_id: role.id,
        role,
        created_at: timestamp,
        updated_at: timestamp
      }
      await this.setUsers([...users, newUser])
      await this.recordSyncEvent({
        entity: 'rbac',
        action: 'create',
        entityId: newUser.id,
        payload: {
          user: newUser
        }
      })
      return newUser
    } finally {
      release()
    }
  }

  async deleteUser(userId: number): Promise<void> {
    await this.ensureRbacSeeded()
    const release = await inventoryLock.acquire()
    try {
      const users = await this.loadUsers()
      if (users.length <= 1) {
        throw new Error('Debe existir al menos un usuario activo en modo local')
      }
      const user = users.find(entry => entry.id === userId)
      if (!user) {
        throw new Error('Usuario no encontrado')
      }
      if (user.is_superuser) {
        throw new Error('No puedes eliminar la cuenta principal en modo local')
      }
      const userToDelete = { ...user }
      await this.setUsers(users.filter(entry => entry.id !== userId))
      await this.recordSyncEvent({
        entity: 'rbac',
        action: 'delete',
        entityId: userId,
        payload: {
          user: userToDelete
        }
      })
    } finally {
      release()
    }
  }

  async updateUserRole(userId: number, roleId: number): Promise<User> {
    await this.ensureRbacSeeded()
    const release = await inventoryLock.acquire()
    try {
      const [users, roles] = await Promise.all([this.loadUsers(), this.loadRoles()])
      const index = users.findIndex(entry => entry.id === userId)
      if (index === -1) {
        throw new Error('Usuario no encontrado')
      }
      const role = roles.find(entry => entry.id === roleId)
      if (!role) {
        throw new Error('Rol no disponible en modo local')
      }
      const now = new Date().toISOString()
      const previousUser = { ...users[index] }
      const updated: User = {
        ...users[index],
        role_id: role.id,
        role,
        is_superuser: role.name.toLowerCase().includes('super'),
        updated_at: now
      }
      users[index] = updated
      await this.setUsers(users)
      await this.recordSyncEvent({
        entity: 'rbac',
        action: 'update',
        entityId: userId,
        payload: {
          before: previousUser,
          after: updated,
          role_change: {
            from: previousUser.role_id,
            to: role.id
          }
        }
      })
      return updated
    } finally {
      release()
    }
  }

  async updateUser(userId: number, updates: Partial<User> & { password?: string; role_id?: number }): Promise<User> {
    await this.ensureRbacSeeded()
    const release = await inventoryLock.acquire()
    try {
      const users = await this.loadUsers()
      const index = users.findIndex(entry => entry.id === userId)
      if (index === -1) {
        throw new Error('Usuario no encontrado')
      }

      let roles: Role[] | undefined
      if (typeof updates.role_id === 'number') {
        roles = await this.loadRoles()
      }

      const nextRole = typeof updates.role_id === 'number'
        ? roles?.find(role => role.id === updates.role_id)
        : users[index].role

      if (typeof updates.role_id === 'number' && !nextRole) {
        throw new Error('Rol no disponible en modo local')
      }

      const { password: _password, ...restUpdates } = updates
      const now = new Date().toISOString()
      const previousUser = { ...users[index] }
      const updated: User = {
        ...users[index],
        ...restUpdates,
        role_id: typeof updates.role_id === 'number' ? updates.role_id : users[index].role_id,
        role: nextRole,
        is_superuser: nextRole ? nextRole.name.toLowerCase().includes('super') : users[index].is_superuser,
        updated_at: now
      }

      if (updates.password) {
        console.info('Actualización de contraseña realizada en modo local; sin efecto en autenticación real')
      }

      users[index] = updated
      await this.setUsers(users)
      await this.recordSyncEvent({
        entity: 'rbac',
        action: 'update',
        entityId: userId,
        payload: {
          before: previousUser,
          after: updated,
          updates: restUpdates
        }
      })
      return updated
    } finally {
      release()
    }
  }

  async getAIProfileConfig(salesProfileId: number): Promise<AIProfileConfig | null> {
    try {
      const kv = getKV()
      const configs = await kv.get<AIProfileConfig[]>(STORAGE_KEYS.AI_CONFIG) || []
      return configs.find(c => c.sales_profile_id === salesProfileId) || null
    } catch (error) {
      console.error('Error getting AI config:', error)
      return null
    }
  }

  async updateAIProfileConfig(id: number, updates: Partial<AIProfileConfig>): Promise<AIProfileConfig> {
    try {
      const kv = getKV()
      const configs = await kv.get<AIProfileConfig[]>(STORAGE_KEYS.AI_CONFIG) || []
      const index = configs.findIndex(c => c.id === id)
      
      if (index === -1) {
        // Create if not exists
        const newConfig: AIProfileConfig = {
            id: Math.max(0, ...configs.map(c => c.id || 0)) + 1,
            sales_profile_id: updates.sales_profile_id!,
            model_name: updates.model_name || 'gpt-4o',
            temperature: updates.temperature || 0.7,
            system_prompt: updates.system_prompt || '',
            is_active: updates.is_active ?? true,
            ...updates
        } as AIProfileConfig
        configs.push(newConfig)
        await kv.set(STORAGE_KEYS.AI_CONFIG, configs)
        await this.recordSyncEvent({
          entity: 'ai_profile',
          action: 'create',
          entityId: newConfig.id,
          payload: {
            config: newConfig
          }
        })
        return newConfig
      }
      
      const previousConfig = { ...configs[index] }
      const updatedConfig = { ...configs[index], ...updates }
      configs[index] = updatedConfig
      await kv.set(STORAGE_KEYS.AI_CONFIG, configs)
      await this.recordSyncEvent({
        entity: 'ai_profile',
        action: 'update',
        entityId: updatedConfig.id,
        payload: {
          before: previousConfig,
          after: updatedConfig,
          updates
        }
      })
      return updatedConfig
    } catch (error) {
      console.error('Error updating AI config:', error)
      throw error
    }
  }

  // ============================================================================
  // V2.1: FINANCING (Financiamiento)
  // ============================================================================

  async getBanks(activeOnly: boolean = true): Promise<Bank[]> {
    try {
      const kv = getKV()
      const banks = await kv.get<Bank[]>(STORAGE_KEYS.BANKS) || []
      if (activeOnly) {
        return banks.filter(b => b.active)
      }
      return banks
    } catch (error) {
      console.error('Error getting banks:', error)
      return []
    }
  }

  async createBank(bank: Partial<Bank>): Promise<Bank> {
    try {
      const kv = getKV()
      const banks = await kv.get<Bank[]>(STORAGE_KEYS.BANKS) || []
      const nextId = banks.length > 0 ? Math.max(...banks.map(b => b.id)) + 1 : 1
      
      const newBank: Bank = {
        id: nextId,
        name: bank.name || 'Nuevo Banco',
        active: bank.active ?? true,
        normal_card_rate: bank.normal_card_rate || 0.04,
        financing_options: []
      }

      await kv.set(STORAGE_KEYS.BANKS, [...banks, newBank])
      await this.recordSyncEvent({
        entity: 'financing',
        action: 'create',
        entityId: newBank.id,
        payload: {
          bank: newBank
        }
      })
      return newBank
    } catch (error) {
      console.error('Error creating bank:', error)
      throw error
    }
  }

  async updateBank(id: number, updates: Partial<Bank>): Promise<Bank> {
    try {
      const kv = getKV()
      const banks = await kv.get<Bank[]>(STORAGE_KEYS.BANKS) || []
      const index = banks.findIndex(b => b.id === id)
      
      if (index === -1) {
        throw new Error(`Bank with ID ${id} not found`)
      }

      const previousBank = { ...banks[index] }
      const updatedBank = { ...banks[index], ...updates }
      banks[index] = updatedBank
      await kv.set(STORAGE_KEYS.BANKS, banks)
      await this.recordSyncEvent({
        entity: 'financing',
        action: 'update',
        entityId: id,
        payload: {
          before: previousBank,
          after: updatedBank,
          updates
        }
      })
      return updatedBank
    } catch (error) {
      console.error('Error updating bank:', error)
      throw error
    }
  }

  async createFinancingOption(bankId: number, option: Partial<FinancingOption>): Promise<FinancingOption> {
    try {
      const kv = getKV()
      const banks = await kv.get<Bank[]>(STORAGE_KEYS.BANKS) || []
      const bankIndex = banks.findIndex(b => b.id === bankId)
      
      if (bankIndex === -1) {
        throw new Error(`Bank with ID ${bankId} not found`)
      }

      // Calculate next global ID
      let maxId = 0
      for (const b of banks) {
        for (const o of b.financing_options) {
          if (o.id > maxId) maxId = o.id
        }
      }
      const nextId = maxId + 1

      const newOption: FinancingOption = {
        id: nextId,
        bank_id: bankId,
        months: option.months || 0,
        rate: option.rate || 0,
        active: option.active ?? true
      }

      banks[bankIndex].financing_options.push(newOption)
      await kv.set(STORAGE_KEYS.BANKS, banks)
      await this.recordSyncEvent({
        entity: 'financing',
        action: 'create',
        entityId: newOption.id,
        payload: {
          bank_id: bankId,
          option: newOption
        }
      })
      return newOption
    } catch (error) {
      console.error('Error creating financing option:', error)
      throw error
    }
  }

  async deleteFinancingOption(optionId: number): Promise<void> {
    try {
      const kv = getKV()
      const banks = await kv.get<Bank[]>(STORAGE_KEYS.BANKS) || []
      
      let found = false
      let removedOption: FinancingOption | null = null
      let removedFromBank: number | null = null
      for (let i = 0; i < banks.length; i++) {
        const bank = banks[i]
        const optionIndex = bank.financing_options.findIndex(o => o.id === optionId)
        if (optionIndex !== -1) {
          const [option] = bank.financing_options.splice(optionIndex, 1)
          removedOption = option
          removedFromBank = bank.id
          found = true
          break 
        }
      }

      if (!found) {
         console.warn(`Financing option ${optionId} not found to delete`)
      }

      await kv.set(STORAGE_KEYS.BANKS, banks)

      if (removedOption && removedFromBank !== null) {
        await this.recordSyncEvent({
          entity: 'financing',
          action: 'delete',
          entityId: removedOption.id,
          payload: {
            bank_id: removedFromBank,
            option: removedOption
          }
        })
      }
    } catch (error) {
      console.error('Error deleting financing option:', error)
      throw error
    }
  }

  // ============================================================================
  // V2.1: TRADE-IN POLICIES
  // ============================================================================

  async getTradeInPolicies(): Promise<TradeInPolicy[]> {
    try {
      const kv = getKV()
      return await kv.get<TradeInPolicy[]>(STORAGE_KEYS.TRADE_IN_POLICIES) || []
    } catch (error) {
      console.error('Error getting trade-in policies:', error)
      return []
    }
  }

  async createTradeInPolicy(policy: Omit<TradeInPolicy, 'id' | 'created_at'>): Promise<TradeInPolicy> {
    try {
      const kv = getKV()
      const policies = await kv.get<TradeInPolicy[]>(STORAGE_KEYS.TRADE_IN_POLICIES) || []
      const nextId = policies.length > 0 ? Math.max(...policies.map(p => p.id)) + 1 : 1
      
      const newPolicy: TradeInPolicy = {
        ...policy,
        id: nextId,
        created_at: new Date().toISOString()
      }

      await kv.set(STORAGE_KEYS.TRADE_IN_POLICIES, [...policies, newPolicy])
      await this.recordSyncEvent({
        entity: 'trade_in',
        action: 'create',
        entityId: newPolicy.id,
        payload: {
          policy: newPolicy
        }
      })
      return newPolicy
    } catch (error) {
      console.error('Error creating trade-in policy:', error)
      throw error
    }
  }

  async deleteTradeInPolicy(id: number): Promise<void> {
    try {
      const kv = getKV()
      const policies = await kv.get<TradeInPolicy[]>(STORAGE_KEYS.TRADE_IN_POLICIES) || []
      const policyToDelete = policies.find(p => p.id === id)
      const filtered = policies.filter(p => p.id !== id)
      await kv.set(STORAGE_KEYS.TRADE_IN_POLICIES, filtered)

      if (policyToDelete) {
        await this.recordSyncEvent({
          entity: 'trade_in',
          action: 'delete',
          entityId: id,
          payload: {
            policy: policyToDelete
          }
        })
      }
    } catch (error) {
      console.error('Error deleting trade-in policy:', error)
      throw error
    }
  }

  async resolveTrainingQueueItem(
    id: number,
    action: 'approve' | 'reject' | 'convert_to_faq',
    correction?: string
  ): Promise<void> {
    try {
      const kv = getKV()
      const items = await kv.get<TrainingQueueItem[]>(STORAGE_KEYS.TRAINING_QUEUE) || []
      const index = items.findIndex(i => i.id === id)
      if (index === -1) {
        throw new Error(`Training queue item ${id} not found`)
      }

      if (action === 'convert_to_faq' && !correction?.trim()) {
        throw new Error('Correction text is required to convert to FAQ')
      }

      const statusMap: Record<'approve' | 'reject' | 'convert_to_faq', TrainingQueueItem['status']> = {
        approve: 'approved',
        reject: 'rejected',
        convert_to_faq: 'converted_to_faq'
      }

      const previousItem = { ...items[index] }
      const now = new Date().toISOString()
      const updatedItem: TrainingQueueItem = {
        ...items[index],
        status: statusMap[action],
        admin_correction: correction?.trim() || items[index].admin_correction,
        updated_at: now
      }

      items[index] = updatedItem
      await kv.set(STORAGE_KEYS.TRAINING_QUEUE, items)
      await this.recordSyncEvent({
        entity: 'ai_profile',
        action: 'resolve',
        entityId: updatedItem.id,
        payload: {
          before: previousItem,
          after: updatedItem,
          resolution: action
        }
      })

      if (action === 'convert_to_faq') {
        const faqs = await this.loadFaqs()
        const nextFaqId = faqs.length > 0 ? Math.max(...faqs.map(f => f.id)) + 1 : 1

        const newFaq: import('./types').FAQEntry = {
          id: nextFaqId,
          pregunta_clave: updatedItem.customer_question,
          respuesta: correction!.trim(),
          categoria: 'IA Auto',
          activa: true,
          veces_usada: 0,
          created_at: now,
          updated_at: now
        }

        await this.setFaqs([newFaq, ...faqs])
        await this.recordSyncEvent({
          entity: 'faq',
          action: 'create',
          entityId: newFaq.id,
          payload: {
            faq: newFaq,
            source: 'training_queue',
            training_item_id: updatedItem.id
          }
        })
      }
    } catch (error) {
      console.error('Error resolving training queue item:', error)
      throw error
    }
  }
}

export const inventoryService = new InventoryService()
