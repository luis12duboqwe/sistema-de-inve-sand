import type {
  Profile,
  ProductWithStock,
  OrderWithItems,
  CreateOrderRequest,
  Product,
  Order
} from './types'

const DEFAULT_API_URL = 'http://localhost:8000/api'

async function getApiUrl(): Promise<string> {
  const url = await window.spark.kv.get<string>('settings_api_url')
  return url || DEFAULT_API_URL
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
    options: RequestInit = {}
  ): Promise<T> {
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

      return response.json()
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error)
      if (error instanceof Error) {
        throw error
      }
      throw new Error(`Request failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listProfiles(): Promise<Profile[]> {
    try {
      return this.request<Profile[]>('/profiles')
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

      const query = params.toString()
      const endpoint = query ? `/products?${query}` : '/products'
      
      return this.request<ProductWithStock[]>(endpoint)
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

      const query = params.toString()
      const endpoint = query ? `/orders?${query}` : '/orders'
      
      const apiOrders = await this.request<ApiOrderResponse[]>(endpoint)
      
      return apiOrders.map(order => ({
        ...order,
        customer_name: String(order.customer_name || ''),
        customer_phone: String(order.customer_phone || ''),
        items: order.items.map(item => {
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
