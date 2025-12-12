import type {
  Profile,
  ProductWithStock,
  OrderWithItems,
  CreateOrderRequest,
  Product,
  Order,
  SalesProfile,
  Location,
  Supplier,
  CreateStockTransferRequest,
  StockTransfer,
  StockByLocation,
  CreateReturnRequest,
  Return,
  IMEIHistory
} from './types'
import { getKV } from './kvStorage'

const DEFAULT_API_URL = 'http://localhost:8000/api'

// Caché en memoria para evitar múltiples llamadas a KV
let cachedApiUrl: string | null = null
let cacheTimestamp = 0
const CACHE_DURATION = 60000 // 60 segundos

async function getApiUrl(): Promise<string> {
  const now = Date.now()
  
  // Si tenemos un valor en caché válido, usarlo
  if (cachedApiUrl && (now - cacheTimestamp) < CACHE_DURATION) {
    return cachedApiUrl
  }
  
  try {
    // Primero intentar desde localStorage (más rápido)
    const localStorageKey = 'spark-kv-settings_api_url'
    const localValue = localStorage.getItem(localStorageKey)
    if (localValue) {
      try {
        cachedApiUrl = JSON.parse(localValue) as string
        cacheTimestamp = now
        return cachedApiUrl
      } catch {
        // Si falla el parse, continuar con el método normal
      }
    }
    
    // Si no está en localStorage, usar KV (con fallback automático)
    const kv = getKV()
    const url = await kv.get<string>('settings_api_url')
    cachedApiUrl = url || DEFAULT_API_URL
    cacheTimestamp = now
    return cachedApiUrl
  } catch (error) {
    console.warn('Error getting API URL, using cached or default:', error)
    return cachedApiUrl || DEFAULT_API_URL
  }
}

// Función para actualizar la URL del API y limpiar el caché
export function updateApiUrl(newUrl: string): void {
  cachedApiUrl = newUrl
  cacheTimestamp = Date.now()
  localStorage.setItem('spark-kv-settings_api_url', JSON.stringify(newUrl))
}

interface ApiProductResponse {
  id: number
  profile_id: number
  sku: string
  nombre: string
  categoria: 'celular' | 'accesorio'
  marca: string
  modelo: string
  capacidad: string
  condicion: 'nuevo' | 'usado' | 'reacondicionado'
  precio: number
  moneda: string
  garantia_meses: number
  activo: boolean
  is_serialized?: boolean
  stock_disponible: number
  stock_items?: StockByLocation[]
}

