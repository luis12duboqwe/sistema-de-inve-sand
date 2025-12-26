export interface FinancingOption {
  id: number
  bank_id: number
  months: number
  rate: number
  active: boolean
}

export interface Bank {
  id: number
  name: string
  active: boolean
  normal_card_rate: number
  financing_options: FinancingOption[]
}

export interface FinancingDetails {
  bank_id: number
  bank_name: string
  months: number
  rate: number
  surcharge: number
  monthly_payment: number
  original_total: number
  down_payment?: number // V2.1: Prima o pago inicial en efectivo
}

export interface ReturnItem {
  id?: number
  product_id: number
  quantity: number
  condition: 'nuevo' | 'defectuoso' | 'abierto'
  action: 'refund' | 'warranty_exchange' | 'store_credit'
  imei?: string
}

export interface CreateReturnRequest {
  order_id: number
  reason?: string
  created_by?: string
  items: ReturnItem[]
}

export interface Return {
  id: number
  order_id: number
  created_at: string
  reason?: string
  status: string
  created_by?: string
  items: ReturnItem[]
}

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
  exchangeRate?: number // V2.0: Tasa de cambio configurable
}

export interface Profile {
  id: number
  name: string
  slug: string
  active: boolean
  settings?: ProfileSettings
}

// V2.0: Ubicaciones físicas (tiendas, bodegas)
export interface Location {
  id: number
  nombre: string
  tipo: 'tienda' | 'bodega' | 'oficina'
  direccion?: string
  telefono?: string
  activo: boolean
  created_at: string
  updated_at?: string
}

// V2.0: Perfiles de venta (bots, vendedores)
export interface SalesProfile {
  id: number
  name: string
  slug: string
  tipo: 'bot_ia' | 'vendedor_humano' | 'sistema_automatico'
  canales: ('whatsapp' | 'facebook' | 'instagram')[]
  configuracion?: Record<string, any>
  active: boolean
  created_at: string
  updated_at?: string
}

// V2.1: Configuración de IA para perfiles de venta
export interface AIProfileConfig {
  id?: number
  sales_profile_id: number
  model_name: string
  temperature: number
  system_prompt: string
  initial_greeting?: string
  voice_tone?: string
  context_rules?: string
  is_active: boolean
  
  // V2.2: Personalización Avanzada
  business_description?: string
  sales_goal?: string
  negotiation_style?: string
  max_discount_rate?: number
  fallback_human_trigger?: string
}

// V2.1: Gestión de Clientes e IA
export interface Customer {
  id: number
  phone_number: string
  name?: string
  email?: string
  notes?: string
  is_troll: boolean
  is_blocked: boolean
  reputation_score: number
  daily_message_count: number
  last_interaction_at?: string
  created_at: string
}

export interface TrainingQueueItem {
  id: number
  sales_profile_id?: number
  customer_question: string
  ai_proposed_answer?: string
  admin_correction?: string
  status: 'pending' | 'approved' | 'rejected' | 'converted_to_faq'
  created_at: string
  sales_profile?: SalesProfile
}

// V2.0: Stock por ubicación
export interface StockByLocation {
  id: number
  product_id: number
  location_id: number
  cantidad_disponible: number
  cantidad_reservada: number  // V2.0: Stock reservado en transferencias pendientes
  cantidad_defectuosa?: number // V2.0: Stock defectuoso/merma
  stock_libre?: number  // Computed: cantidad_disponible - cantidad_reservada
  location?: Location
}

