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
    product: ApiProductResponse
  }[]
}

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
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
  }

  async listProfiles(): Promise<Profile[]> {
    return this.request<Profile[]>('/profiles')
  }

  async createProfile(name: string, slug: string): Promise<Profile> {
    return this.request<Profile>('/profiles', {
      method: 'POST',
      body: JSON.stringify({ name, slug, active: true }),
    })
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive = false
  ): Promise<ProductWithStock[]> {
    const params = new URLSearchParams()
    if (profileSlug) params.append('profile_slug', profileSlug)
    if (search) params.append('search', search)
    if (includeInactive) params.append('include_inactive', 'true')

    const query = params.toString()
    const endpoint = query ? `/products?${query}` : '/products'
    
    return this.request<ProductWithStock[]>(endpoint)
  }

  async createProduct(
    product: Omit<Product, 'id' | 'activo'>,
    initialStock: number
  ): Promise<ProductWithStock> {
    return this.request<ProductWithStock>('/products', {
      method: 'POST',
      body: JSON.stringify({
        ...product,
        activo: true,
        stock_inicial: initialStock,
      }),
    })
  }

  async updateProduct(
    productId: number,
    updates: Partial<Product>
  ): Promise<ProductWithStock> {
    return this.request<ProductWithStock>(`/products/${productId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
  }

  async updateStock(productId: number, cantidad: number): Promise<void> {
    await this.request(`/products/${productId}/stock`, {
      method: 'PUT',
      body: JSON.stringify({ cantidad_disponible: cantidad }),
    })
  }

  async fetchOrders(profileSlug?: string): Promise<OrderWithItems[]> {
    const params = new URLSearchParams()
    if (profileSlug) params.append('profile_slug', profileSlug)

    const query = params.toString()
    const endpoint = query ? `/orders?${query}` : '/orders'
    
    const apiOrders = await this.request<ApiOrderResponse[]>(endpoint)
    
    return apiOrders.map(order => ({
      ...order,
      items: order.items.map(item => ({
        id: item.id,
        order_id: order.id,
        product_id: item.product_id,
        cantidad: item.cantidad,
        precio_unitario: item.precio_unitario,
        es_regalo_promocion: item.es_regalo_promocion,
        product: {
          id: item.product.id,
          profile_id: item.product.profile_id,
          sku: item.product.sku,
          nombre: item.product.nombre,
          categoria: item.product.categoria,
          marca: item.product.marca,
          modelo: item.product.modelo,
          capacidad: item.product.capacidad,
          condicion: item.product.condicion,
          precio: item.product.precio,
          moneda: item.product.moneda,
          garantia_meses: item.product.garantia_meses,
          activo: item.product.activo,
        }
      }))
    }))
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    const apiOrder = await this.request<ApiOrderResponse>('/orders', {
      method: 'POST',
      body: JSON.stringify(request),
    })

    return {
      ...apiOrder,
      items: apiOrder.items.map(item => ({
        id: item.id,
        order_id: apiOrder.id,
        product_id: item.product_id,
        cantidad: item.cantidad,
        precio_unitario: item.precio_unitario,
        es_regalo_promocion: item.es_regalo_promocion,
        product: {
          id: item.product.id,
          profile_id: item.product.profile_id,
          sku: item.product.sku,
          nombre: item.product.nombre,
          categoria: item.product.categoria,
          marca: item.product.marca,
          modelo: item.product.modelo,
          capacidad: item.product.capacidad,
          condicion: item.product.condicion,
          precio: item.product.precio,
          moneda: item.product.moneda,
          garantia_meses: item.product.garantia_meses,
          activo: item.product.activo,
        }
      }))
    }
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<Order> {
    return this.request<Order>(`/orders/${orderId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ estado }),
    })
  }

  async initializeData(): Promise<void> {
    await this.request('/init-data', {
      method: 'POST',
    })
  }

  async checkHealth(): Promise<{ status: string; database: string }> {
    return this.request('/health')
  }
}

export const apiClient = new ApiClient()