interface ApiOrderResponse {
  id: number
  profile_id?: number
  sales_profile_id?: number
  source_location_id?: number
  customer_name: string
  customer_phone: string
  canal: 'whatsapp' | 'facebook' | 'instagram'
  metodo_pago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  total: number
  estado: 'pendiente' | 'por_entregar' | 'completada' | 'cancelada'
  created_at: string
  items: {
    id: number
    product_id: number
    cantidad: number
    precio_unitario: number
    es_regalo_promocion: boolean
    product?: ApiProductResponse
  }[]
  trade_ins?: {
    id: number
    marca: string
    modelo: string
    imei?: string
    condicion: string
    valor_estimado: number
    notas?: string
    created_at: string
  }[]
}

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retries = 3
  ): Promise<T> {
    let lastError: Error | null = null
    
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const apiBaseUrl = await getApiUrl()
        const url = `${apiBaseUrl}${endpoint}`
        
        const response = await fetch(url, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          },
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
          throw new Error(errorData.detail || `API Error: ${response.status}`)
        }

        // Si es 204 No Content, devolver objeto vacío en lugar de parsear JSON
        if (response.status === 204) {
          return {} as T
        }

        return response.json()
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown error')
        
        // Si es un error de red (Failed to fetch), reintentamos
        if (lastError.message.includes('Failed to fetch') && attempt < retries - 1) {
          console.warn(`API request failed for ${endpoint} (attempt ${attempt + 1}/${retries}), retrying...`)
          // Espera progresiva: 500ms, 1000ms, 1500ms
          await new Promise(resolve => setTimeout(resolve, (attempt + 1) * 500))
          continue
        }
        
        // Para otros errores o último intento, lanzamos el error
        // Evitar loguear errores de validación de negocio conocidos como errores críticos
        const errorMessage = lastError.message || ''
        if (!errorMessage.includes('referenciado') && 
            !errorMessage.includes('históricas') && 
            !errorMessage.includes('completada') && 
            !errorMessage.includes('cancelar')) {
            console.error(`API request failed for ${endpoint}:`, lastError)
        }
        
        // Mensaje de error más descriptivo
        if (lastError.message.includes('Failed to fetch')) {
          const apiBaseUrl = await getApiUrl()
          throw new Error(
            `No se puede conectar al backend en ${apiBaseUrl}. ` +
            `Verifica que el servidor esté corriendo. ` +
            `Puedes inicializarlo con: bash /workspaces/spark-template/run-backend-direct.sh`
          )
        }
        
        throw lastError
      }
    }
    
    throw lastError || new Error('Request failed after retries')
  }

  async listProfiles(): Promise<Profile[]> {
    try {
      const response = await this.request<{ items: Profile[]; total: number }>('/profiles?per_page=100')
      // El backend devuelve { items: [], total, page, per_page, pages }
      return response.items || []
    } catch (error) {
      console.error('Error listing profiles from API:', error)
      throw new Error(`Failed to list profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listSalesProfiles(): Promise<SalesProfile[]> {
    try {
      const response = await this.request<SalesProfile[]>('/sales-profiles?active=true')
      return response || []
    } catch (error) {
      console.error('Error listing sales profiles from API:', error)
      throw new Error(`Failed to list sales profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createSalesProfile(payload: Omit<SalesProfile, 'id' | 'created_at' | 'updated_at' | 'active'> & { active?: boolean }): Promise<SalesProfile> {
    try {
      return this.request<SalesProfile>('/sales-profiles', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    } catch (error) {
      console.error('Error creating sales profile via API:', error)
      throw new Error(`Failed to create sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateSalesProfile(id: number, updates: Partial<SalesProfile>): Promise<SalesProfile> {
    try {
      return this.request<SalesProfile>(`/sales-profiles/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      })
    } catch (error) {
      console.error('Error updating sales profile via API:', error)
      throw new Error(`Failed to update sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteSalesProfile(id: number): Promise<void> {
    try {
      await this.request<void>(`/sales-profiles/${id}`, { method: 'DELETE' })
    } catch (error) {
      console.error('Error deleting sales profile via API:', error)
      throw new Error(`Failed to delete sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listLocations(activeOnly = false): Promise<Location[]> {
    try {
      const endpoint = activeOnly ? '/locations?activo=true' : '/locations'
      const response = await this.request<Location[]>(endpoint)
      console.log('📍 API listLocations response:', response)
      // El backend retorna directamente un array, no { items: [] }
      return Array.isArray(response) ? response : []
    } catch (error) {
      console.error('Error listing locations from API:', error)
      throw new Error(`Failed to list locations: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getLocation(id: number): Promise<Location> {
    try {
      return await this.request<Location>(`/locations/${id}`)
    } catch (error) {
      console.error('Error getting location from API:', error)
      throw new Error(`Failed to get location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getSalesProfile(id: number): Promise<SalesProfile> {
    try {
      return await this.request<SalesProfile>(`/sales-profiles/${id}`)
    } catch (error) {
      console.error('Error getting sales profile from API:', error)
      throw new Error(`Failed to get sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listSuppliers(includeInactive = false): Promise<Supplier[]> {
    try {
      const endpoint = includeInactive ? '/suppliers?include_inactive=true' : '/suppliers?include_inactive=false'
      const response = await this.request<{ items: Supplier[] }>(endpoint)
      return response?.items || []
    } catch (error) {
      console.error('Error listing suppliers from API:', error)
      throw new Error(`Failed to list suppliers: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createLocation(payload: Omit<Location, 'id' | 'created_at' | 'updated_at' | 'activo'> & { activo?: boolean }): Promise<Location> {
    try {
      return this.request<Location>('/locations', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    } catch (error) {
      console.error('Error creating location via API:', error)
      throw new Error(`Failed to create location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateLocation(id: number, updates: Partial<Location>): Promise<Location> {
    try {
      return this.request<Location>(`/locations/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      })
    } catch (error) {
      console.error('Error updating location via API:', error)
      throw new Error(`Failed to update location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteLocation(id: number): Promise<void> {
    try {
      await this.request<void>(`/locations/${id}`, { method: 'DELETE' })
    } catch (error) {
      console.error('Error deleting location via API:', error)
      throw new Error(`Failed to delete location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createProfile(name: string, slug: string): Promise<Profile> {
    try {
      return this.request<Profile>('/profiles', {
        method: 'POST',
        body: JSON.stringify({ name, slug, active: true }),
      })
    } catch (error) {
      console.error('Error creating profile via API:', error)
      throw new Error(`Failed to create profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateProfile(profileId: number, updates: { name?: string; active?: boolean }): Promise<Profile> {
    try {
      return this.request<Profile>(`/profiles/${profileId}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      })
    } catch (error) {
      console.error('Error updating profile via API:', error)
      throw new Error(`Failed to update profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive = false
  ): Promise<ProductWithStock[]> {
    try {
      const params = new URLSearchParams()
      if (profileSlug) params.append('profile_slug', profileSlug)
      if (search) params.append('search', search)
      if (includeInactive) params.append('include_inactive', 'true')
      params.append('per_page', '100') // Límite máximo del backend

      const query = params.toString()
      const endpoint = query ? `/products?${query}` : '/products?per_page=100'
      
      const response = await this.request<{ items: ProductWithStock[]; total: number }>(endpoint)
      // El backend devuelve { items: [], total, page, per_page, pages }
      return response.items || []
    } catch (error) {
      console.error('Error fetching products from API:', error)
      throw new Error(`Failed to fetch products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getAvailableIMEIs(productId: number, locationId: number): Promise<string[]> {
    try {
      const endpoint = `/products/${productId}/imeis?location_id=${locationId}`
      return await this.request<string[]>(endpoint)
    } catch (error) {
      console.error('Error fetching IMEIs from API:', error)
      return []
    }
  }

  async createProduct(
    product: Omit<Product, 'id' | 'activo'>,
    initialStock: number,
    locationId?: number  // V2.0: ID de ubicación para stock inicial
  ): Promise<ProductWithStock> {
    try {
      const body: any = {
        ...product,
        activo: true,
        stock_inicial: initialStock,
      }
      
      // V2.0: Agregar locationId si se proporciona
      if (locationId) {
        body.initial_location_id = locationId
        
        // V2.0: Transformar imeis (string[]) a imeis_con_ubicacion (objeto[])
        if (body.imeis && Array.isArray(body.imeis) && body.imeis.length > 0) {
          body.imeis_con_ubicacion = body.imeis.map((imei: string) => ({
            imei,
            location_id: locationId
          }))
          // Eliminar campo legacy para forzar uso de V2.0 en backend
          delete body.imeis
        }
      }
      
      return this.request<ProductWithStock>('/products', {
        method: 'POST',
        body: JSON.stringify(body),
      })
    } catch (error) {
      console.error('Error creating product via API:', error)
      throw new Error(`Failed to create product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateProduct(
    productId: number,
    updates: Partial<Product>
  ): Promise<ProductWithStock> {
    try {
      return this.request<ProductWithStock>(`/products/${productId}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      })
    } catch (error) {
      console.error('Error updating product via API:', error)
      throw new Error(`Failed to update product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateStock(productId: number, cantidad: number, locationId: number): Promise<void> {
    try {
      if (!locationId) {
        throw new Error('locationId is required to actualizar stock por ubicación (V2.0)')
      }

      await this.request(`/products/${productId}/stock?location_id=${locationId}`, {
        method: 'PUT',
        body: JSON.stringify({ cantidad_disponible: cantidad }),
      })
    } catch (error) {
      console.error('Error updating stock via API:', error)
      throw new Error(`Failed to update stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteProduct(productId: number): Promise<void> {
    try {
      await this.request(`/products/${productId}`, {
        method: 'DELETE',
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      if (!message.includes('referenciado') && !message.includes('históricas')) {
          console.error('Error deleting product via API:', error)
      }
      throw new Error(`Failed to delete product: ${message}`)
    }
  }

  async getStockByLocation(productId: number, includeInactiveLocations = false): Promise<StockByLocation[]> {
    try {
      const query = includeInactiveLocations ? '?include_inactive_locations=true' : ''
      return await this.request<StockByLocation[]>(`/products/${productId}/stock/by-location${query}`)
    } catch (error) {
      console.error('Error fetching stock by location:', error)
      throw new Error(`Failed to fetch stock by location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateStockByLocation(productId: number, locationId: number, cantidad: number): Promise<void> {
    try {
      await this.request(`/products/${productId}/stock/location/${locationId}?cantidad=${cantidad}`, {
        method: 'POST'
      })
    } catch (error) {
      console.error('Error updating stock by location:', error)
      throw new Error(`Failed to update stock by location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteOrder(orderId: number): Promise<void> {
    try {
      const apiBaseUrl = await getApiUrl()
      const fullUrl = `${apiBaseUrl}/orders/${orderId}`
      console.log(`🗑️ Eliminando orden ${orderId} via API...`)
      console.log(`📡 DELETE URL: ${fullUrl}`)
      await this.request(`/orders/${orderId}`, {
        method: 'DELETE',
      })
      console.log(`✅ Orden ${orderId} eliminada exitosamente`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      if (!message.includes('completada') && !message.includes('cancelar')) {
          console.error('Error deleting order via API:', error)
      }
      throw new Error(`Failed to delete order: ${message}`)
    }
  }

  async cancelOrder(orderId: number, reason?: string): Promise<OrderWithItems> {
    try {
      const query = reason ? `?reason=${encodeURIComponent(reason)}` : ''
      return await this.request<OrderWithItems>(`/orders/${orderId}/cancel${query}`, {
        method: 'POST',
      })
    } catch (error) {
      console.error('Error cancelling order via API:', error)
      throw new Error(`Failed to cancel order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[], locationId?: number): Promise<ProductWithStock[]> {
    try {
      if (!locationId) {
        throw new Error('locationId es obligatorio para carga masiva en V2.0')
      }

      const productsToCreate = productsData.map(p => ({
        profile_id: p.profile_id,
        sku: p.sku!,
        nombre: p.nombre!,
        categoria: p.categoria!,
        marca: p.marca!,
        modelo: p.modelo || '',
        capacidad: p.capacidad || '',
        condicion: p.condicion!,
        precio: p.precio!,
        moneda: p.moneda || 'HNL',
        garantia_meses: p.garantia_meses || 0,
        activo: true,
        stock_inicial: p.stock_disponible || 0,
        initial_location_id: locationId
      }))

      return this.request<ProductWithStock[]>('/products/bulk', {
        method: 'POST',
        body: JSON.stringify({ products: productsToCreate }),
      })
    } catch (error) {
      console.error('Error bulk creating products via API:', error)
      throw new Error(`Failed to bulk create products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchOrders(salesProfileSlug?: string): Promise<OrderWithItems[]> {
    try {
      const params = new URLSearchParams()
      if (salesProfileSlug) params.append('sales_profile_slug', salesProfileSlug)
      params.append('per_page', '100') // Límite máximo del backend

      const query = params.toString()
      const endpoint = query ? `/orders?${query}` : '/orders?per_page=100'
      
      const response = await this.request<{ items: ApiOrderResponse[]; total: number }>(endpoint)
      // El backend devuelve { items: [], total, page, per_page, pages }
      const apiOrders = response.items || []
      
      return apiOrders.map(order => ({
        ...order,
        customer_name: String(order.customer_name || ''),
        customer_phone: String(order.customer_phone || ''),
        items: (order.items || []).map(item => {
          const product = item.product
          const productMapped = product
            ? {
                ...product,
                condicion: product.condicion as Product['condicion']
              }
            : undefined
          return {
            id: item.id,
            order_id: order.id,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: item.precio_unitario,
            es_regalo_promocion: item.es_regalo_promocion,
            product: productMapped
          }
        }),
        trade_ins: order.trade_ins?.map(t => ({
          ...t,
          condicion: t.condicion as 'usado' | 'dañado' | 'para_repuestos'
        }))
      }))
    } catch (error) {
      console.error('Error fetching orders from API:', error)
      throw new Error(`Failed to fetch orders: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    try {
      const sanitizedRequest = {
        ...request,
        customer_phone: String(request.customer_phone || '').trim()
      }

      if (!sanitizedRequest.source_location_id) {
        throw new Error('source_location_id es obligatorio para crear órdenes (V2.0)')
      }

      if (!sanitizedRequest.sales_profile_slug && !sanitizedRequest.profile_slug) {
        throw new Error('Debe proporcionar sales_profile_slug (V2.0) o profile_slug (legacy)')
      }
      
      const apiOrder = await this.request<ApiOrderResponse>('/orders', {
        method: 'POST',
        body: JSON.stringify(sanitizedRequest),
      })

      return {
        ...apiOrder,
        items: apiOrder.items.map(item => {
          const product = item.product
          const productMapped = product
            ? {
                ...product,
                condicion: product.condicion as Product['condicion']
              }
            : undefined

          return {
            id: item.id,
            order_id: apiOrder.id,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: item.precio_unitario,
            es_regalo_promocion: item.es_regalo_promocion,
            product: productMapped
          }
        }),
        trade_ins: apiOrder.trade_ins?.map(t => ({
          ...t,
          condicion: t.condicion as 'usado' | 'dañado' | 'para_repuestos'
        }))
      }
    } catch (error) {
      // Bug #6: Mejor manejo de errores para exponer mensaje del backend
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      console.error('Order creation failed:', {
        payload: request,
        error: errorMessage,
        timestamp: new Date().toISOString()
      })
      throw new Error(errorMessage)
    }
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<Order> {
    try {
      // Si se quiere cancelar, usar el endpoint especial que libera stock
      if (estado === 'cancelada') {
        return await this.cancelOrder(orderId)
      }
      
      return this.request<Order>(`/orders/${orderId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ estado }),
      })
    } catch (error) {
      console.error('Error updating order status via API:', error)
      throw new Error(`Failed to update order status: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async cancelOrder(orderId: number): Promise<Order> {
    try {
      return this.request<Order>(`/orders/${orderId}/cancel`, {
        method: 'POST',
      })
    } catch (error) {
      console.error('Error canceling order via API:', error)
      throw new Error(`Failed to cancel order: ${error instanceof Error ? error.message : 'Unknown error'}`)
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
        imeis?: string[]
      }>
    }
  ): Promise<OrderWithItems> {
    try {
      const sanitizedUpdates = {
        ...updates,
        customer_phone: updates.customer_phone ? String(updates.customer_phone).trim() : undefined
      }

      const apiOrder = await this.request<ApiOrderResponse>(`/orders/${orderId}`, {
        method: 'PUT',
        body: JSON.stringify(sanitizedUpdates),
      })

      return {
        ...apiOrder,
        items: apiOrder.items.map(item => {
          const product = item.product
          const productMapped = product
            ? {
                ...product,
                condicion: product.condicion as Product['condicion']
              }
            : undefined

          return {
            id: item.id,
            order_id: apiOrder.id,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: item.precio_unitario,
            es_regalo_promocion: item.es_regalo_promocion,
            product: productMapped
          }
        }),
        trade_ins: apiOrder.trade_ins?.map(t => ({
          ...t,
          condicion: t.condicion as 'usado' | 'dañado' | 'para_repuestos'
        }))
      }
    } catch (error) {
      console.error('Error updating order via API:', error)
      throw new Error(`Failed to update order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async initializeData(): Promise<void> {
    try {
      await this.request('/init-data', {
        method: 'POST',
      })
    } catch (error) {
      console.error('Error initializing data via API:', error)
      throw new Error(`Failed to initialize data: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async checkHealth(): Promise<{ status: string; database: string }> {
    try {
      return this.request('/health')
    } catch (error) {
      console.error('Error checking API health:', error)
      throw new Error(`Failed to check API health: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // V2.0: Stock Transfers between Locations
  async createStockTransfer(transfer: CreateStockTransferRequest): Promise<StockTransfer> {
    try {
      return this.request('/stock-transfers', {
        method: 'POST',
        body: JSON.stringify(transfer)
      })
    } catch (error) {
      console.error('Error creating stock transfer:', error)
      throw new Error(`Failed to create transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listStockTransfers(filters?: {
    product_id?: number
    from_location_id?: number
    to_location_id?: number
    location_id?: number  // Buscar donde la ubicación es origen O destino
    estado?: 'pendiente' | 'confirmada' | 'rechazada' | 'cancelada'
  }): Promise<StockTransfer[]> {
    try {
      const params = new URLSearchParams()
      if (filters?.product_id) params.append('product_id', filters.product_id.toString())
      if (filters?.location_id) params.append('location_id', filters.location_id.toString())
      if (filters?.from_location_id) params.append('from_location_id', filters.from_location_id.toString())
      if (filters?.to_location_id) params.append('to_location_id', filters.to_location_id.toString())
      if (filters?.estado) params.append('estado', filters.estado)
      
      const queryString = params.toString()
      const response: any = await this.request(`/stock-transfers${queryString ? '?' + queryString : ''}`)
      
      // Mapear respuesta paginada del backend
      const items = response.items || response
      
      // Agregar helper product para facilitar uso en componentes
      return items.map((t: any) => ({
        ...t,
        product: t.product_nombre ? {
          id: t.product_id,
          nombre: t.product_nombre,
          sku: t.product_sku
        } : undefined
      }))
    } catch (error) {
      console.error('Error listing stock transfers:', error)
      throw new Error(`Failed to list transfers: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getStockTransfer(id: number): Promise<StockTransfer> {
    try {
      return this.request(`/stock-transfers/${id}`)
    } catch (error) {
      console.error('Error getting stock transfer:', error)
      throw new Error(`Failed to get transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async confirmStockTransfer(id: number, confirmed_by: string): Promise<StockTransfer> {
    try {
      return this.request(`/stock-transfers/${id}/confirm`, {
        method: 'POST',
        body: JSON.stringify({ confirmed_by })
      })
    } catch (error) {
      console.error('Error confirming stock transfer:', error)
      throw new Error(`Failed to confirm transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async rejectStockTransfer(id: number, rejected_by: string, rejection_reason?: string): Promise<StockTransfer> {
    try {
      return this.request(`/stock-transfers/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ rejected_by, rejection_reason })
      })
    } catch (error) {
      console.error('Error rejecting stock transfer:', error)
      throw new Error(`Failed to reject transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async cancelStockTransfer(id: number): Promise<void> {
    try {
      await this.request(`/stock-transfers/${id}`, {
        method: 'DELETE'
      })
    } catch (error) {
      console.error('Error canceling stock transfer:', error)
      throw new Error(`Failed to cancel transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createSupplier(supplier: Omit<Supplier, 'id' | 'created_at' | 'updated_at'>): Promise<Supplier> {
    try {
      return this.request<Supplier>('/suppliers', {
        method: 'POST',
        body: JSON.stringify(supplier)
      })
    } catch (error) {
      console.error('Error creating supplier:', error)
      throw new Error(`Failed to create supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateSupplier(id: number, updates: Partial<Supplier>): Promise<Supplier> {
    try {
      return this.request<Supplier>(`/suppliers/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates)
      })
    } catch (error) {
      console.error('Error updating supplier:', error)
      throw new Error(`Failed to update supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteSupplier(id: number): Promise<void> {
    try {
      await this.request(`/suppliers/${id}`, {
        method: 'DELETE'
      })
    } catch (error) {
      console.error('Error deleting supplier:', error)
      throw new Error(`Failed to delete supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createReturn(returnData: CreateReturnRequest): Promise<Return> {
    try {
      return this.request<Return>('/returns', {
        method: 'POST',
        body: JSON.stringify(returnData)
      })
    } catch (error) {
      console.error('Error creating return:', error)
      throw new Error(`Failed to create return: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getReturns(): Promise<Return[]> {
    try {
      const response = await this.request<{ items: Return[] }>('/returns')
      return response.items || []
    } catch (error) {
      console.error('Error getting returns:', error)
      throw new Error(`Failed to get returns: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getIMEIHistory(imei: string): Promise<IMEIHistory[]> {
    try {
      return this.request<IMEIHistory[]>(`/imeis/history/${imei}`)
    } catch (error) {
      console.error('Error getting IMEI history:', error)
      throw new Error(`Failed to get IMEI history: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }
}

export const apiClient = new ApiClient()