export interface Product {
  id: number
  profile_id?: number  // V2.0: Opcional, productos son globales (solo compatibilidad V1)
  supplier_id?: number
  sku: string
  nombre: string
  categoria: 'celular' | 'accesorio' | 'pendiente_revision'
  marca: string
  modelo: string
  color?: string // V2.1: Color específico
  capacidad?: string
  condicion: 'nuevo' | 'usado' | 'reacondicionado'
  precio: number
  costo?: number // V2.0: Costo para reportes financieros
  moneda: string
  garantia_meses: number
  garantia_condiciones?: string
  activo: boolean
  is_serialized?: boolean // V2.0: Control explícito de serialización
  imei?: string  // DEPRECATED: Usar imeis[]
  imeis?: string[]
  stock_disponible?: number  // Total consolidado de todas las ubicaciones
  stock_items?: StockByLocation[]  // V2.0: Stock por ubicación
}

export interface Stock {
  id: number
  product_id: number
  location_id?: number
  cantidad_disponible: number
  cantidad_reservada?: number
  cantidad_defectuosa?: number // V2.0: Stock defectuoso/merma
}

export interface Order {
  id: number
  profile_id?: number  // LEGACY V1
  sales_profile_id?: number  // V2.0: ID del perfil de venta
  source_location_id?: number  // V2.0: ID de la ubicación origen
  customer_name: string
  customer_phone: string
  canal: 'whatsapp' | 'facebook' | 'instagram'
  metodo_pago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  total: number
  financing_details?: string // JSON con datos de financiamiento (V2.1)
  estado: 'pendiente' | 'por_entregar' | 'completada' | 'cancelada'
  created_at: string
  notes?: string
  delivery_date?: string
  notas?: string
  updated_at?: string
  sales_profile?: SalesProfile  // V2.0: Perfil de venta expandido
  source_location?: Location  // V2.0: Ubicación origen expandida
  trade_ins?: TradeIn[] // V2.0: Equipos recibidos en parte de pago
}

export interface OrderItem {
  id: number
  order_id: number
  product_id: number
  cantidad: number
  precio_unitario: number
  es_regalo_promocion: boolean
  product?: Product
  imeis?: string[] // V2.0: IMEIs vendidos
}

export interface ProductWithStock extends Product {
  stock_disponible: number
  stock_items?: StockByLocation[]  // V2.0: Explícitamente incluir stock por ubicación
}

export interface TradeIn {
  id?: number
  order_id?: number
  marca: string
  modelo: string
  imei?: string
  condicion: 'usado' | 'dañado' | 'para_repuestos'
  valor_estimado: number
  precio_venta?: number // V2.0: Precio de venta sugerido
  notas?: string
  created_at?: string
}

export interface OrderWithItems extends Order {
  items: (OrderItem & { product?: Product })[]
  trade_ins?: TradeIn[]  // V2.0: Equipos recibidos en parte de pago
  financing_details?: string // JSON string
}

export interface CreateOrderRequest {
  profile_slug?: string  // LEGACY V1 (opcional)
  sales_profile_slug?: string  // V2.0: Slug del perfil de venta
  source_location_id: number  // V2.0: ID de ubicación origen (obligatorio)
  canal: 'whatsapp' | 'facebook' | 'instagram'
  customer_name: string
  customer_phone: string
  metodo_pago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  items: {
    product_id: number
    cantidad: number
    imeis?: string[]
    precio_unitario?: number
    es_regalo_promocion?: boolean // V2.1: Regalos/promos no suman al total
  }[]
  trade_ins?: TradeIn[]  // V2.0: Equipos recibidos en parte de pago
  notes?: string
  delivery_date?: string
  notas?: string
  financing_data?: {
    bank_id: number
    months: number
    down_payment?: number
  }
}

export interface Supplier {
  id: number
  profile_id?: number
  nombre: string
  contacto: string
  telefono: string
  email?: string
  direccion?: string
  notas?: string
  activo: boolean
  created_at: string
  updated_at?: string
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
  from_location_id: number  // V2.0: Ubicación origen
  to_location_id: number  // V2.0: Ubicación destino
  from_profile_id?: number  // Legacy V1, puede ser null
  to_profile_id?: number  // Legacy V1, puede ser null
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
  from_location_name?: string  // V2.0: Nombre de ubicación origen
  to_location_name?: string  // V2.0: Nombre de ubicación destino
  from_profile_name?: string  // Legacy V1
  to_profile_name?: string  // Legacy V1
  imeis?: string[] // V2.0: Lista de IMEIs transferidos
  // Helper para compatibilidad con componentes
  product?: { id: number; nombre: string; sku: string }
}

