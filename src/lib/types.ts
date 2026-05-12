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
  imei?: string            // IMEI del equipo defectuoso que entra (devuelto por el cliente)
  replacement_imei?: string // IMEI del equipo de reemplazo que sale (solo warranty_exchange)
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
  defaultChannel: 'whatsapp' | 'facebook' | 'instagram' | 'tienda'
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

export interface UserLocationAccess {
  id: number
  user_id: number
  location_id: number
  can_view: boolean
  can_edit: boolean
  can_close_cash: boolean
  can_count_stock: boolean
  can_receive_purchase: boolean
  created_at: string
  updated_at?: string
}

export type UserLocationAccessInput = Omit<UserLocationAccess, 'id' | 'user_id' | 'created_at' | 'updated_at'>

export interface AuditLogEntry {
  id: number
  user_id?: number
  username?: string
  action: string
  entity_type: string
  entity_id?: number
  location_id?: number
  before_data?: Record<string, any>
  after_data?: Record<string, any>
  metadata?: Record<string, any>
  created_at: string
}

export interface PurchaseReceiptItemInput {
  product_id: number
  quantity: number
  unit_cost: number
  imeis?: string[]
  notes?: string
}

export interface PurchaseReceiptInput {
  supplier_id?: number
  location_id: number
  invoice_number?: string
  notes?: string
  items: PurchaseReceiptItemInput[]
}

export interface PurchaseReceipt extends PurchaseReceiptInput {
  id: number
  status: string
  total_cost: number
  received_by?: string
  received_at: string
  created_at: string
}

export interface InventoryCountItemInput {
  product_id: number
  counted_quantity: number
  notes?: string
  imeis?: string[]
}

export interface InventoryCountInput {
  location_id: number
  notes?: string
  items: InventoryCountItemInput[]
}

export interface InventoryCountItem {
  id: number
  product_id: number
  expected_quantity: number
  counted_quantity: number
  difference: number
  imeis?: string[]
  notes?: string
}

export interface InventoryCount {
  id: number
  location_id: number
  status: 'draft' | 'approved' | 'rejected'
  notes?: string
  counted_by?: string
  approved_by?: string
  counted_at: string
  approved_at?: string
  created_at: string
  items: InventoryCountItem[]
}

export interface LocationDailyCloseInput {
  location_id: number
  close_date: string
  cash_counted: number
  transfer_total?: number
  card_total?: number
  financing_total?: number
  notes?: string
}

export interface LocationDailyClose extends LocationDailyCloseInput {
  id: number
  cash_expected: number
  transfer_expected: number
  card_expected: number
  financing_expected: number
  transfer_total: number
  card_total: number
  financing_total: number
  difference: number
  status: string
  closed_by?: string
  approved_by?: string
  closed_at: string
  approved_at?: string
}

