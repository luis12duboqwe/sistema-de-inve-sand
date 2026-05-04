import type { Bank, FinancingOption,
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
  IMEIDetail,
  IMEIHistory,
  ProductIMEI,
  AIProfileConfig,
  WarrantyStatus,
  AIStatusResponse,
  BusinessInsightsResponse,
  DashboardStats,
  SalesReport,
  InventoryAlert,
  StockSummaryByLocation,
  SalesSummaryByLocation,
  TopProductByLocationEntry,
  CustomerStats,
  CustomerHistory,
  StockHistory,
  StockHistoryStats,
  StockHistoryCreateRequest,
  AIContextPayload,
  AIContextResponse,
  AIReplyPayload,
  AIReplyResponse,
  AIInteractionLogPayload,
  AICreateOrderPayload,
  AICreateOrderResponse,
  AIHandleMessagePayload,
  AIHandleMessageResponse,
  ChannelHealthResponse,
  TrainingSubmissionPayload,
  FlagTrollResponse,
  PublicProduct,
  PublicCatalogFilters,
  PaginatedResponse,
  SetupInitialAdminRequest,
  AuthResponse,
  ProductRestockPayload
} from './types'
import type { SalesForecast } from './aiForecasting'
import { getKV } from './kvStorage'

const DEFAULT_API_URL = 'http://localhost:8000/api'

function getEnvironmentDefaultApiUrl(): string {
  if (typeof window === 'undefined') {
    return DEFAULT_API_URL
  }

  const hostname = window.location.hostname
  const port = window.location.port

  if (hostname.includes('.app.github.dev')) {
    const backendHostname = hostname.replace(/-\d+\.app\.github\.dev$/, '-8000.app.github.dev')
    return `https://${backendHostname}/api`
  }

  if (port === '5000' || port === '5173') {
    return `${window.location.origin}/api`
  }

  return 'http://localhost:8000/api'
}

function normalizeApiUrl(rawUrl: string | null | undefined): string | null {
  if (!rawUrl) {
    return null
  }

  const trimmed = rawUrl.trim()
  if (!trimmed) {
    return null
  }

  try {
    const parsed = new URL(trimmed)

    if (parsed.port === '5000' || parsed.port === '5173') {
      return null
    }

    const path = parsed.pathname.replace(/\/$/, '')
    if (!path.endsWith('/api')) {
      parsed.pathname = `${path}/api`
    }

    return parsed.toString().replace(/\/$/, '')
  } catch {
    return null
  }
}

// Caché en memoria para evitar múltiples llamadas a KV
let cachedApiUrl: string | null = null
let cacheTimestamp = 0
const CACHE_DURATION = 60000 // 60 segundos

async function getApiUrl(): Promise<string> {
  const now = Date.now()
  const environmentDefaultUrl = getEnvironmentDefaultApiUrl()
  const useSameOriginApi = typeof window !== 'undefined' && (window.location.port === '5000' || window.location.port === '5173')
  
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
        const parsedLocalUrl = normalizeApiUrl(JSON.parse(localValue) as string)
        if (parsedLocalUrl) {
          if (useSameOriginApi && /:\/\/localhost:8000\/api$|:\/\/127\.0\.0\.1:8000\/api$/i.test(parsedLocalUrl)) {
            cachedApiUrl = environmentDefaultUrl
            cacheTimestamp = now
            return cachedApiUrl
          }
          cachedApiUrl = parsedLocalUrl
          cacheTimestamp = now
          return cachedApiUrl
        }
      } catch {
        // Si falla el parse, continuar con el método normal
      }
    }
    
    // Si no está en localStorage, usar KV (con fallback automático)
    const kv = getKV()
    const url = await kv.get<string>('settings_api_url')
    const normalizedUrl = normalizeApiUrl(url)
    if (useSameOriginApi && normalizedUrl && /:\/\/localhost:8000\/api$|:\/\/127\.0\.0\.1:8000\/api$/i.test(normalizedUrl)) {
      cachedApiUrl = environmentDefaultUrl
      cacheTimestamp = now
      return cachedApiUrl
    }
    cachedApiUrl = normalizedUrl || environmentDefaultUrl
    cacheTimestamp = now
    return cachedApiUrl
  } catch (error) {
    console.warn('Error getting API URL, using cached or default:', error)
    return cachedApiUrl || environmentDefaultUrl
  }
}

// Función para actualizar la URL del API y limpiar el caché
export function updateApiUrl(newUrl: string): void {
  cachedApiUrl = normalizeApiUrl(newUrl) || getEnvironmentDefaultApiUrl()
  cacheTimestamp = Date.now()
  localStorage.setItem('spark-kv-settings_api_url', JSON.stringify(cachedApiUrl))
}

