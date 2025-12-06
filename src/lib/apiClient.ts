import type {
  Profile,
  ProductWithStock,
  OrderWithItems,
  CreateOrderRequest,
  Product,
  Order
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
  condicion: 'nuevo' | 'usado' | 'reacondicionado' | 'grado A'
  precio: number
  moneda: string
  garantia_meses: number
  activo: boolean
  stock_disponible: number
}

interface ApiOrderResponse {
  id: number
  profile_id: number
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
        console.error(`API request failed for ${endpoint}:`, lastError)
        
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

  async createProduct(
    product: Omit<Product, 'id' | 'activo'>,
    initialStock: number
  ): Promise<ProductWithStock> {
    try {
      return this.request<ProductWithStock>('/products', {
        method: 'POST',
        body: JSON.stringify({
          ...product,
          activo: true,
          stock_inicial: initialStock,
        }),
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

  async updateStock(productId: number, cantidad: number): Promise<void> {
    try {
      await this.request(`/products/${productId}/stock`, {
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
      console.error('Error deleting product via API:', error)
      throw new Error(`Failed to delete product: ${error instanceof Error ? error.message : 'Unknown error'}`)
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
      console.error('Error deleting order via API:', error)
      throw new Error(`Failed to delete order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[]): Promise<ProductWithStock[]> {
    try {
      const productsToCreate = productsData.map(p => ({
        profile_id: p.profile_id!,
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
        stock_inicial: p.stock_disponible || 0
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

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    try {
      const params = new URLSearchParams()
      if (profileSlug) params.append('profile_slug', profileSlug)
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
          return {
            id: item.id,
            order_id: order.id,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: item.precio_unitario,
            es_regalo_promocion: item.es_regalo_promocion,
            product: product ? {
              id: product.id,
              profile_id: product.profile_id,
              sku: product.sku,
              nombre: product.nombre,
              categoria: product.categoria,
              marca: product.marca,
              modelo: product.modelo,
              capacidad: product.capacidad,
              condicion: product.condicion,
              precio: product.precio,
              moneda: product.moneda,
              garantia_meses: product.garantia_meses,
              activo: product.activo,
            } : undefined
          }
        })
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
      
      const apiOrder = await this.request<ApiOrderResponse>('/orders', {
        method: 'POST',
        body: JSON.stringify(sanitizedRequest),
      })

      return {
        ...apiOrder,
        items: apiOrder.items.map(item => {
          const product = item.product
          return {
            id: item.id,
            order_id: apiOrder.id,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: item.precio_unitario,
            es_regalo_promocion: item.es_regalo_promocion,
            product: product ? {
              id: product.id,
              profile_id: product.profile_id,
              sku: product.sku,
              nombre: product.nombre,
              categoria: product.categoria,
              marca: product.marca,
              modelo: product.modelo,
              capacidad: product.capacidad,
              condicion: product.condicion,
              precio: product.precio,
              moneda: product.moneda,
              garantia_meses: product.garantia_meses,
              activo: product.activo,
            } : undefined
          }
        })
      }
    } catch (error) {
      console.error('Error creating order via API:', error)
      throw new Error(`Failed to create order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<Order> {
    try {
      return this.request<Order>(`/orders/${orderId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ estado }),
      })
    } catch (error) {
      console.error('Error updating order status via API:', error)
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
      items?: Array<{
        id?: number
        product_id: number
        cantidad: number
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
          return {
            id: item.id,
            order_id: apiOrder.id,
            product_id: item.product_id,
            cantidad: item.cantidad,
            precio_unitario: item.precio_unitario,
            es_regalo_promocion: item.es_regalo_promocion,
            product: product ? {
              id: product.id,
              profile_id: product.profile_id,
              sku: product.sku,
              nombre: product.nombre,
              categoria: product.categoria,
              marca: product.marca,
              modelo: product.modelo,
              capacidad: product.capacidad,
              condicion: product.condicion,
              precio: product.precio,
              moneda: product.moneda,
              garantia_meses: product.garantia_meses,
              activo: product.activo,
            } : undefined
          }
        })
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
}

export const apiClient = new ApiClient()
