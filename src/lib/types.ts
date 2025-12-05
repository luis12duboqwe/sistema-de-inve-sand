export interface ProfileSettings {
  currency: string
  taxRate: number
  lowStockThreshold: number
  enableNotifications: boolean
  defaultPaymentMethod: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  defaultChannel: 'whatsapp' | 'facebook' | 'instagram'
  businessAddress?: string
  businessPhone?: string
  businessEmail?: string
  autoCalculateTax: boolean
  priceFormat: 'standard' | 'comma' | 'space'
}

export interface Profile {
  id: number
  name: string
  slug: string
  active: boolean
  settings?: ProfileSettings
}

export interface Product {
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
}

export interface Stock {
  id: number
  product_id: number
  cantidad_disponible: number
}

export interface Order {
  id: number
  profile_id: number
  customer_name: string
  customer_phone: string
  canal: 'whatsapp' | 'facebook' | 'instagram'
  metodo_pago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  total: number
  estado: 'pendiente' | 'por_entregar' | 'completada' | 'cancelada'
  created_at: string
  notas?: string
  updated_at?: string
}

export interface OrderItem {
  id: number
  order_id: number
  product_id: number
  cantidad: number
  precio_unitario: number
  es_regalo_promocion: boolean
}

export interface ProductWithStock extends Product {
  stock_disponible: number
}

export interface OrderWithItems extends Order {
  items: (OrderItem & { product?: Product })[]
}

export interface CreateOrderRequest {
  profile_slug: string
  canal: 'whatsapp' | 'facebook' | 'instagram'
  customer_name: string
  customer_phone: string
  metodo_pago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  items: {
    product_id: number
    cantidad: number
  }[]
  notas?: string
}

export interface Supplier {
  id: number
  profile_id: number
  nombre: string
  contacto: string
  telefono: string
  email?: string
  direccion?: string
  notas?: string
  activo: boolean
  created_at: string
}

export interface ProductWithSupplier extends ProductWithStock {
  supplier_id?: number
  supplier?: Supplier
}

export interface DateRange {
  from: Date
  to: Date
}

export interface AdvancedSearchFilters {
  dateRange?: DateRange
  minAmount?: number
  maxAmount?: number
  customerName?: string
  customerPhone?: string
  productId?: number
  supplierId?: number
}

export interface ReportData {
  totalRevenue: number
  totalOrders: number
  topProducts: Array<{
    product: ProductWithStock
    quantity: number
    revenue: number
  }>
  monthlyTrends: Array<{
    month: string
    revenue: number
    orders: number
  }>
  profitMargin: number
}