interface ApiProductWithStock {
  id: number
  profile_id: number
  sku: string
  nombre: string
  categoria: 'celular' | 'accesorio'
  marca: string
  modelo: string
  color?: string
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
  canal: 'whatsapp' | 'facebook' | 'instagram' | 'tienda'
  metodo_pago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  transfer_bank_name?: string
  transfer_reference?: string
  total: number
  estado: 'pendiente' | 'por_entregar' | 'completada' | 'cancelada'
  created_at: string
  items: {
    id: number
    product_id: number
    cantidad: number
    precio_unitario: number
    es_regalo_promocion: boolean
    imeis?: string[]
    product?: ApiProductWithStock
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
  private token: string | null = localStorage.getItem('auth_token')

  setToken(token: string) {
    this.token = token
    localStorage.setItem('auth_token', token)
  }

  getToken(): string | null {
    return this.token
  }

  logout() {
    this.token = null
    localStorage.removeItem('auth_token')
  }

  private mapApiOrder(apiOrder: ApiOrderResponse): OrderWithItems {
    return {
      ...apiOrder,
      customer_name: String(apiOrder.customer_name || ''),
      customer_phone: String(apiOrder.customer_phone || ''),
      items: (apiOrder.items || []).map(item => {
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
          product: productMapped,
          imeis: item.imeis
        }
      }),
      trade_ins: apiOrder.trade_ins?.map(t => ({
        ...t,
        condicion: t.condicion as 'usado' | 'dañado' | 'para_repuestos'
      }))
    }
  }

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
        
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          ...(options.headers as Record<string, string>),
        }

        if (this.token) {
          headers['Authorization'] = `Bearer ${this.token}`
        }

        const response = await fetch(url, {
          ...options,
          headers,
        })

        if (response.status === 401) {
          this.logout()
          window.dispatchEvent(new Event('auth:unauthorized'))
          throw new Error('Sesión expirada o credenciales inválidas. Por favor inicie sesión nuevamente.')
        }

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
            !errorMessage.includes('cancelar') &&
            !errorMessage.includes('AI Config not found')) {
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

  async login(username: string, password: string): Promise<AuthResponse> {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    // Note: request method adds Content-Type: application/json by default, so we override it
    const response = await this.request<AuthResponse>('/auth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    })
    
    if (response.access_token) {
      this.setToken(response.access_token)
    }
    
    // Fetch user details separately if not provided in token response
    if (!response.user) {
      try {
        const user = await this.request<import('./types').User>('/auth/me')
        response.user = user
      } catch (e) {
        console.error('Failed to fetch user details after login', e)
      }
    }
    
    return response
  }

  async setupInitialAdmin(payload: SetupInitialAdminRequest): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>('/auth/setup', {
      method: 'POST',
      body: JSON.stringify(payload)
    })

    if (response.access_token) {
      this.setToken(response.access_token)
    }

    return response
  }

  async getProductByIMEI(imei: string): Promise<ProductWithStock> {
    try {
      return await this.request<ProductWithStock>(`/products/imei/${imei}`)
    } catch (error) {
      console.error('Error fetching product by IMEI:', error)
      throw error
    }
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

  // --- Reports & Analytics ---

  async getDashboardStats(params?: { sales_profile_slug?: string; location_id?: number }): Promise<DashboardStats> {
    const queryParams = new URLSearchParams()
    if (params?.sales_profile_slug) queryParams.append('sales_profile_slug', params.sales_profile_slug)
    if (params?.location_id) queryParams.append('location_id', params.location_id.toString())

    const query = queryParams.toString()
    const endpoint = query ? `/reports/dashboard?${query}` : '/reports/dashboard'
    return this.request<DashboardStats>(endpoint)
  }

  async getSalesReport(params?: {
    sales_profile_slug?: string
    date_from?: string
    date_to?: string
    top_limit?: number
  }): Promise<SalesReport> {
    const queryParams = new URLSearchParams()
    if (params?.sales_profile_slug) queryParams.append('sales_profile_slug', params.sales_profile_slug)
    if (params?.date_from) queryParams.append('date_from', params.date_from)
    if (params?.date_to) queryParams.append('date_to', params.date_to)
    if (params?.top_limit) queryParams.append('top_limit', params.top_limit.toString())

    const query = queryParams.toString()
    const endpoint = query ? `/reports/sales?${query}` : '/reports/sales'
    return this.request<SalesReport>(endpoint)
  }

  async getInventoryAlerts(params?: { location_id?: number }): Promise<InventoryAlert[]> {
    const queryParams = new URLSearchParams()
    if (params?.location_id) queryParams.append('location_id', params.location_id.toString())
    const query = queryParams.toString()
    const endpoint = query ? `/reports/inventory/alerts?${query}` : '/reports/inventory/alerts'
    return this.request<InventoryAlert[]>(endpoint)
  }

  async getStockSummaryByLocation(activeOnly = true): Promise<StockSummaryByLocation[]> {
    const query = activeOnly ? '?active_only=true' : '?active_only=false'
    return this.request<StockSummaryByLocation[]>(`/reports/stock-summary-by-location${query}`)
  }

  async getSalesSummaryByLocation(params?: { start_date?: string; end_date?: string }): Promise<SalesSummaryByLocation[]> {
    const queryParams = new URLSearchParams()
    if (params?.start_date) queryParams.append('start_date', params.start_date)
    if (params?.end_date) queryParams.append('end_date', params.end_date)
    const query = queryParams.toString()
    const endpoint = query ? `/reports/sales-summary-by-location?${query}` : '/reports/sales-summary-by-location'
    return this.request<SalesSummaryByLocation[]>(endpoint)
  }

  async getTopProductsByLocation(
    locationId: number,
    params?: { start_date?: string; end_date?: string; limit?: number }
  ): Promise<TopProductByLocationEntry[]> {
    const queryParams = new URLSearchParams()
    if (params?.start_date) queryParams.append('start_date', params.start_date)
    if (params?.end_date) queryParams.append('end_date', params.end_date)
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    const query = queryParams.toString()
    const endpoint = query ? `/reports/top-products-by-location/${locationId}?${query}` : `/reports/top-products-by-location/${locationId}`
    return this.request<TopProductByLocationEntry[]>(endpoint)
  }

  // --- AI Intelligence Methods ---
  // (Moved to bottom of file to avoid duplicates)

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

  // --- AI Training & Customer Insights ---
  // (Moved to bottom of file)

  async getLocation(id: number): Promise<Location> {
    try {
      return await this.request<Location>(`/locations/${id}`)
    } catch (error) {
      console.error('Error getting location from API:', error)
      throw new Error(`Failed to get location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getLocationStock(locationId: number): Promise<StockByLocation[]> {
    try {
      return await this.request<StockByLocation[]>(`/locations/${locationId}/stock`)
    } catch (error) {
      console.error('Error getting location stock via API:', error)
      throw new Error(`Failed to get location stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
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

  async getProducts(params?: { 
    profile_slug?: string, 
    search?: string, 
    include_inactive?: boolean,
    per_page?: number,
    page?: number
  }): Promise<{ items: ProductWithStock[]; total: number }> {
    try {
      const queryParams = new URLSearchParams()
      // V2.0: profile_slug is ignored by backend
      // if (params?.profile_slug) queryParams.append('profile_slug', params.profile_slug)
      if (params?.search) queryParams.append('search', params.search)
      if (params?.include_inactive) queryParams.append('include_inactive', 'true')
      if (params?.per_page) queryParams.append('per_page', params.per_page.toString())
      if (params?.page) queryParams.append('page', params.page.toString())

      const query = queryParams.toString()
      const endpoint = query ? `/products?${query}` : '/products'
      
      return await this.request<{ items: ProductWithStock[]; total: number }>(endpoint)
    } catch (error) {
      console.error('Error getting products from API:', error)
      throw new Error(`Failed to get products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive = false
  ): Promise<ProductWithStock[]> {
    try {
      const perPage = 100
      let page = 1
      const collected: ProductWithStock[] = []

      while (true) {
        const params = new URLSearchParams()
        // V2.0: profile_slug is ignored by backend, removing to avoid confusion
        // if (profileSlug) params.append('profile_slug', profileSlug)
        if (search) params.append('search', search)
        if (includeInactive) params.append('include_inactive', 'true')
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/products?${params.toString()}`
        const response = await this.request<{
          items: ProductWithStock[]
          total?: number
          page?: number
          per_page?: number
          pages?: number
        }>(endpoint)

        const items = response.items || []
        collected.push(...items)

        const total = typeof response.total === 'number' ? response.total : collected.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (items.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }

      return collected
    } catch (error) {
      console.error('Error fetching products from API:', error)
      throw new Error(`Failed to fetch products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getPublicCatalog(filters?: PublicCatalogFilters): Promise<PaginatedResponse<PublicProduct>> {
    const queryParams = new URLSearchParams()
    if (filters?.search) queryParams.append('search', filters.search)
    if (filters?.category) queryParams.append('category', filters.category)
    if (filters?.per_page) queryParams.append('per_page', filters.per_page.toString())
    if (filters?.page) queryParams.append('page', filters.page.toString())
    const query = queryParams.toString()
    const endpoint = query ? `/public/catalog?${query}` : '/public/catalog'
    return this.request<PaginatedResponse<PublicProduct>>(endpoint)
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

  async fetchProductIMEIs(filters: {
    vendido?: boolean
    location_id?: number
    product_id?: number
    search?: string
  } = {}): Promise<ProductIMEI[]> {
    const perPage = 250
    let page = 1
    const collected: ProductIMEI[] = []

    try {
      while (true) {
        const params = new URLSearchParams()
        if (filters.vendido !== undefined) params.append('vendido', String(filters.vendido))
        if (filters.location_id) params.append('location_id', filters.location_id.toString())
        if (filters.product_id) params.append('product_id', filters.product_id.toString())
        if (filters.search) params.append('search', filters.search)
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/imeis?${params.toString()}`
        const response = await this.request<PaginatedResponse<ProductIMEI>>(endpoint)
        const items = response.items || []
        collected.push(...items)

        const total = typeof response.total === 'number' ? response.total : collected.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (items.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }
    } catch (error) {
      console.error('Error fetching product IMEIs:', error)
      throw new Error(`Failed to fetch IMEIs: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }

    return collected
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

  async restockProduct(productId: number, payload: ProductRestockPayload): Promise<ProductWithStock> {
    try {
      return await this.request<ProductWithStock>(`/products/${productId}/restock`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    } catch (error) {
      console.error('Error restocking product via API:', error)
      throw new Error(`Failed to restock product: ${error instanceof Error ? error.message : 'Unknown error'}`)
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
      const perPage = 100
      let page = 1
      const orders: OrderWithItems[] = []

      while (true) {
        const params = new URLSearchParams()
        if (salesProfileSlug) params.append('sales_profile_slug', salesProfileSlug)
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/orders?${params.toString()}`
        const response = await this.request<{
          items: ApiOrderResponse[]
          total?: number
          page?: number
          per_page?: number
          pages?: number
        }>(endpoint)

        const apiOrders = response.items || []
        orders.push(...apiOrders.map(order => this.mapApiOrder(order)))

        const total = typeof response.total === 'number' ? response.total : orders.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (apiOrders.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }

      return orders
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

      return this.mapApiOrder(apiOrder)
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
  ): Promise<OrderWithItems> {
    try {
      // Si se quiere cancelar, usar el endpoint especial que libera stock
      if (estado === 'cancelada') {
        return await this.cancelOrder(orderId)
      }

      const apiOrder = await this.request<ApiOrderResponse>(`/orders/${orderId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ estado }),
      })

      return this.mapApiOrder(apiOrder)
    } catch (error) {
      console.error('Error updating order status via API:', error)
      throw new Error(`Failed to update order status: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async cancelOrder(orderId: number, reason?: string): Promise<OrderWithItems> {
    try {
      const query = reason ? `?reason=${encodeURIComponent(reason)}` : ''
      const apiOrder = await this.request<ApiOrderResponse>(`/orders/${orderId}/cancel${query}`, {
        method: 'POST',
      })
      return this.mapApiOrder(apiOrder)
    } catch (error) {
      console.error('Error cancelling order via API:', error)
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
      transfer_bank_name?: string
      transfer_reference?: string
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
    try {
      const sanitizedUpdates = {
        ...updates,
        customer_phone: updates.customer_phone ? String(updates.customer_phone).trim() : undefined,
        transfer_bank_name: updates.transfer_bank_name?.trim() || updates.transfer_bank_name,
        transfer_reference: updates.transfer_reference?.trim() || updates.transfer_reference,
        notas: updates.notas?.trim() || updates.notas
      }

      const apiOrder = await this.request<ApiOrderResponse>(`/orders/${orderId}`, {
        method: 'PUT',
        body: JSON.stringify(sanitizedUpdates),
      })

      return this.mapApiOrder(apiOrder)
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

  async confirmStockTransfer(id: number, confirmed_by: string, scanned_imeis?: string[]): Promise<StockTransfer> {
    try {
      return this.request(`/stock-transfers/${id}/confirm`, {
        method: 'POST',
        body: JSON.stringify({ confirmed_by, scanned_imeis })
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

  async fetchIMEIHistoryEntries(filters: {
    imei?: string
    product_id?: number
    location_id?: number
    days?: number
  } = {}): Promise<IMEIHistory[]> {
    const perPage = 250
    let page = 1
    const collected: IMEIHistory[] = []

    try {
      while (true) {
        const params = new URLSearchParams()
        if (filters.imei) params.append('imei', filters.imei)
        if (filters.product_id) params.append('product_id', filters.product_id.toString())
        if (filters.location_id) params.append('location_id', filters.location_id.toString())
        if (filters.days) params.append('days', filters.days.toString())
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/imeis/history?${params.toString()}`
        const response = await this.request<PaginatedResponse<IMEIHistory>>(endpoint)
        const items = response.items || []
        collected.push(...items)

        const total = typeof response.total === 'number' ? response.total : collected.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (items.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }
    } catch (error) {
      console.error('Error fetching IMEI history:', error)
      throw new Error(`Failed to fetch IMEI history: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }

    return collected
  }

  async getIMEIHistory(imei: string): Promise<IMEIHistory[]> {
    try {
      return this.request<IMEIHistory[]>(`/imeis/history/${imei}`)
    } catch (error) {
      console.error('Error getting IMEI history:', error)
      throw new Error(`Failed to get IMEI history: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getIMEIDetail(imei: string): Promise<IMEIDetail | null> {
    try {
      return this.request<IMEIDetail>(`/imeis/detail/${imei}`)
    } catch (error) {
      console.error('Error getting IMEI detail:', error)
      throw new Error(`Failed to get IMEI detail: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async checkWarrantyStatus(imei: string): Promise<WarrantyStatus> {
    try {
      return this.request<WarrantyStatus>(`/imeis/${imei}/warranty-status`)
    } catch (error) {
      console.error('Error checking warranty status:', error)
      throw new Error(`Failed to check warranty status: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // ==========================================
  // MÓDULO DE INTELIGENCIA ARTIFICIAL (V2.1)
  // ==========================================

  async getAIProfileConfig(salesProfileId: number): Promise<AIProfileConfig | null> {
    try {
      return await this.request<AIProfileConfig>(`/ai/config/${salesProfileId}`)
    } catch {
      // Si no existe (404), retornamos null para que el UI sepa que debe crear uno
      return null
    }
  }

  async updateAIProfileConfig(salesProfileId: number, config: Partial<AIProfileConfig>): Promise<AIProfileConfig> {
    try {
      return await this.request<AIProfileConfig>(`/ai/config/${salesProfileId}`, {
        method: 'POST',
        body: JSON.stringify(config)
      })
    } catch (error) {
      console.error('Error updating AI config:', error)
      throw new Error(`Failed to update AI config: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async generateBusinessInsights(params: {
    sales_profile_slug?: string
    sales_profile_id?: number
    location_id?: number
    days?: number
    use_cache?: boolean
    force_refresh?: boolean
  } = {}): Promise<BusinessInsightsResponse> {
    try {
      const payload = {
        ...params,
        use_cache: params.use_cache ?? true,
        force_refresh: params.force_refresh ?? false
      }
      return await this.request<BusinessInsightsResponse>('/ai/business-insights', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
    } catch (error) {
      console.error('Error generating business insights:', error)
      throw new Error(`Failed to generate business insights: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getAIContext(payload: AIContextPayload): Promise<AIContextResponse> {
    return this.request<AIContextResponse>('/ai/context', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async generateAIReply(payload: AIReplyPayload): Promise<AIReplyResponse> {
    const handled = await this.request<AIHandleMessageResponse>('/ai/handle-message', {
      method: 'POST',
      body: JSON.stringify(payload)
    })

    return {
      reply: handled.reply,
      tokens_used: handled.tokens_used,
      model: handled.model,
      context: handled.context
    }
  }

  async logAIInteraction(payload: AIInteractionLogPayload): Promise<{ status: string }> {
    return this.request<{ status: string }>('/ai/log', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async submitAITrainingExample(payload: TrainingSubmissionPayload): Promise<{ status: string }> {
    return this.request<{ status: string }>('/ai/training/submit', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async flagCustomerAsTroll(phoneNumber: string, reason: string): Promise<FlagTrollResponse> {
    return this.request<FlagTrollResponse>('/ai/flag-troll', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber, reason })
    })
  }

  async linkOrderToInteraction(customerPhone: string, orderId: number): Promise<void> {
    try {
      await this.request('/ai/link-order', {
        method: 'POST',
        body: JSON.stringify({ customer_phone: customerPhone, order_id: orderId })
      })
    } catch (error) {
      // Non-critical error, just log it
      console.warn('Failed to link order to interaction:', error)
    }
  }

  async createOrderFromAIIntent(payload: AICreateOrderPayload): Promise<AICreateOrderResponse> {
    return this.request<AICreateOrderResponse>('/ai/create-order', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async handleAIMessage(payload: AIHandleMessagePayload): Promise<AIHandleMessageResponse> {
    return this.request<AIHandleMessageResponse>('/ai/handle-message', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async getChannelsHealth(): Promise<ChannelHealthResponse> {
    return this.request<ChannelHealthResponse>('/channels/health')
  }

  async testChannelConnection(salesProfileSlug: string, channel: string): Promise<{
    status: 'success' | 'error'
    channel: string
    sales_profile_slug: string
    details: string
    timestamp: string
  }> {
    return this.request('/channels/test-connection/' + salesProfileSlug + '/' + channel, {
      method: 'POST'
    })
  }

  async getPhotoRequests(params?: {
    assigned_to_me?: boolean
    status?: string
  }): Promise<any[]> {
    const query = new URLSearchParams()
    if (params?.assigned_to_me !== undefined) query.append('assigned_to_me', String(params.assigned_to_me))
    if (params?.status) query.append('status', params.status)
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return this.request<any[]>(`/photo-requests/pending${suffix}`)
  }

  async getPhotoRequest(photoRequestId: number): Promise<any> {
    return this.request<any>(`/photo-requests/${photoRequestId}`)
  }

  async getPhotoRequestSummary(): Promise<import('./types').PhotoRequestSummary> {
    return this.request<import('./types').PhotoRequestSummary>('/photo-requests/summary')
  }

  async uploadPhotoMedia(photoRequestId: number, payload: {
    media_url: string
    media_type?: 'photo' | 'video' | '360_view'
    metadata?: Record<string, unknown>
  }): Promise<any> {
    return this.request<any>(`/photo-requests/${photoRequestId}/media`, {
      method: 'POST',
      body: JSON.stringify({
        media_url: payload.media_url,
        media_type: payload.media_type || 'photo',
        metadata: payload.metadata || {}
      })
    })
  }

  async uploadPhotoFile(photoRequestId: number, file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)

    const apiBaseUrl = await getApiUrl()
    const headers: HeadersInit = {}
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`
    }

    const response = await fetch(`${apiBaseUrl}/photo-requests/${photoRequestId}/upload-file`, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (!response.ok) {
      let message = `HTTP ${response.status}`
      try {
        const error = await response.json()
        message = error.detail || message
      } catch {
        // ignore parsing error
      }
      throw new Error(message)
    }

    return response.json()
  }

  async claimPhotoRequest(photoRequestId: number): Promise<any> {
    return this.request<any>(`/photo-requests/${photoRequestId}/claim`, {
      method: 'POST'
    })
  }

  async sendPhotosToCustomer(photoRequestId: number): Promise<{
    status: string
    message: string
    photo_request_id: number
  }> {
    return this.request<{
      status: string
      message: string
      photo_request_id: number
    }>(`/photo-requests/${photoRequestId}/send-to-customer`, {
      method: 'POST'
    })
  }

  async updatePhotoRequest(photoRequestId: number, payload: {
    status?: string
    completion_notes?: string
  }): Promise<any> {
    return this.request<any>(`/photo-requests/${photoRequestId}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    })
  }

  async listTrainingQueue(status = 'pending'): Promise<import('./types').TrainingQueueItem[]> {
    const perPage = 100
    let page = 1
    const collected: import('./types').TrainingQueueItem[] = []

    try {
      while (true) {
        const params = new URLSearchParams()
        params.append('status', status)
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/ai/training-queue?${params.toString()}`
        const response = await this.request<PaginatedResponse<import('./types').TrainingQueueItem>>(endpoint)
        const items = response.items || []
        collected.push(...items)

        const total = typeof response.total === 'number' ? response.total : collected.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (items.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }
    } catch (error) {
      console.error('Error fetching training queue:', error)
      return []
    }

    return collected
  }

  async getTrainingQueue(status: string = 'pending'): Promise<any[]> {
      return this.listTrainingQueue(status)
  }

  async resolveTrainingItem(itemId: number, action: 'approve' | 'reject' | 'convert_to_faq', correction?: string): Promise<void> {
    try {
      await this.request(`/ai/training-queue/${itemId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ action, correction }),
        headers: { 'Content-Type': 'application/json' }
      })
    } catch (error) {
      console.error('Error resolving training item:', error)
      throw new Error(`Failed to resolve item: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateTrainingQueueItem(id: number, updates: Partial<import('./types').TrainingQueueItem>): Promise<import('./types').TrainingQueueItem> {
    if (updates.status && ['approved', 'rejected', 'converted_to_faq'].includes(updates.status)) {
      const statusToAction: Record<string, 'approve' | 'reject' | 'convert_to_faq'> = {
        'approved': 'approve',
        'rejected': 'reject',
        'converted_to_faq': 'convert_to_faq'
      }
      
      await this.resolveTrainingItem(
        id, 
        statusToAction[updates.status], 
        updates.admin_correction
      )
      
      // Fetch the updated item to return it
      // Note: The item might move to a different list based on status, so we search in the new status list
      const queue = await this.listTrainingQueue(updates.status)
      const item = queue.find(i => i.id === id)
      if (item) return item
    }

    try {
      return await this.request<import('./types').TrainingQueueItem>(`/ai/training-queue/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
        headers: { 'Content-Type': 'application/json' }
      })
    } catch (error) {
      console.error('Error updating training queue item:', error)
      throw new Error(`Failed to update training queue item: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listCustomers(search?: string, options?: { isTroll?: boolean }): Promise<import('./types').Customer[]> {
    const perPage = 100
    let page = 1
    const collected: import('./types').Customer[] = []

    try {
      while (true) {
        const params = new URLSearchParams()
        if (search) params.append('search', search)
        if (options?.isTroll !== undefined) params.append('is_troll', String(options.isTroll))
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/ai/customers?${params.toString()}`
        const response = await this.request<PaginatedResponse<import('./types').Customer>>(endpoint)
        const items = response.items || []
        collected.push(...items)

        const total = typeof response.total === 'number' ? response.total : collected.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (items.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }
    } catch (error) {
      console.error('Error listing customers:', error)
      return []
    }

    return collected
  }

  async listCustomerStats(params?: {
    sales_profile_slug?: string
    page?: number
    per_page?: number
  }): Promise<CustomerStats[]> {
    try {
      const queryParams = new URLSearchParams()
      if (params?.sales_profile_slug) queryParams.append('sales_profile_slug', params.sales_profile_slug)
      if (params?.page) queryParams.append('page', params.page.toString())
      if (params?.per_page) queryParams.append('per_page', params.per_page.toString())
      const query = queryParams.toString()
      const endpoint = query ? `/customers?${query}` : '/customers'
      return await this.request<CustomerStats[]>(endpoint)
    } catch (error) {
      console.error('Error fetching customer stats:', error)
      throw error instanceof Error ? error : new Error('Failed to fetch customer stats')
    }
  }

  async getCustomerStatsByPhone(
    customerPhone: string,
    params?: { sales_profile_slug?: string }
  ): Promise<CustomerStats> {
    const queryParams = new URLSearchParams()
    if (params?.sales_profile_slug) queryParams.append('sales_profile_slug', params.sales_profile_slug)
    const query = queryParams.toString()
    const endpoint = query
      ? `/customers/${encodeURIComponent(customerPhone)}/stats?${query}`
      : `/customers/${encodeURIComponent(customerPhone)}/stats`
    return this.request<CustomerStats>(endpoint)
  }

  async getCustomerHistory(
    customerPhone: string,
    params?: { sales_profile_slug?: string }
  ): Promise<CustomerHistory> {
    const queryParams = new URLSearchParams()
    if (params?.sales_profile_slug) queryParams.append('sales_profile_slug', params.sales_profile_slug)
    const query = queryParams.toString()
    const endpoint = query
      ? `/customers/${encodeURIComponent(customerPhone)}/history?${query}`
      : `/customers/${encodeURIComponent(customerPhone)}/history`
    return this.request<CustomerHistory>(endpoint)
  }

  async getCustomers(search?: string): Promise<import('./types').Customer[]> {
    return this.listCustomers(search)
  }

  async updateCustomerStatus(id: number, updates: { is_troll?: boolean; is_blocked?: boolean; notes?: string }): Promise<import('./types').Customer> {
    try {
      return await this.request<import('./types').Customer>(`/ai/customers/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
        headers: { 'Content-Type': 'application/json' }
      })
    } catch (error) {
      console.error('Error updating customer:', error)
      throw error
    }
  }

  async updateCustomer(customerId: number, updates: any): Promise<import('./types').Customer> {
    return this.updateCustomerStatus(customerId, updates)
  }


  async getBanks(activeOnly: boolean = true): Promise<Bank[]> {
    try {
      return this.request<Bank[]>(`/financing/banks?active_only=${activeOnly}`)
    } catch (error) {
      console.error('Error fetching banks:', error)
      return []
    }
  }

  async createBank(bank: Partial<Bank>): Promise<Bank> {
    return this.request<Bank>('/financing/banks', {
      method: 'POST',
      body: JSON.stringify(bank)
    })
  }

  async updateBank(id: number, bank: Partial<Bank>): Promise<Bank> {
    return this.request<Bank>(`/financing/banks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(bank)
    })
  }

  async createFinancingOption(bankId: number, option: Partial<FinancingOption>): Promise<FinancingOption> {
    return this.request<FinancingOption>(`/financing/options?bank_id=${bankId}`, {
      method: 'POST',
      body: JSON.stringify(option)
    })
  }

  async deleteFinancingOption(optionId: number): Promise<void> {
    return this.request<void>(`/financing/options/${optionId}`, {
      method: 'DELETE'
    })
  }

  // User Management
  async listUsers(search?: string): Promise<import('./types').User[]> {
    const perPage = 100
    let page = 1
    const collected: import('./types').User[] = []

    try {
      while (true) {
        const params = new URLSearchParams()
        if (search) params.append('search', search)
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/auth/users?${params.toString()}`
        const response = await this.request<PaginatedResponse<import('./types').User>>(endpoint)
        const items = response.items || []
        collected.push(...items)

        const total = typeof response.total === 'number' ? response.total : collected.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (items.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }
    } catch (error) {
      console.error('Error listing users:', error)
      return []
    }

    return collected
  }

  async createUser(user: Partial<import('./types').User> & { password?: string }): Promise<import('./types').User> {
    return this.request<import('./types').User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(user)
    })
  }

  async deleteUser(userId: number): Promise<void> {
    return this.request<void>(`/auth/users/${userId}`, {
      method: 'DELETE'
    })
  }

  async listRoles(): Promise<import('./types').Role[]> {
    const perPage = 100
    let page = 1
    const collected: import('./types').Role[] = []

    try {
      while (true) {
        const params = new URLSearchParams()
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/auth/roles?${params.toString()}`
        const response = await this.request<PaginatedResponse<import('./types').Role>>(endpoint)
        const items = response.items || []
        collected.push(...items)

        const total = typeof response.total === 'number' ? response.total : collected.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (items.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }
    } catch (error) {
      console.error('Error listing roles:', error)
      return []
    }

    return collected
  }

  async updateUserRole(userId: number, roleId: number): Promise<import('./types').User> {
    return this.request<import('./types').User>(`/auth/users/${userId}/role?role_id=${roleId}`, {
      method: 'PUT'
    })
  }

  async updateUser(userId: number, updates: Partial<import('./types').User> & { password?: string; role_id?: number }): Promise<import('./types').User> {
    return this.request<import('./types').User>(`/auth/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    })
  }

  async listPermissions(): Promise<import('./types').Permission[]> {
    const perPage = 200
    let page = 1
    const collected: import('./types').Permission[] = []

    try {
      while (true) {
        const params = new URLSearchParams()
        params.append('per_page', perPage.toString())
        params.append('page', page.toString())

        const endpoint = `/auth/permissions?${params.toString()}`
        const response = await this.request<PaginatedResponse<import('./types').Permission>>(endpoint)
        const items = response.items || []
        collected.push(...items)

        const total = typeof response.total === 'number' ? response.total : collected.length
        const totalPages = response.pages ?? Math.max(1, Math.ceil(total / perPage))
        if (items.length < perPage || page >= totalPages) {
          break
        }

        page += 1
      }
    } catch (error) {
      console.error('Error listing permissions:', error)
      return []
    }

    return collected
  }

  // Trade-In Policies
  async getTradeInPolicies(): Promise<import('./types').TradeInPolicy[]> {
    return this.request<import('./types').TradeInPolicy[]>('/ai/trade-in-policies')
  }

  async createTradeInPolicy(policy: Omit<import('./types').TradeInPolicy, 'id' | 'created_at'>): Promise<import('./types').TradeInPolicy> {
    return this.request<import('./types').TradeInPolicy>('/ai/trade-in-policies', {
      method: 'POST',
      body: JSON.stringify(policy)
    })
  }

  async deleteTradeInPolicy(id: number): Promise<void> {
    return this.request<void>(`/ai/trade-in-policies/${id}`, {
      method: 'DELETE'
    })
  }
  async getStockHistory(productId: number, params?: {
    limit?: number
    tipo_cambio?: string
    date_from?: string
    date_to?: string
  }): Promise<StockHistory[]> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.tipo_cambio) queryParams.append('tipo_cambio', params.tipo_cambio)
    if (params?.date_from) queryParams.append('date_from', params.date_from)
    if (params?.date_to) queryParams.append('date_to', params.date_to)
    
    return this.request<StockHistory[]>(`/stock-history/product/${productId}?${queryParams.toString()}`)
  }

  async getLocationStockHistory(locationId: number, params?: {
    limit?: number
    tipo_cambio?: string
    days?: number
  }): Promise<StockHistory[]> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.tipo_cambio) queryParams.append('tipo_cambio', params.tipo_cambio)
    if (params?.days) queryParams.append('days', params.days.toString())
    const query = queryParams.toString()
    const endpoint = query
      ? `/stock-history/location/${locationId}?${query}`
      : `/stock-history/location/${locationId}`
    return this.request<StockHistory[]>(endpoint)
  }

  async getProfileStockHistory(profileId: number, params?: {
    limit?: number
    tipo_cambio?: string
    days?: number
  }): Promise<StockHistory[]> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.tipo_cambio) queryParams.append('tipo_cambio', params.tipo_cambio)
    if (params?.days) queryParams.append('days', params.days.toString())
    const query = queryParams.toString()
    const endpoint = query
      ? `/stock-history/profile/${profileId}?${query}`
      : `/stock-history/profile/${profileId}`
    return this.request<StockHistory[]>(endpoint)
  }

  async createStockHistoryEntry(payload: StockHistoryCreateRequest): Promise<StockHistory> {
    return this.request<StockHistory>('/stock-history', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async getProductStockStats(productId: number, days = 30): Promise<StockHistoryStats> {
    return this.request<StockHistoryStats>(`/stock-history/stats/${productId}?days=${days}`)
  }

  // FAQ Management
  async listFAQs(params?: { activa?: boolean, categoria?: string, page?: number, per_page?: number }): Promise<{ items: import('./types').FAQEntry[], total: number, pages: number }> {
    const queryParams = new URLSearchParams()
    if (params?.activa !== undefined) queryParams.append('activa', params.activa.toString())
    if (params?.categoria) queryParams.append('categoria', params.categoria)
    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.per_page) queryParams.append('per_page', params.per_page.toString())
    
    return this.request<{ items: import('./types').FAQEntry[], total: number, pages: number }>(`/faq?${queryParams.toString()}`)
  }

  async createFAQ(faq: Omit<import('./types').FAQEntry, 'id' | 'created_at' | 'updated_at' | 'veces_usada'>): Promise<import('./types').FAQEntry> {
    return this.request<import('./types').FAQEntry>('/faq', {
      method: 'POST',
      body: JSON.stringify(faq)
    })
  }

  async updateFAQ(id: number, updates: Partial<import('./types').FAQEntry>): Promise<import('./types').FAQEntry> {
    return this.request<import('./types').FAQEntry>(`/faq/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    })
  }

  async deleteFAQ(id: number): Promise<void> {
    return this.request<void>(`/faq/${id}`, {
      method: 'DELETE'
    })
  }

  async getForecasting(): Promise<SalesForecast[]> {
    try {
      return this.request<SalesForecast[]>('/forecasting/predict')
    } catch (error) {
      console.error('Error fetching forecasting:', error)
      throw new Error(`Failed to fetch forecasting: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getAIStatus(alertsLimit = 5): Promise<AIStatusResponse> {
    try {
      const params = new URLSearchParams({ alerts_limit: alertsLimit.toString() })
      return this.request<AIStatusResponse>(`/ai/status?${params.toString()}`)
    } catch (error) {
      console.error('Error fetching AI status:', error)
      throw new Error(`Failed to fetch AI status: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // ─────────────────────── CIERRE DE DÍA ───────────────────────────────────

  async getDailyClosePending(): Promise<any[]> {
    return this.request<any[]>('/daily-close/pending')
  }

  async getDailyCloseConfig(): Promise<{ configured: boolean; mensaje: string }> {
    return this.request<{ configured: boolean; mensaje: string }>('/daily-close/config')
  }

  async setDailyCloseConfig(data: {
    new_code: string
    confirm_code: string
    current_code?: string
  }): Promise<{ configured: boolean; mensaje: string }> {
    return this.request<{ configured: boolean; mensaje: string }>('/daily-close/config', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async validateDailyClose(data: {
    validation_code: string
    order_ids: number[]
    notas?: string
  }): Promise<{
    validated_count: number
    validated_orders: number[]
    total_ventas: number
    mensaje: string
  }> {
    return this.request('/daily-close/validate', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }
}

export const apiClient = new ApiClient()