export interface CreateStockTransferRequest {
  product_id: number
  from_location_id: number  // V2.0: ID de ubicación origen
  to_location_id: number  // V2.0: ID de ubicación destino
  cantidad: number
  imeis?: string[] // V2.0: Lista de IMEIs específicos (opcional)
  notas?: string
  created_by?: string
}

export interface StockHistory {
  id: number
  product_id: number
  location_id?: number // V2.0: Ubicación donde ocurrió el movimiento
  tipo_cambio: 'venta' | 'transferencia_salida' | 'transferencia_entrada' | 'transferencia_reserva' | 'transferencia_cancelada' | 'transferencia_rechazada' | 'ajuste' | 'devolucion' | 'retoma' | 'compra'
  cantidad: number  // Positivo para entrada, negativo para salida
  stock_anterior: number
  stock_nuevo: number
  referencia_id?: number
  referencia_tipo?: 'order' | 'transfer' | 'adjustment' | 'transfer_pending' | 'transfer_rejected' | 'transfer_cancelled' | 'manual_adjustment' | 'product_creation' | 'order_update' | 'order_cancelled' | 'return' | 'initial_stock'
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

export interface ProductIMEI {
  id: number
  product_id: number
  location_id?: number
  imei: string
  vendido: boolean
  order_id?: number
  transfer_id?: number // V2.0: ID de transferencia si está en tránsito
  created_at: string
}

export interface IMEIHistory {
  id: number
  imei: string
  product_id: number
  location_id?: number
  event_type: string
  reference_id?: number
  reference_type?: string
  notes?: string
  created_at: string
  created_by?: string
  product_name?: string
  location_name?: string
}

// ==========================================
// MÓDULO DE INTELIGENCIA ARTIFICIAL (V2.1)
// ==========================================

export interface Customer {
  id: number
  phone_number: string
  name?: string
  email?: string
  notes?: string
  is_troll: boolean
  is_blocked: boolean
  reputation_score: number
  daily_message_count: number
  last_interaction_at?: string
  created_at: string
  updated_at?: string
}

export interface InteractionLog {
  id: number
  customer_id: number
  sales_profile_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  tokens_used: number
  converted_order_id?: number
  created_at: string
}

export interface TrainingQueueItem {
  id: number
  sales_profile_id: number
  customer_question: string
  ai_proposed_answer?: string
  admin_correction?: string
  status: 'pending' | 'approved' | 'rejected' | 'converted_to_faq'
  created_at: string
  updated_at?: string
  sales_profile?: SalesProfile
}

export interface Permission {
  id: number
  slug: string
  description?: string
  module: string
  // Compatibilidad con código anterior (opcionales)
  resource?: string
  action?: string
}

export interface Role {
  id: number
  name: string
  description?: string
  permissions: Permission[]
}

export interface User {
  id: number
  username: string
  email?: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  role_id?: number
  role?: Role
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user?: User
}

export interface TradeInPolicy {
  id: number
  rule_type: 'model_rejection' | 'brand_rejection' | 'condition_rejection'
  pattern: string
  action: 'reject' | 'accept_with_conditions'
  reason?: string
  is_active: boolean
  created_at: string
}

export interface FAQEntry {
  id: number
  pregunta_clave: string
  respuesta: string
  categoria?: string
  activa: boolean
  veces_usada: number
  created_at: string
  updated_at?: string
}

export interface WarrantyStatus {
  imei: string
  product?: string
  status: 'vigente' | 'vencida' | 'sin_garantia' | 'en_stock'
  sale_date?: string
  expiration_date?: string
  days_remaining?: number
  detail: string
}