// V2.0: Perfiles de venta (bots, vendedores)
export interface SalesProfile {
  id: number
  name: string
  slug: string
  tipo: 'bot_ia' | 'vendedor_humano' | 'sistema_automatico'
  canales: ('whatsapp' | 'facebook' | 'instagram' | 'tienda')[]
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
  imeis?: string[]
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

export interface OrderSummary {
  id: number
  profile_id?: number
  sales_profile_id?: number
  source_location_id?: number
  customer_name: string
  customer_phone: string
  canal: Order['canal']
  metodo_pago: Order['metodo_pago']
  total: number
  estado: Order['estado']
  notes?: string
  delivery_date?: string
  created_at: string
}

export interface CustomerStats {
  customer_phone: string
  customer_name: string
  total_orders: number
  total_spent: number
  average_order: number
  first_order_date: string
  last_order_date: string
  id?: number
  is_troll: boolean
  is_blocked: boolean
  reputation_score: number
  daily_message_count: number
}

export interface CustomerHistory extends CustomerStats {
  orders: OrderSummary[]
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
  sales_profile_name?: string
}

export interface ForecastingAlertItem {
  product_id: number
  product_name: string
  days_until_stockout: number
  restock_recommendation: number
  trend: 'increasing' | 'stable' | 'decreasing'
}

export interface AIProfileMetric {
  sales_profile_id: number
  sales_profile_name: string
  slug?: string
  is_ai_active: boolean
  last_interaction_at?: string
  interactions_last_7_days: number
  tokens_last_7_days: number
  pending_training_items: number
}

export interface AIStatusResponse {
  snapshot_generated_at: string
  total_sales_profiles: number
  ai_profiles_active: number
  ai_profiles_inactive: number
  interactions_last_24h: number
  tokens_last_24h: number
  avg_tokens_per_response: number
  customers_flagged: number
  training_backlog: number
  ai_profiles: AIProfileMetric[]
  forecasting_alerts: ForecastingAlertItem[]
}

export interface BusinessInsightTopSeller {
  product_id: number
  product_name: string
  units_sold: number
  revenue: number
  gross_profit: number
}

export interface BusinessInsightSlowMover {
  product_id: number
  product_name: string
  stock_available: number
  days_without_sales: number
  last_sale_at?: string | null
}

export interface BusinessInsightStockAlert {
  product_id: number
  product_name: string
  stock_available: number
  avg_daily_demand: number
  days_until_stockout?: number | null
}

export interface BusinessInsightTrendPoint {
  date: string
  revenue: number
}

export interface BusinessInsightsKPIs {
  total_revenue: number
  orders_count: number
  avg_order_value: number
  gross_margin_estimate: number
}

export interface BusinessInsightsMetrics {
  kpis: BusinessInsightsKPIs
  top_sellers: BusinessInsightTopSeller[]
  slow_movers: BusinessInsightSlowMover[]
  stock_alerts: BusinessInsightStockAlert[]
  revenue_trends: BusinessInsightTrendPoint[]
}

export interface BusinessInsightRecommendation {
  title: string
  action: string
  impact?: string
  category?: string
  priority: 'alta' | 'media' | 'baja' | 'critica'
}

export interface BusinessInsightsFilters {
  location_id?: number | null
  sales_profile_id?: number | null
  sales_profile_slug?: string | null
}

export interface BusinessInsightsResponse {
  generated_at: string
  period_days: number
  filters: BusinessInsightsFilters
  metrics: BusinessInsightsMetrics
  recommendations: BusinessInsightRecommendation[]
  ai_summary?: string | null
  tokens_used: number
  raw_response?: string | null
}

export interface DashboardStats {
  active_products: number
  total_products: number
  low_stock_count: number
  out_of_stock_count: number
  total_inventory_value: number
  pending_orders: number
  total_orders_today: number
  total_revenue_today: number
  total_revenue_month: number
  total_revenue_last_month: number
  gross_margin_month?: number
  average_ticket_month?: number
}

export interface TopProductReport {
  product_id: number
  product_name: string
  units_sold: number
  total_revenue: number
}

export interface SalesReport {
  period_start: string
  period_end: string
  total_orders: number
  total_revenue: number
  average_order_value: number
  top_products: TopProductReport[]
}

export interface InventoryAlert {
  product_id: number
  product_name: string
  sku: string
  current_stock: number
  category: string
  alert_level: 'critical' | 'low' | 'out_of_stock'
}

export interface StockSummaryByLocation {
  location_id: number
  location_nombre: string
  location_tipo: Location['tipo']
  total_productos: number
  total_unidades: number
  valor_inventario: number
}

export interface SalesSummaryByLocation {
  location_id: number
  location_nombre: string
  total_ordenes: number
  total_unidades_vendidas: number
  total_ingresos: number
  ticket_promedio: number
}

export interface TopProductByLocationEntry {
  product_id: number
  product_nombre: string
  product_categoria: Product['categoria']
  cantidad_vendida: number
  ingresos_totales: number
}

export interface BankTransferReconciliationItem {
  order_id: number
  created_at: string
  customer_name: string
  customer_phone: string
  location_id?: number
  location_nombre?: string
  bank_name?: string
  reference?: string
  total: number
  estado: Order['estado']
  validated_by?: string
  validada_at?: string
}

export interface BankTransferReconciliationReport {
  total_amount: number
  total_orders: number
  items: BankTransferReconciliationItem[]
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
  en_transito_salida?: number
  en_transito_entrada?: number
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
  canal: 'whatsapp' | 'facebook' | 'instagram' | 'tienda'
  metodo_pago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  transfer_bank_name?: string
  transfer_reference?: string
  transfer_reference_normalized?: string
  total: number
  financing_details?: string // JSON con datos de financiamiento (V2.1)
  estado: 'pendiente' | 'por_entregar' | 'completada' | 'validada' | 'cancelada'
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

export interface ProductRestockPayload {
  location_id: number
  cantidad: number
  costo_unitario: number
  supplier_id?: number
  notas?: string
  imeis?: string[]
}

export interface TradeIn {
  id?: number
  order_id?: number
  marca: string
  modelo: string
  color?: string
  capacidad?: string
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
  canal: 'whatsapp' | 'facebook' | 'instagram' | 'tienda'
  customer_name: string
  customer_phone: string
  metodo_pago: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  transfer_bank_name?: string
  transfer_reference?: string
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
  received_quantity?: number
  missing_quantity?: number
  incident_notes?: string
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
  tipo_cambio: 'venta' | 'venta_reserva' | 'venta_reserva_liberada' | 'VENTA_VALIDADA' | 'transferencia_salida' | 'transferencia_entrada' | 'transferencia_reserva' | 'transferencia_cancelada' | 'transferencia_rechazada' | 'transferencia_recepcion_parcial' | 'ajuste' | 'CONTEO_FISICO' | 'COMPRA_RECIBIDA' | 'devolucion' | 'retoma' | 'compra' | 'garantia_salida' | 'garantia_entrada' | 'devolucion_defectuosa'
  cantidad: number  // Positivo para entrada, negativo para salida
  stock_anterior: number
  stock_nuevo: number
  referencia_id?: number
  referencia_tipo?: 'order' | 'order_validated' | 'order_finalized' | 'purchase_receipt' | 'physical_inventory_count' | 'transfer' | 'adjustment' | 'transfer_pending' | 'transfer_rejected' | 'transfer_cancelled' | 'transfer_partial' | 'manual_adjustment' | 'product_creation' | 'order_update' | 'order_cancelled' | 'return' | 'initial_stock'
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
  supplier_id?: number
  imei: string
  vendido: boolean
  order_id?: number
  transfer_id?: number // V2.0: ID de transferencia si está en tránsito
  received_at?: string
  sold_at?: string
  acquisition_type?: string
  received_notes?: string
  received_by?: string
  created_at: string
  product_name?: string
  location_name?: string
  supplier_name?: string
}

export interface IMEIHistory {
  id: number
  imei: string
  product_id: number
  location_id?: number
  supplier_id?: number
  event_type: string
  reference_id?: number
  reference_type?: string
  notes?: string
  created_at: string
  created_by?: string
  product_name?: string
  location_name?: string
  supplier_name?: string
}

export interface IMEIDetail extends ProductIMEI {
  product_sku?: string
  customer_name?: string
  customer_phone?: string
  status_label?: string
  warranty_months?: number
  warranty_expires_at?: string
}

export type StockHistoryCreateRequest = Omit<StockHistory, 'id' | 'created_at'>

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
  conversation_summary?: string
  ai_memory_json?: string
  last_referenced_product_id?: number
  last_referenced_product_name?: string
  last_referenced_color?: string
  last_referenced_variant?: string
  memory_updated_at?: string
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

export interface AIContextPayload {
  sales_profile_slug: string
  customer_phone: string
  message_content: string
  customer_name?: string
}

export interface AIContextResponse {
  system_prompt: string
  bot_config: Record<string, any>
  customer_info: Record<string, any>
  relevant_inventory: string
  relevant_faqs: string
  financing_info: string
  previous_context: Array<Record<string, string>>
}

export interface PhotoRequestMedia {
  id: number
  photo_request_id: number
  media_url: string
  media_type: string
  uploaded_by_user_id?: number
  uploaded_at: string
  sent_to_customer_at?: string
  customer_viewed: boolean
}

export interface PhotoRequest {
  id: number
  customer_id: string
  product_id?: number
  product_name: string
  color_requested?: string
  size_requested?: string
  additional_notes?: string
  customer_name?: string
  origin_channel?: string
  status: string
  assigned_to_user_id?: number
  completion_notes?: string
  claimed_at?: string
  last_notified_at?: string
  notification_count: number
  priority_score?: number
  sla_breached?: boolean
  created_at: string
  resolved_at?: string
  agent_response_time_minutes?: number
  csat_score?: number
  csat_feedback?: string
  photo_urls?: string[]
  media_items?: PhotoRequestMedia[]
  assigned_to_user?: Record<string, unknown>
}

export interface PhotoRequestSummary {
  pending_total: number
  assigned_to_me: number
  overdue_total: number
  awaiting_upload_total: number
}

export interface AIReplyPayload extends AIContextPayload {
  conversation_override?: Array<Record<string, string>>
}

export interface AIReplyResponse {
  reply: string
  tokens_used: number
  model: string
  context: AIContextResponse
}

export interface AIInteractionLogPayload {
  sales_profile_slug: string
  customer_phone: string
  role: 'user' | 'assistant' | 'system'
  content: string
  tokens_used?: number
}

export interface AICreateOrderItemPayload {
  product_id?: number
  product_query?: string
  cantidad: number
  precio_unitario?: number
  imeis?: string[]
}

export interface AICreateOrderPayload {
  sales_profile_slug: string
  source_location_id: number
  customer_phone: string
  customer_name?: string
  canal?: 'whatsapp' | 'facebook' | 'instagram' | 'tienda'
  metodo_pago?: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  items: AICreateOrderItemPayload[]
  notes?: string
  auto_link_interaction?: boolean
}

export interface AICreateOrderResponse {
  status: 'created'
  order_id: number
  linked_interaction: boolean
}

export interface AIHandleOrderIntent {
  source_location_id: number
  items: AICreateOrderItemPayload[]
  canal?: 'whatsapp' | 'facebook' | 'instagram' | 'tienda'
  metodo_pago?: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'
  notes?: string
  auto_create?: boolean
  auto_link_interaction?: boolean
}

export interface AIHandleMessagePayload extends AIReplyPayload {
  message_id?: string
  channel_hint?: 'whatsapp' | 'facebook' | 'instagram' | 'messenger'
  order_intent?: AIHandleOrderIntent
}

export interface AIHandleMessageResponse extends AIReplyResponse {
  order?: AICreateOrderResponse
}

export interface ChannelHealthGlobal {
  has_verify_token: boolean
  has_default_sales_profile: boolean
  signature_validation_enabled: boolean
  message_ttl_seconds: number
  missing: string[]
}

export interface ChannelHealthChannel {
  ready: boolean
  missing: string[]
}

export interface ChannelHealthResponse {
  status: 'ok'
  ready: boolean
  global: ChannelHealthGlobal
  channels: {
    whatsapp: ChannelHealthChannel
    messenger: ChannelHealthChannel
    instagram: ChannelHealthChannel
  }
}

export interface TrainingSubmissionPayload {
  sales_profile_slug: string
  customer_question: string
  ai_proposed_answer?: string
}

export interface FlagTrollResponse {
  status: 'flagged'
  customer: string
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
  is_system_role: boolean
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
  created_at?: string
  updated_at?: string
}

export interface CreateUserRequest {
  username: string
  email?: string
  full_name?: string
  password?: string
  role_id: number
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

export interface PublicProduct {
  id: number
  nombre: string
  marca: string
  modelo: string
  categoria: Product['categoria']
  condicion: Product['condicion']
  precio: number
  moneda: string
  capacidad?: string
  color?: string
  in_stock: boolean
}

export interface PublicCatalogFilters {
  search?: string
  category?: string
  per_page?: number
  page?: number
}

export interface SetupInitialAdminRequest {
  username: string
  password: string
  email?: string
  full_name?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page?: number
  per_page?: number
  pages?: number
}

// --- Sincronización Local ↔ API -------------------------------------------------
export type SyncEntityType =
  | 'product'
  | 'stock'
  | 'supplier'
  | 'order'
  | 'stock_transfer'
  | 'location'
  | 'sales_profile'
  | 'profile'
  | 'return'
  | 'customer'
  | 'stock_history'
  | 'faq'
  | 'imei'
  | 'trade_in'
  | 'financing'
  | 'ai_profile'
  | 'rbac'
  | 'settings'

export type SyncActionType =
  | 'create'
  | 'update'
  | 'delete'
  | 'transfer'
  | 'assign'
  | 'confirm'
  | 'reject'
  | 'cancel'
  | 'resolve'

export interface SyncEventInput {
  entity: SyncEntityType
  action: SyncActionType
  entityId?: number | string | null
  payload: any
  origin?: 'local' | 'remote'
  metadata?: Record<string, any>
}

export interface SyncEvent extends SyncEventInput {
  id: string
  checksum: string
  timestamp: string
  retry_count: number
  last_error?: string
  synced_at?: string
}

export interface SyncJournalSummary {
  pending: number
  synced: number
  failed: number
  lastSyncAt?: string
}
