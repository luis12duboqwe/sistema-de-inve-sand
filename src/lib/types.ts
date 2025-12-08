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
  supplier_id?: number
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
  garantia_condiciones?: string  // Condiciones de garantía del proveedor
  activo: boolean
  imei?: string  // DEPRECATED: Usar imeis[] para nuevos productos
  imeis?: string[]  // Array de IMEIs para productos con múltiples unidades
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
  notes?: string  // Notas adicionales de la orden
  delivery_date?: string  // Fecha de entrega programada
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
  notes?: string  // Notas adicionales de la orden
  delivery_date?: string  // Fecha de entrega programada
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

export interface StockTransfer {
  id: number
  product_id: number
  from_profile_id: number
  to_profile_id: number
  cantidad: number
  notas?: string
  estado: 'pendiente' | 'confirmada' | 'rechazada' | 'cancelada'
  confirmed_at?: string
  confirmed_by?: string
  rejection_reason?: string
  created_at: string
  created_by?: string
  product_nombre?: string
  product_sku?: string
  from_profile_name?: string
  to_profile_name?: string
}

export interface CreateStockTransferRequest {
  product_id: number
  from_profile_slug: string
  to_profile_slug: string
  cantidad: number
  notas?: string
  created_by?: string
}

export interface StockHistory {
  id: number
  product_id: number
  tipo_cambio: 'venta' | 'transferencia_salida' | 'transferencia_entrada' | 'ajuste' | 'devolucion'
  cantidad: number  // Positivo para entrada, negativo para salida
  stock_anterior: number
  stock_nuevo: number
  referencia_id?: number
  referencia_tipo?: 'order' | 'transfer' | 'adjustment'
  notas?: string
  usuario?: string
  created_at: string
}

export interface StockHistoryStats {
  product_id: number
  product_name: string
  period_days: number
  total_movements: number
  movements_by_type: Record<string, number>
  total_entrada: number
  total_salida: number
  stock_actual: number
}
