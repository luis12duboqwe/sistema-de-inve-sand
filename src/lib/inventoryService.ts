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
  IMEIHistory
} from './types'
import { getKV } from './kvStorage'

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
  IMEI_HISTORY: 'inventory-imei-history'      // V2.0
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
              const hasGifts = request.items.some(i => {
                  // En request.items no viene es_regalo_promocion explícito a veces, 
                  // pero si viniera, lo checamos. 
                  // En la UI actual no se manda es_regalo_promocion en el request principal, 
                  // pero asumiremos que si el precio es 0 es regalo.
                  // O mejor, si implementamos la UI de regalos después.
                  // Por ahora, usaremos 5% como base estricta.
                  return false 
              })
              
              // TODO: Detectar regalos en frontend request si se implementa UI de regalos
              const MAX_DISCOUNT_PERCENT = 0.05 
              const minPriceAllowed = precioBaseLocal * (1 - MAX_DISCOUNT_PERCENT)
              
              if (precioFinal < minPriceAllowed) {
                 throw new Error(`El bot no está autorizado a dar descuentos mayores al ${MAX_DISCOUNT_PERCENT*100}%. Precio mínimo: ${minPriceAllowed}`)
              }

              // REGLA 2: Números cerrados
              if (precioFinal % 100 !== 0) {
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
        
        total += precioFinal * item.cantidad

        const stockEntry = updatedStock.find(
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
        // Check if product is serialized (explicit flag OR has IMEIs registered)
        const isSerialized = product.is_serialized || updatedIMEIs.some(pi => pi.product_id === item.product_id)
        
        if (isSerialized) {
          let imeisToSell: ProductIMEI[] = []

          if (item.imeis && item.imeis.length > 0) {
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
          es_regalo_promocion: false
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
        for (const tradeIn of request.trade_ins) {
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
            p.activo
          )

          let newProduct: Product
          let isNewProduct = false

          if (existingProduct) {
             newProduct = existingProduct
             // No actualizamos precio ni costo del producto existente
          } else {
             // Crear Producto Nuevo si no existe
             isNewProduct = true
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
                categoria: tradeIn.imei ? 'celular' : 'accesorio',
                marca: tradeIn.marca,
                modelo: tradeIn.modelo,
                condicion: tradeIn.condicion as any,
                precio: tradeIn.precio_venta ? Number(tradeIn.precio_venta) : Number(tradeIn.valor_estimado) * 1.3,
                costo: Number(tradeIn.valor_estimado),
                moneda: 'HNL',
                activo: true,
                garantia_meses: 0,
                is_serialized: !!tradeIn.imei,
                capacidad: ''
             }
             tradeInProducts.push(newProduct)
          }

          // 2. Crear o Actualizar Stock
          // Check if we already have a stock entry for this product in the current transaction (tradeInStock)
          let stockEntry = tradeInStock.find(s => s.product_id === newProduct.id && s.location_id === request.source_location_id)
          
          // If not in current transaction, check existing stock
          if (!stockEntry) {
             const existingStock = stock.find(s => s.product_id === newProduct.id && s.location_id === request.source_location_id)
             if (existingStock) {
                // Clone it to avoid mutating original array directly before commit
                stockEntry = { ...existingStock }
                // Remove from original stock array in memory to avoid duplicates when merging later? 
                // Actually, we should just update the existing one in `stock` array, but here we are building `tradeInStock` list.
                // Let's just use `tradeInStock` for NEW entries, and update `stock` directly for existing ones.
                
                // Better approach: Update `updatedStock` directly
                const updatedStockEntry = updatedStock.find(s => s.product_id === newProduct.id && s.location_id === request.source_location_id)
                if (updatedStockEntry) {
                   updatedStockEntry.cantidad_disponible += 1
                } else {
                   // Should not happen if we found it in `stock`
                }
             } else {
                // Create new stock entry
                const nextStockId = Math.max(0, ...stock.map(s => s.id), ...tradeInStock.map(s => s.id)) + 1
                stockEntry = {
                    id: nextStockId,
                    product_id: newProduct.id,
                    location_id: request.source_location_id,
                    cantidad_disponible: 1,
                    cantidad_reservada: 0
                }
                tradeInStock.push(stockEntry)
             }
          } else {
             // Already added to tradeInStock in this loop (multiple trade-ins of same new product)
             stockEntry.cantidad_disponible += 1
          }
          
          // Calculate previous stock for history
          const stockAnterior = isNewProduct ? 0 : (
             stock.find(s => s.product_id === newProduct.id && s.location_id === request.source_location_id)?.cantidad_disponible || 0
          )

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

      await this.setProducts([...products, ...tradeInProducts])
      await this.setStock([...updatedStock, ...tradeInStock])
      await this.setOrders([...orders, newOrder])
      await this.setOrderItems([...orderItems, ...newOrderItems])
      await this.setStockHistory([...stockHistory, ...newStockHistory, ...tradeInStockHistory])
      await this.setProductIMEIs([...updatedIMEIs, ...tradeInIMEIs])
      await this.setTradeIns([...tradeIns, ...newTradeIns])
      await this.setIMEIHistory([...imeiHistory, ...newIMEIHistory])

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
        imeis?: string[]
      }>
    }
  ): Promise<OrderWithItems> {
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
      const currentItems = orderItems.filter(oi => oi.order_id === orderId)
      const locationId = currentOrder.source_location_id
      if (!locationId) {
        throw new Error('Order does not have a source_location_id; cannot update stock by location')
      }

      if (updates.items) {
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
        }

        // 2. Liberar IMEIs asociados a esta orden (marcarlos como no vendidos)
        // Esto permite que sean re-seleccionados si se mantienen en la orden, o liberados si se quitan
        for (let i = 0; i < imeis.length; i++) {
          if (imeis[i].order_id === orderId) {
            imeis[i] = { ...imeis[i], vendido: false, order_id: undefined }
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
          total += product.precio * item.cantidad

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

          // Marcar IMEIs como vendidos
          if (item.imeis && item.imeis.length > 0) {
            for (const imeiStr of item.imeis) {
              const imeiIndex = imeis.findIndex(i => i.imei === imeiStr && i.product_id === item.product_id)
              if (imeiIndex !== -1) {
                imeis[imeiIndex] = { ...imeis[imeiIndex], vendido: true, order_id: orderId }
              }
            }
          }

          const newOrderItem: OrderItem = {
            id: item.id || nextItemId++,
            order_id: orderId,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: product.precio,
            es_regalo_promocion: false,
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

      const newProduct: Product = {
        ...product,
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

      // Update stock
      const fromStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.from_location_id)
      if (!fromStock) throw new Error(`Source stock not found`)
      
      // Release reservation and decrease stock
      fromStock.cantidad_reservada = (fromStock.cantidad_reservada || 0) - transfer.cantidad
      fromStock.cantidad_disponible -= transfer.cantidad

      // Increase destination stock
      let toStock = stock.find(s => s.product_id === transfer.product_id && s.location_id === transfer.to_location_id)
      let stockLibreDestinoAntes = 0

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
        stockLibreDestinoAntes = toStock.cantidad_disponible - (toStock.cantidad_reservada || 0)
      }
      toStock.cantidad_disponible += transfer.cantidad

      // V2.0: Stock History (Exit from Source, Entry to Destination)
      const stockLibreOrigenAntes = fromStock.cantidad_disponible + transfer.cantidad - (fromStock.cantidad_reservada + transfer.cantidad)
      const stockLibreOrigenDespues = fromStock.cantidad_disponible - fromStock.cantidad_reservada
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

      await Promise.all([
        this.setStock(stock),
        this.setStockTransfers(transfers),
        this.setProductIMEIs(productIMEIs),
        this.setIMEIHistory([...imeiHistory, ...newIMEIHistory]),
        this.setStockHistory([...stockHistory, historySalida, historyEntrada])
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

      for (const item of request.items) {
        if (item.action === 'refund' || item.action === 'warranty_exchange') {
          const locationId = order.source_location_id
          if (!locationId) continue

          const stockEntry = updatedStock.find(s => s.product_id === item.product_id && s.location_id === locationId)
          
          if (stockEntry) {
            // Solo reingresar al stock disponible si NO es defectuoso
            if (item.condition !== 'defectuoso') {
              stockEntry.cantidad_disponible += item.quantity
            }
          } else {
            const nextStockId = Math.max(0, ...updatedStock.map(s => s.id)) + 1
            updatedStock.push({
              id: nextStockId,
              product_id: item.product_id,
              location_id: locationId,
              cantidad_disponible: item.condition !== 'defectuoso' ? item.quantity : 0,
              cantidad_reservada: 0
            })
          }

          // Add history
          const nextHistoryId = Math.max(0, ...newStockHistory.map(h => h.id)) + 1
          newStockHistory.push({
            id: nextHistoryId,
            product_id: item.product_id,
            location_id: locationId,
            tipo_cambio: 'devolucion',
            cantidad: item.quantity,
            stock_anterior: stockEntry ? stockEntry.cantidad_disponible - item.quantity : 0,
            stock_nuevo: stockEntry ? stockEntry.cantidad_disponible : item.quantity,
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
            }
          }
        }
      }

      await this.setReturns([...returns, newReturn])
      await this.setStock(updatedStock)
      await this.setStockHistory(newStockHistory)
      await this.setProductIMEIs(updatedIMEIs)
      await this.setIMEIHistory(updatedIMEIHistory)

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
}

export const inventoryService = new InventoryService()
