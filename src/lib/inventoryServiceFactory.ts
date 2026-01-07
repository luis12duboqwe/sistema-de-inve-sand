import { inventoryService as localService } from './inventoryService'
import { apiClient } from './apiClient'
import { getKV } from './kvStorage'
import type {
  Profile,
  Product,
  ProductWithStock,
  OrderWithItems,
  CreateOrderRequest,
  Order,
  Stock,
  OrderItem,
  SalesProfile,
  Location,
  CreateStockTransferRequest,
  StockTransfer,
  Supplier,
  StockByLocation,
  CreateReturnRequest,
  Return,
  IMEIHistory,
  StockHistory,
  TrainingQueueItem,
  Customer,
  AIProfileConfig,
  Bank,
  FinancingOption,
  WarrantyStatus,
  DashboardStats,
  SalesReport,
  InventoryAlert,
  StockSummaryByLocation,
  SalesSummaryByLocation,
  TopProductByLocationEntry,
  PublicProduct,
  PublicCatalogFilters,
  PaginatedResponse,
  CustomerStats,
  CustomerHistory,
  AIContextPayload,
  AIContextResponse,
  AIReplyPayload,
  AIReplyResponse,
  AIInteractionLogPayload,
  TrainingSubmissionPayload,
  FlagTrollResponse,
  StockHistoryCreateRequest,
  StockHistoryStats,
  BusinessInsightsResponse,
  TradeInPolicy,
  AIStatusResponse,
  Role,
  Permission,
  User,
  CreateUserRequest
} from './types'
import type { SalesForecast } from './aiForecasting'

async function getUseApiSetting(): Promise<boolean> {
  const kv = getKV()
  const useApi = await kv.get<boolean>('settings_use_api')
  return useApi ?? false
}

export interface IInventoryService {
  initializeData(
    profiles: Profile[],
    products: Product[],
    stock: Stock[],
    orders?: Order[],
    orderItems?: OrderItem[]
  ): Promise<void>
  
  fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive?: boolean
  ): Promise<ProductWithStock[]>
  
  getProducts(): Promise<ProductWithStock[]>
  
  createOrder(request: CreateOrderRequest): Promise<OrderWithItems>
  
  fetchOrders(salesProfileSlug?: string): Promise<OrderWithItems[]>
  
  getOrders(): Promise<OrderWithItems[]>
  
  createProfile(profile: Omit<Profile, 'id'>): Promise<Profile>
  
  listProfiles(): Promise<Profile[]>
  
  getProfiles(): Promise<Profile[]>

  listSalesProfiles(): Promise<SalesProfile[]>
  getSalesProfiles(): Promise<SalesProfile[]>
  getSalesProfile(id: number): Promise<SalesProfile>
  createSalesProfile(profile: Omit<SalesProfile, 'id' | 'created_at' | 'updated_at'>): Promise<SalesProfile>
  updateSalesProfile(id: number, updates: Partial<SalesProfile>): Promise<SalesProfile>
  deleteSalesProfile(id: number): Promise<void>

  listLocations(): Promise<Location[]>
  getLocations(): Promise<Location[]>
  getLocation(id: number): Promise<Location>
  createLocation(location: Omit<Location, 'id' | 'created_at' | 'updated_at'>): Promise<Location>
  updateLocation(id: number, updates: Partial<Location>): Promise<Location>
  deleteLocation(id: number): Promise<void>

  updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile>
  
  updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems>

  cancelOrder(orderId: number, reason?: string): Promise<OrderWithItems>

  updateOrder(
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
        es_regalo_promocion?: boolean
        imeis?: string[]
      }>
    }
  ): Promise<OrderWithItems>
  
  addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number,
    locationId?: number
  ): Promise<Product | ProductWithStock>
  
  createProduct(product: Omit<ProductWithStock, 'id'>, locationId?: number): Promise<ProductWithStock>
  
  updateStock(productId: number, cantidad: number, locationId: number): Promise<void>
  updateStockByLocation(productId: number, locationId: number, cantidad: number): Promise<void>
  
  updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock>

  deleteProduct(productId: number): Promise<void>
  deleteOrder(orderId: number): Promise<void>

  createStockTransfer(request: CreateStockTransferRequest): Promise<StockTransfer>
  listStockTransfers(filters?: {
    product_id?: number
    from_location_id?: number
    to_location_id?: number
    location_id?: number
    estado?: 'pendiente' | 'confirmada' | 'rechazada' | 'cancelada'
  }): Promise<StockTransfer[]>
  confirmStockTransfer(id: number, confirmedBy: string, scannedImeis?: string[]): Promise<StockTransfer>
  rejectStockTransfer(id: number, rejectedBy: string, rejectionReason?: string): Promise<StockTransfer>
  cancelStockTransfer(id: number): Promise<void>

  listSuppliers(includeInactive?: boolean): Promise<Supplier[]>
  createSupplier(supplier: Omit<Supplier, 'id' | 'created_at' | 'updated_at'>): Promise<Supplier>
  updateSupplier(id: number, updates: Partial<Supplier>): Promise<Supplier>
  deleteSupplier(id: number): Promise<void>

  getStockByLocation(productId: number): Promise<StockByLocation[]>
  getLocationStock(locationId: number): Promise<StockByLocation[]>
  getLocationStockHistory(locationId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]>
  getProfileStockHistory(profileId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]>
  createStockHistoryEntry(entry: StockHistoryCreateRequest): Promise<StockHistory>
  getProductStockStats(productId: number, days?: number): Promise<StockHistoryStats>
  getPublicCatalog(filters?: PublicCatalogFilters): Promise<PaginatedResponse<PublicProduct>>
  getDashboardStats(params?: { sales_profile_slug?: string; location_id?: number }): Promise<DashboardStats>
  getSalesReport(params?: { sales_profile_slug?: string; date_from?: string; date_to?: string; top_limit?: number }): Promise<SalesReport>
  getInventoryAlerts(params?: { location_id?: number }): Promise<InventoryAlert[]>
  getStockSummaryByLocation(activeOnly?: boolean): Promise<StockSummaryByLocation[]>
  getSalesSummaryByLocation(params?: { start_date?: string; end_date?: string }): Promise<SalesSummaryByLocation[]>
  getTopProductsByLocation(locationId: number, params?: { start_date?: string; end_date?: string; limit?: number }): Promise<TopProductByLocationEntry[]>
  generateBusinessInsights(params?: {
    sales_profile_slug?: string
    sales_profile_id?: number
    location_id?: number
    days?: number
    use_cache?: boolean
    force_refresh?: boolean
  }): Promise<BusinessInsightsResponse>
  getForecasting(): Promise<SalesForecast[]>
  getAIStatus(alertsLimit?: number): Promise<AIStatusResponse>
  
  getAvailableIMEIs(productId: number, locationId: number): Promise<string[]>
  
  getProductByIMEI(imei: string): Promise<ProductWithStock>

  createReturn(returnData: CreateReturnRequest): Promise<Return>
  getReturns(): Promise<Return[]>

  getBanks(activeOnly?: boolean): Promise<Bank[]>
  createBank(bank: Partial<Bank>): Promise<Bank>
  updateBank(id: number, updates: Partial<Bank>): Promise<Bank>
  createFinancingOption(bankId: number, option: Partial<FinancingOption>): Promise<FinancingOption>
  deleteFinancingOption(optionId: number): Promise<void>

  getTradeInPolicies(): Promise<TradeInPolicy[]>
  createTradeInPolicy(policy: Omit<TradeInPolicy, 'id' | 'created_at'>): Promise<TradeInPolicy>
  deleteTradeInPolicy(id: number): Promise<void>

  listUsers(): Promise<User[]>
  createUser(user: CreateUserRequest): Promise<User>
  deleteUser(userId: number): Promise<void>
  updateUserRole(userId: number, roleId: number): Promise<User>
  updateUser(userId: number, updates: Partial<User> & { password?: string; role_id?: number }): Promise<User>
  listRoles(): Promise<Role[]>
  listPermissions(): Promise<Permission[]>

  getIMEIHistory(imei: string): Promise<IMEIHistory[]>
  checkWarrantyStatus(imei: string): Promise<WarrantyStatus>

  // AI & Customer Methods
  listTrainingQueue(status?: string): Promise<TrainingQueueItem[]>
  updateTrainingQueueItem(id: number, updates: Partial<TrainingQueueItem>): Promise<TrainingQueueItem>
  getCustomers(search?: string): Promise<Customer[]>
  updateCustomer(id: number, updates: Partial<Customer>): Promise<Customer>
  listCustomerStats(params?: { sales_profile_slug?: string; page?: number; per_page?: number }): Promise<CustomerStats[]>
  getCustomerStatsByPhone(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerStats>
  getCustomerHistory(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerHistory>
  getAIProfileConfig(salesProfileId: number): Promise<AIProfileConfig | null>
  updateAIProfileConfig(id: number, updates: Partial<AIProfileConfig>): Promise<AIProfileConfig>
  getStockHistory(productId: number, params?: any): Promise<StockHistory[]>
  getAIContext(payload: AIContextPayload): Promise<AIContextResponse>
  generateAIReply(payload: AIReplyPayload): Promise<AIReplyResponse>
  logAIInteraction(payload: AIInteractionLogPayload): Promise<{ status: string }>
  submitAITrainingExample(payload: TrainingSubmissionPayload): Promise<{ status: string }>
  flagCustomerAsTroll(phoneNumber: string, reason: string): Promise<FlagTrollResponse>
  resolveTrainingQueueItem(id: number, action: 'approve' | 'reject' | 'convert_to_faq', correction?: string): Promise<void>
  
  // FAQ Methods
  listFAQs(params?: any): Promise<{ items: import('./types').FAQEntry[], total: number, pages: number }>
  createFAQ(faq: any): Promise<import('./types').FAQEntry>
  updateFAQ(id: number, updates: any): Promise<import('./types').FAQEntry>
  deleteFAQ(id: number): Promise<void>

  linkOrderToInteraction(customerPhone: string, orderId: number): Promise<void>
}

class LocalServiceWrapper implements IInventoryService {
  private service = localService

  async initializeData(
    profiles: Profile[],
    products: Product[],
    stock: Stock[],
    orders?: Order[],
    orderItems?: OrderItem[]
  ): Promise<void> {
    return this.service.initializeData(profiles, products, stock, orders, orderItems)
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive?: boolean
  ): Promise<ProductWithStock[]> {
    return this.service.fetchProducts(profileSlug, search, includeInactive)
  }

  async getProducts(): Promise<ProductWithStock[]> {
    return this.service.getProducts()
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    return this.service.createOrder(request)
  }

  async fetchOrders(salesProfileSlug?: string): Promise<OrderWithItems[]> {
    return this.service.fetchOrders(salesProfileSlug)
  }

  async getOrders(): Promise<OrderWithItems[]> {
    return this.service.getOrders()
  }

  async createProfile(profile: Omit<Profile, 'id'>): Promise<Profile> {
    return this.service.createProfile(profile.name, profile.slug)
  }

  async listProfiles(): Promise<Profile[]> {
    return this.service.listProfiles()
  }

  async getProfiles(): Promise<Profile[]> {
    return this.service.getProfiles()
  }

  async listSalesProfiles(): Promise<SalesProfile[]> {
    return this.service.getSalesProfiles()
  }

  async getSalesProfiles(): Promise<SalesProfile[]> {
    return this.service.getSalesProfiles()
  }

  async getSalesProfile(id: number): Promise<SalesProfile> {
    return this.service.getSalesProfile(id)
  }

  async createSalesProfile(profile: Omit<SalesProfile, 'id' | 'created_at' | 'updated_at'>): Promise<SalesProfile> {
    return this.service.createSalesProfile(profile)
  }

  async updateSalesProfile(id: number, updates: Partial<SalesProfile>): Promise<SalesProfile> {
    return this.service.updateSalesProfile(id, updates)
  }

  async deleteSalesProfile(id: number): Promise<void> {
    return this.service.deleteSalesProfile(id)
  }

  async listLocations(): Promise<Location[]> {
    return this.service.getLocations()
  }

  async getLocations(): Promise<Location[]> {
    return this.service.getLocations()
  }

  async getLocation(id: number): Promise<Location> {
    return this.service.getLocation(id)
  }

  async createLocation(location: Omit<Location, 'id' | 'created_at' | 'updated_at'>): Promise<Location> {
    return this.service.createLocation(location)
  }

  async updateLocation(id: number, updates: Partial<Location>): Promise<Location> {
    return this.service.updateLocation(id, updates)
  }

  async deleteLocation(id: number): Promise<void> {
    return this.service.deleteLocation(id)
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    return this.service.updateProfile(profileId, updates)
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    return this.service.updateOrderStatus(orderId, estado)
  }

  async cancelOrder(orderId: number, reason?: string): Promise<OrderWithItems> {
    return this.service.cancelOrder(orderId, reason)
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
        es_regalo_promocion?: boolean
        imeis?: string[]
      }>
    }
  ): Promise<OrderWithItems> {
    return this.service.updateOrder(orderId, updates)
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number,
    locationId?: number
  ): Promise<ProductWithStock> {
    return this.service.addProduct(product, initialStock, locationId)
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>, locationId?: number): Promise<ProductWithStock> {
    return this.service.createProduct(product, locationId)
  }

  async updateStock(productId: number, cantidad: number, locationId: number): Promise<void> {
    return this.service.updateStock(productId, cantidad, locationId)
  }

  async updateStockByLocation(productId: number, locationId: number, cantidad: number): Promise<void> {
    return this.service.updateStockByLocation(productId, locationId, cantidad)
  }

  async updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock> {
    return this.service.updateProduct(productId, updates)
  }
  async deleteProduct(productId: number): Promise<void> {
    return this.service.deleteProduct(productId)
  }
  async deleteOrder(orderId: number): Promise<void> {
    return this.service.deleteOrder(orderId)
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[], locationId?: number): Promise<ProductWithStock[]> {
    return this.service.bulkCreateProducts(productsData, locationId)
  }

  async createStockTransfer(request: CreateStockTransferRequest): Promise<StockTransfer> {
    return this.service.createStockTransfer(request)
  }

  async listStockTransfers(filters?: any): Promise<StockTransfer[]> {
    return this.service.listStockTransfers(filters)
  }

  async confirmStockTransfer(id: number, confirmedBy: string, scannedImeis?: string[]): Promise<StockTransfer> {
    return this.service.confirmStockTransfer(id, confirmedBy, scannedImeis)
  }

  async rejectStockTransfer(id: number, rejectedBy: string, rejectionReason?: string): Promise<StockTransfer> {
    return this.service.rejectStockTransfer(id, rejectedBy, rejectionReason)
  }

  async cancelStockTransfer(id: number): Promise<void> {
    return this.service.cancelStockTransfer(id)
  }

  async listSuppliers(includeInactive?: boolean): Promise<Supplier[]> {
    return this.service.listSuppliers(includeInactive)
  }

  async createSupplier(supplier: Omit<Supplier, 'id' | 'created_at' | 'updated_at'>): Promise<Supplier> {
    return this.service.createSupplier(supplier)
  }

  async updateSupplier(id: number, updates: Partial<Supplier>): Promise<Supplier> {
    return this.service.updateSupplier(id, updates)
  }

  async deleteSupplier(id: number): Promise<void> {
    return this.service.deleteSupplier(id)
  }

  async getStockByLocation(productId: number): Promise<StockByLocation[]> {
    return this.service.getStockByLocation(productId)
  }

  async getLocationStock(locationId: number): Promise<StockByLocation[]> {
    return this.service.getLocationStock(locationId)
  }

  async getDashboardStats(params?: { sales_profile_slug?: string; location_id?: number }): Promise<DashboardStats> {
    return this.service.getDashboardStats(params)
  }

  async getSalesReport(params?: { sales_profile_slug?: string; date_from?: string; date_to?: string; top_limit?: number }): Promise<SalesReport> {
    return this.service.getSalesReport(params)
  }

  async getInventoryAlerts(params?: { location_id?: number }): Promise<InventoryAlert[]> {
    return this.service.getInventoryAlerts(params)
  }

  async getStockSummaryByLocation(activeOnly?: boolean): Promise<StockSummaryByLocation[]> {
    return this.service.getStockSummaryByLocation(activeOnly)
  }

  async getSalesSummaryByLocation(params?: { start_date?: string; end_date?: string }): Promise<SalesSummaryByLocation[]> {
    return this.service.getSalesSummaryByLocation(params)
  }

  async getTopProductsByLocation(locationId: number, params?: { start_date?: string; end_date?: string; limit?: number }): Promise<TopProductByLocationEntry[]> {
    return this.service.getTopProductsByLocation(locationId, params)
  }

  async generateBusinessInsights(params?: {
    sales_profile_slug?: string
    sales_profile_id?: number
    location_id?: number
    days?: number
    use_cache?: boolean
    force_refresh?: boolean
  }): Promise<BusinessInsightsResponse> {
    return this.service.generateBusinessInsights(params)
  }

  async getForecasting(): Promise<SalesForecast[]> {
    return this.service.getForecasting()
  }

  async getAIStatus(alertsLimit = 5): Promise<AIStatusResponse> {
    return this.service.getAIStatus(alertsLimit)
  }

  async getPublicCatalog(filters?: PublicCatalogFilters): Promise<PaginatedResponse<PublicProduct>> {
    return this.service.getPublicCatalog(filters)
  }
  async getAvailableIMEIs(productId: number, locationId: number): Promise<string[]> {
    return this.service.getAvailableIMEIs(productId, locationId)
  }

  async createReturn(returnData: CreateReturnRequest): Promise<Return> {
    return this.service.createReturn(returnData)
  }

  async getReturns(): Promise<Return[]> {
    return this.service.getReturns()
  }

  async getBanks(activeOnly?: boolean): Promise<Bank[]> {
    return this.service.getBanks(activeOnly ?? true)
  }

  async createBank(bank: Partial<Bank>): Promise<Bank> {
    return this.service.createBank(bank)
  }

  async updateBank(id: number, updates: Partial<Bank>): Promise<Bank> {
    return this.service.updateBank(id, updates)
  }

  async createFinancingOption(bankId: number, option: Partial<FinancingOption>): Promise<FinancingOption> {
    return this.service.createFinancingOption(bankId, option)
  }

  async deleteFinancingOption(optionId: number): Promise<void> {
    return this.service.deleteFinancingOption(optionId)
  }

  async getTradeInPolicies(): Promise<TradeInPolicy[]> {
    return this.service.getTradeInPolicies()
  }

  async createTradeInPolicy(policy: Omit<TradeInPolicy, 'id' | 'created_at'>): Promise<TradeInPolicy> {
    return this.service.createTradeInPolicy(policy)
  }

  async deleteTradeInPolicy(id: number): Promise<void> {
    return this.service.deleteTradeInPolicy(id)
  }

  async listUsers(): Promise<User[]> {
    return this.service.listUsers()
  }

  async createUser(user: CreateUserRequest): Promise<User> {
    return this.service.createUser(user)
  }

  async deleteUser(userId: number): Promise<void> {
    return this.service.deleteUser(userId)
  }

  async updateUserRole(userId: number, roleId: number): Promise<User> {
    return this.service.updateUserRole(userId, roleId)
  }

  async updateUser(userId: number, updates: Partial<User> & { password?: string; role_id?: number }): Promise<User> {
    return this.service.updateUser(userId, updates)
  }

  async listRoles(): Promise<Role[]> {
    return this.service.listRoles()
  }

  async listPermissions(): Promise<Permission[]> {
    return this.service.listPermissions()
  }

  async getIMEIHistory(imei: string): Promise<IMEIHistory[]> {
    return this.service.getIMEIHistory(imei)
  }

  async checkWarrantyStatus(imei: string): Promise<WarrantyStatus> {
    return this.service.checkWarrantyStatus(imei)
  }

  async listTrainingQueue(status?: string): Promise<TrainingQueueItem[]> {
    return this.service.listTrainingQueue(status)
  }

  async updateTrainingQueueItem(id: number, updates: Partial<TrainingQueueItem>): Promise<TrainingQueueItem> {
    return this.service.updateTrainingQueueItem(id, updates)
  }

  async getCustomers(search?: string): Promise<Customer[]> {
    return this.service.getCustomers(search)
  }

  async updateCustomer(id: number, updates: Partial<Customer>): Promise<Customer> {
    return this.service.updateCustomer(id, updates)
  }

  async resolveTrainingQueueItem(id: number, action: 'approve' | 'reject' | 'convert_to_faq', correction?: string): Promise<void> {
    return this.service.resolveTrainingQueueItem(id, action, correction)
  }

  async listCustomerStats(params?: { sales_profile_slug?: string; page?: number; per_page?: number }): Promise<CustomerStats[]> {
    return this.service.listCustomerStats(params)
  }

  async getCustomerStatsByPhone(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerStats> {
    return this.service.getCustomerStatsByPhone(customerPhone, params)
  }

  async getCustomerHistory(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerHistory> {
    return this.service.getCustomerHistory(customerPhone, params)
  }

  async getAIProfileConfig(salesProfileId: number): Promise<AIProfileConfig | null> {
    return this.service.getAIProfileConfig(salesProfileId)
  }

  async updateAIProfileConfig(id: number, updates: Partial<AIProfileConfig>): Promise<AIProfileConfig> {
    return this.service.updateAIProfileConfig(id, updates)
  }

  async getAIContext(payload: AIContextPayload): Promise<AIContextResponse> {
    return this.service.getAIContext(payload)
  }

  async generateAIReply(payload: AIReplyPayload): Promise<AIReplyResponse> {
    return this.service.generateAIReply(payload)
  }

  async logAIInteraction(payload: AIInteractionLogPayload): Promise<{ status: string }> {
    return this.service.logAIInteraction(payload)
  }

  async submitAITrainingExample(payload: TrainingSubmissionPayload): Promise<{ status: string }> {
    return this.service.submitAITrainingExample(payload)
  }

  async flagCustomerAsTroll(phoneNumber: string, reason: string): Promise<FlagTrollResponse> {
    return this.service.flagCustomerAsTroll(phoneNumber, reason)
  }

  async getStockHistory(productId: number, params?: any): Promise<StockHistory[]> {
    return this.service.getStockHistory(productId, params)
  }

  async getLocationStockHistory(locationId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]> {
    return this.service.getLocationStockHistory(locationId, params)
  }

  async getProfileStockHistory(profileId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]> {
    return this.service.getProfileStockHistory(profileId, params)
  }

  async createStockHistoryEntry(entry: StockHistoryCreateRequest): Promise<StockHistory> {
    return this.service.createStockHistoryEntry(entry)
  }

  async getProductStockStats(productId: number, days?: number): Promise<StockHistoryStats> {
    return this.service.getProductStockStats(productId, days)
  }

  async listFAQs(params?: any): Promise<{ items: import('./types').FAQEntry[], total: number, pages: number }> {
    return this.service.listFAQs(params)
  }

  async createFAQ(faq: any): Promise<import('./types').FAQEntry> {
    return this.service.createFAQ(faq)
  }

  async updateFAQ(id: number, updates: any): Promise<import('./types').FAQEntry> {
    return this.service.updateFAQ(id, updates)
  }

  async deleteFAQ(id: number): Promise<void> {
    return this.service.deleteFAQ(id)
  }

  async linkOrderToInteraction(_customerPhone: string, _orderId: number): Promise<void> {
    // No-op in local mode
    return
  }
}

class UnifiedInventoryService implements IInventoryService {
  private async getService(): Promise<IInventoryService> {
    try {
      const useApi = await getUseApiSetting()
      return useApi ? new ApiInventoryService() : new LocalServiceWrapper()
    } catch (error) {
      console.error('Error determining service type:', error)
      return new LocalServiceWrapper()
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
      const service = await this.getService()
      return service.initializeData(profiles, products, stock, orders, orderItems)
    } catch (error) {
      console.error('Error initializing data (unified):', error)
      throw new Error(`Failed to initialize data: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive = false
  ): Promise<ProductWithStock[]> {
    try {
      const service = await this.getService()
      return service.fetchProducts(profileSlug, search, includeInactive)
    } catch (error) {
      console.error('Error fetching products (unified):', error)
      throw new Error(`Failed to fetch products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getProducts(): Promise<ProductWithStock[]> {
    try {
      return this.fetchProducts(undefined, undefined, true)
    } catch (error) {
      console.error('Error getting products (unified):', error)
      throw new Error(`Failed to get products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    try {
      const service = await this.getService()
      return service.createOrder(request)
    } catch (error) {
      console.error('Error creating order (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to create order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async fetchOrders(salesProfileSlug?: string): Promise<OrderWithItems[]> {
    try {
      const service = await this.getService()
      return service.fetchOrders(salesProfileSlug)
    } catch (error) {
      console.error('Error fetching orders (unified):', error)
      throw new Error(`Failed to fetch orders: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getOrders(): Promise<OrderWithItems[]> {
    try {
      return this.fetchOrders()
    } catch (error) {
      console.error('Error getting orders (unified):', error)
      throw new Error(`Failed to get orders: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createProfile(profile: Omit<Profile, 'id'>): Promise<Profile> {
    try {
      const service = await this.getService()
      return service.createProfile(profile)
    } catch (error) {
      console.error('Error creating profile (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to create profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listProfiles(): Promise<Profile[]> {
    try {
      const service = await this.getService()
      return service.listProfiles()
    } catch (error) {
      console.error('Error listing profiles (unified):', error)
      throw new Error(`Failed to list profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getProfiles(): Promise<Profile[]> {
    try {
      return this.listProfiles()
    } catch (error) {
      console.error('Error getting profiles (unified):', error)
      throw new Error(`Failed to get profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listSalesProfiles(): Promise<SalesProfile[]> {
    try {
      const service = await this.getService()
      return service.listSalesProfiles ? service.listSalesProfiles() : []
    } catch (error) {
      console.error('Error listing sales profiles (unified):', error)
      throw new Error(`Failed to list sales profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getSalesProfiles(): Promise<SalesProfile[]> {
    try {
      return this.listSalesProfiles()
    } catch (error) {
      console.error('Error getting sales profiles (unified):', error)
      throw new Error(`Failed to get sales profiles: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getSalesProfile(id: number): Promise<SalesProfile> {
    try {
      const service = await this.getService()
      return service.getSalesProfile(id)
    } catch (error) {
      console.error('Error getting sales profile (unified):', error)
      throw new Error(`Failed to get sales profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createSalesProfile(profile: Omit<SalesProfile, 'id' | 'created_at' | 'updated_at'>): Promise<SalesProfile> {
    try {
      const service = await this.getService()
      return service.createSalesProfile(profile)
    } catch (error) {
      console.error('Error creating sales profile (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to create sales profile: ${error}`)
    }
  }

  async updateSalesProfile(id: number, updates: Partial<SalesProfile>): Promise<SalesProfile> {
    try {
      const service = await this.getService()
      return service.updateSalesProfile(id, updates)
    } catch (error) {
      console.error('Error updating sales profile (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update sales profile: ${error}`)
    }
  }

  async deleteSalesProfile(id: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.deleteSalesProfile(id)
    } catch (error) {
      console.error('Error deleting sales profile (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to delete sales profile: ${error}`)
    }
  }

  async listLocations(): Promise<Location[]> {
    try {
      const service = await this.getService()
      return service.listLocations()
    } catch (error) {
      console.error('Error listing locations (unified):', error)
      throw new Error(`Failed to list locations: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getLocations(): Promise<Location[]> {
    try {
      return this.listLocations()
    } catch (error) {
      console.error('Error getting locations (unified):', error)
      throw new Error(`Failed to get locations: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getLocation(id: number): Promise<Location> {
    try {
      const service = await this.getService()
      return service.getLocation(id)
    } catch (error) {
      console.error('Error getting location (unified):', error)
      throw new Error(`Failed to get location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createLocation(location: Omit<Location, 'id' | 'created_at' | 'updated_at'>): Promise<Location> {
    try {
      const service = await this.getService()
      return service.createLocation(location)
    } catch (error) {
      console.error('Error creating location (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to create location: ${error}`)
    }
  }

  async updateLocation(id: number, updates: Partial<Location>): Promise<Location> {
    try {
      const service = await this.getService()
      return service.updateLocation(id, updates)
    } catch (error) {
      console.error('Error updating location (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update location: ${error}`)
    }
  }

  async deleteLocation(id: number): Promise<void> {
    try {
      const service = await this.getService()
      if (!service.deleteLocation) throw new Error('Locations no disponibles en este modo')
      return service.deleteLocation(id)
    } catch (error) {
      console.error('Error deleting location (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to delete location: ${error}`)
    }
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    try {
      const service = await this.getService()
      return service.updateProfile(profileId, updates)
    } catch (error) {
      console.error('Error updating profile (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update profile: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    try {
      const service = await this.getService()
      return service.updateOrderStatus(orderId, estado)
    } catch (error) {
      console.error('Error updating order status (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update order status: ${error instanceof Error ? error.message : 'Unknown error'}`)
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
        es_regalo_promocion?: boolean
        imeis?: string[]
      }>
    }
  ): Promise<OrderWithItems> {
    try {
      const service = await this.getService()
      return service.updateOrder(orderId, updates)
    } catch (error) {
      console.error('Error updating order (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number,
    locationId?: number
  ): Promise<ProductWithStock> {
    try {
      const service = await this.getService()
      return service.addProduct(product, initialStock, locationId) as Promise<ProductWithStock>
    } catch (error) {
      console.error('Error adding product (unified):', error)
      throw new Error(`Failed to add product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>, locationId?: number): Promise<ProductWithStock> {
    try {
      // V2.0: locationId se pasa al servicio apropiado
      const service = await this.getService()
      return service.createProduct(product, locationId)
    } catch (error) {
      console.error('Error creating product (unified):', error)
      throw new Error(`Failed to create product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateStock(productId: number, cantidad: number, locationId: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.updateStock(productId, cantidad, locationId)
    } catch (error) {
      console.error('Error updating stock (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateStockByLocation(productId: number, locationId: number, cantidad: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.updateStockByLocation(productId, locationId, cantidad)
    } catch (error) {
      console.error('Error updating stock by location (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update stock by location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock> {
    try {
      const service = await this.getService()
      return service.updateProduct(productId, updates)
    } catch (error) {
      console.error('Error updating product (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to update product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteProduct(productId: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.deleteProduct(productId)
    } catch (error) {
      console.error('Error deleting product (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to delete product: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteOrder(orderId: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.deleteOrder(orderId)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      if (!message.includes('completada') && !message.includes('cancelar')) {
          console.error('Error deleting order (unified):', error)
      }
      throw error instanceof Error ? error : new Error(`Failed to delete order: ${message}`)
    }
  }

  async cancelOrder(orderId: number, reason?: string): Promise<OrderWithItems> {
    try {
      const useApi = await getUseApiSetting()
      if (useApi) {
        return apiClient.cancelOrder(orderId, reason)
      } else {
        const service = await this.getService()
        return service.cancelOrder(orderId, reason)
      }
    } catch (error) {
      console.error('Error cancelling order (unified):', error)
      throw error instanceof Error ? error : new Error(`Failed to cancel order: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[], locationId?: number): Promise<ProductWithStock[]> {
    try {
      const service = await this.getService()
      return service.bulkCreateProducts(productsData, locationId)
    } catch (error) {
      console.error('Error bulk creating products (unified):', error)
      throw new Error(`Failed to bulk create products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createStockTransfer(request: CreateStockTransferRequest): Promise<StockTransfer> {
    try {
      const service = await this.getService()
      return service.createStockTransfer(request)
    } catch (error) {
      console.error('Error creating stock transfer (unified):', error)
      throw new Error(`Failed to create stock transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listStockTransfers(filters?: any): Promise<StockTransfer[]> {
    try {
      const service = await this.getService()
      return service.listStockTransfers(filters)
    } catch (error) {
      console.error('Error listing stock transfers (unified):', error)
      throw new Error(`Failed to list stock transfers: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async confirmStockTransfer(id: number, confirmedBy: string, scannedImeis?: string[]): Promise<StockTransfer> {
    try {
      const service = await this.getService()
      return service.confirmStockTransfer(id, confirmedBy, scannedImeis)
    } catch (error) {
      console.error('Error confirming stock transfer (unified):', error)
      throw new Error(`Failed to confirm stock transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async rejectStockTransfer(id: number, rejectedBy: string, rejectionReason?: string): Promise<StockTransfer> {
    try {
      const service = await this.getService()
      return service.rejectStockTransfer(id, rejectedBy, rejectionReason)
    } catch (error) {
      console.error('Error rejecting stock transfer (unified):', error)
      throw new Error(`Failed to reject stock transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async cancelStockTransfer(id: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.cancelStockTransfer(id)
    } catch (error) {
      console.error('Error canceling stock transfer (unified):', error)
      throw new Error(`Failed to cancel stock transfer: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listSuppliers(includeInactive?: boolean): Promise<Supplier[]> {
    try {
      const service = await this.getService()
      return service.listSuppliers(includeInactive)
    } catch (error) {
      console.error('Error listing suppliers (unified):', error)
      throw new Error(`Failed to list suppliers: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createSupplier(supplier: Omit<Supplier, 'id' | 'created_at' | 'updated_at'>): Promise<Supplier> {
    try {
      const service = await this.getService()
      return service.createSupplier(supplier)
    } catch (error) {
      console.error('Error creating supplier (unified):', error)
      throw new Error(`Failed to create supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateSupplier(id: number, updates: Partial<Supplier>): Promise<Supplier> {
    try {
      const service = await this.getService()
      return service.updateSupplier(id, updates)
    } catch (error) {
      console.error('Error updating supplier (unified):', error)
      throw new Error(`Failed to update supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteSupplier(id: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.deleteSupplier(id)
    } catch (error) {
      console.error('Error deleting supplier (unified):', error)
      throw new Error(`Failed to delete supplier: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getStockByLocation(productId: number): Promise<StockByLocation[]> {
    try {
      const service = await this.getService()
      return service.getStockByLocation(productId)
    } catch (error) {
      console.error('Error getting stock by location (unified):', error)
      throw new Error(`Failed to get stock by location: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getLocationStock(locationId: number): Promise<StockByLocation[]> {
    try {
      const service = await this.getService()
      return service.getLocationStock(locationId)
    } catch (error) {
      console.error('Error getting location stock (unified):', error)
      throw new Error(`Failed to get location stock: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getDashboardStats(params?: { sales_profile_slug?: string; location_id?: number }): Promise<DashboardStats> {
    try {
      const service = await this.getService()
      return service.getDashboardStats(params)
    } catch (error) {
      console.error('Error getting dashboard stats (unified):', error)
      throw new Error(`Failed to get dashboard stats: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getSalesReport(params?: { sales_profile_slug?: string; date_from?: string; date_to?: string; top_limit?: number }): Promise<SalesReport> {
    try {
      const service = await this.getService()
      return service.getSalesReport(params)
    } catch (error) {
      console.error('Error getting sales report (unified):', error)
      throw new Error(`Failed to get sales report: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getInventoryAlerts(params?: { location_id?: number }): Promise<InventoryAlert[]> {
    try {
      const service = await this.getService()
      return service.getInventoryAlerts(params)
    } catch (error) {
      console.error('Error getting inventory alerts (unified):', error)
      throw new Error(`Failed to get inventory alerts: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getStockSummaryByLocation(activeOnly?: boolean): Promise<StockSummaryByLocation[]> {
    try {
      const service = await this.getService()
      return service.getStockSummaryByLocation(activeOnly)
    } catch (error) {
      console.error('Error getting stock summary by location (unified):', error)
      throw new Error(`Failed to get stock summary: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getSalesSummaryByLocation(params?: { start_date?: string; end_date?: string }): Promise<SalesSummaryByLocation[]> {
    try {
      const service = await this.getService()
      return service.getSalesSummaryByLocation(params)
    } catch (error) {
      console.error('Error getting sales summary by location (unified):', error)
      throw new Error(`Failed to get sales summary: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getTopProductsByLocation(locationId: number, params?: { start_date?: string; end_date?: string; limit?: number }): Promise<TopProductByLocationEntry[]> {
    try {
      const service = await this.getService()
      return service.getTopProductsByLocation(locationId, params)
    } catch (error) {
      console.error('Error getting top products by location (unified):', error)
      throw new Error(`Failed to get top products: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async generateBusinessInsights(params?: {
    sales_profile_slug?: string
    sales_profile_id?: number
    location_id?: number
    days?: number
    use_cache?: boolean
    force_refresh?: boolean
  }): Promise<BusinessInsightsResponse> {
    try {
      const service = await this.getService()
      return service.generateBusinessInsights(params)
    } catch (error) {
      console.error('Error generating business insights (unified):', error)
      throw new Error(`Failed to generate business insights: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getForecasting(): Promise<SalesForecast[]> {
    try {
      const service = await this.getService()
      return service.getForecasting()
    } catch (error) {
      console.error('Error getting forecasting (unified):', error)
      throw new Error(`Failed to get forecasting: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getAIStatus(alertsLimit = 5): Promise<AIStatusResponse> {
    try {
      const service = await this.getService()
      return service.getAIStatus(alertsLimit)
    } catch (error) {
      console.error('Error getting AI status (unified):', error)
      throw new Error(`Failed to get AI status: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getPublicCatalog(filters?: PublicCatalogFilters): Promise<PaginatedResponse<PublicProduct>> {
    try {
      const service = await this.getService()
      return service.getPublicCatalog(filters)
    } catch (error) {
      console.error('Error getting public catalog (unified):', error)
      throw new Error(`Failed to get public catalog: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getAvailableIMEIs(productId: number, locationId: number): Promise<string[]> {
    try {
      const service = await this.getService()
      return service.getAvailableIMEIs(productId, locationId)
    } catch (error) {
      console.error('Error getting available IMEIs (unified):', error)
      throw new Error(`Failed to get available IMEIs: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createReturn(returnData: CreateReturnRequest): Promise<Return> {
    try {
      const service = await this.getService()
      return service.createReturn(returnData)
    } catch (error) {
      console.error('Error creating return (unified):', error)
      throw new Error(`Failed to create return: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getReturns(): Promise<Return[]> {
    try {
      const service = await this.getService()
      return service.getReturns()
    } catch (error) {
      console.error('Error getting returns (unified):', error)
      throw new Error(`Failed to get returns: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getBanks(activeOnly?: boolean): Promise<Bank[]> {
    try {
      const service = await this.getService()
      return service.getBanks(activeOnly)
    } catch (error) {
      console.error('Error getting banks (unified):', error)
      throw new Error(`Failed to get banks: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createBank(bank: Partial<Bank>): Promise<Bank> {
    try {
      const service = await this.getService()
      return service.createBank(bank)
    } catch (error) {
      console.error('Error creating bank (unified):', error)
      throw new Error(`Failed to create bank: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async updateBank(id: number, updates: Partial<Bank>): Promise<Bank> {
    try {
      const service = await this.getService()
      return service.updateBank(id, updates)
    } catch (error) {
      console.error('Error updating bank (unified):', error)
      throw new Error(`Failed to update bank: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createFinancingOption(bankId: number, option: Partial<FinancingOption>): Promise<FinancingOption> {
    try {
      const service = await this.getService()
      return service.createFinancingOption(bankId, option)
    } catch (error) {
      console.error('Error creating financing option (unified):', error)
      throw new Error(`Failed to create financing option: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteFinancingOption(optionId: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.deleteFinancingOption(optionId)
    } catch (error) {
      console.error('Error deleting financing option (unified):', error)
      throw new Error(`Failed to delete financing option: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async getTradeInPolicies(): Promise<TradeInPolicy[]> {
    try {
      const service = await this.getService()
      return service.getTradeInPolicies()
    } catch (error) {
      console.error('Error getting trade-in policies (unified):', error)
      throw new Error(`Failed to get trade-in policies: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async createTradeInPolicy(policy: Omit<TradeInPolicy, 'id' | 'created_at'>): Promise<TradeInPolicy> {
    try {
      const service = await this.getService()
      return service.createTradeInPolicy(policy)
    } catch (error) {
      console.error('Error creating trade-in policy (unified):', error)
      throw new Error(`Failed to create trade-in policy: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async deleteTradeInPolicy(id: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.deleteTradeInPolicy(id)
    } catch (error) {
      console.error('Error deleting trade-in policy (unified):', error)
      throw new Error(`Failed to delete trade-in policy: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listUsers(): Promise<User[]> {
    try {
      const service = await this.getService()
      return service.listUsers()
    } catch (error) {
      console.error('Error listing users (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to list users')
    }
  }

  async createUser(user: CreateUserRequest): Promise<User> {
    try {
      const service = await this.getService()
      return service.createUser(user)
    } catch (error) {
      console.error('Error creating user (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to create user')
    }
  }

  async deleteUser(userId: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.deleteUser(userId)
    } catch (error) {
      console.error('Error deleting user (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to delete user')
    }
  }

  async updateUserRole(userId: number, roleId: number): Promise<User> {
    try {
      const service = await this.getService()
      return service.updateUserRole(userId, roleId)
    } catch (error) {
      console.error('Error updating user role (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to update user role')
    }
  }

  async updateUser(userId: number, updates: Partial<User> & { password?: string; role_id?: number }): Promise<User> {
    try {
      const service = await this.getService()
      return service.updateUser(userId, updates)
    } catch (error) {
      console.error('Error updating user (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to update user')
    }
  }

  async listRoles(): Promise<Role[]> {
    try {
      const service = await this.getService()
      return service.listRoles()
    } catch (error) {
      console.error('Error listing roles (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to list roles')
    }
  }

  async listPermissions(): Promise<Permission[]> {
    try {
      const service = await this.getService()
      return service.listPermissions()
    } catch (error) {
      console.error('Error listing permissions (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to list permissions')
    }
  }

  async getIMEIHistory(imei: string): Promise<IMEIHistory[]> {
    try {
      const service = await this.getService()
      return service.getIMEIHistory(imei)
    } catch (error) {
      console.error('Error getting IMEI history (unified):', error)
      throw new Error(`Failed to get IMEI history: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async checkWarrantyStatus(imei: string): Promise<WarrantyStatus> {
    try {
      const service = await this.getService()
      return service.checkWarrantyStatus(imei)
    } catch (error) {
      console.error('Error checking warranty status (unified):', error)
      throw new Error(`Failed to check warranty status: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async listTrainingQueue(status?: string): Promise<TrainingQueueItem[]> {
    try {
      const service = await this.getService()
      return service.listTrainingQueue(status)
    } catch (error) {
      console.error('Error listing training queue (unified):', error)
      return []
    }
  }

  async updateTrainingQueueItem(id: number, updates: Partial<TrainingQueueItem>): Promise<TrainingQueueItem> {
    try {
      const service = await this.getService()
      return service.updateTrainingQueueItem(id, updates)
    } catch (error) {
      console.error('Error updating training queue item (unified):', error)
      throw error
    }
  }

  async resolveTrainingQueueItem(id: number, action: 'approve' | 'reject' | 'convert_to_faq', correction?: string): Promise<void> {
    try {
      const service = await this.getService()
      await service.resolveTrainingQueueItem(id, action, correction)
    } catch (error) {
      console.error('Error resolving training queue item (unified):', error)
      throw error
    }
  }

  async getCustomers(search?: string): Promise<Customer[]> {
    try {
      const service = await this.getService()
      return service.getCustomers(search)
    } catch (error) {
      console.error('Error getting customers (unified):', error)
      return []
    }
  }

  async updateCustomer(id: number, updates: Partial<Customer>): Promise<Customer> {
    try {
      const service = await this.getService()
      return service.updateCustomer(id, updates)
    } catch (error) {
      console.error('Error updating customer (unified):', error)
      throw error
    }
  }

  async listCustomerStats(params?: { sales_profile_slug?: string; page?: number; per_page?: number }): Promise<CustomerStats[]> {
    try {
      const service = await this.getService()
      return service.listCustomerStats(params)
    } catch (error) {
      console.error('Error listing customer stats (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to list customer stats')
    }
  }

  async getCustomerStatsByPhone(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerStats> {
    try {
      const service = await this.getService()
      return service.getCustomerStatsByPhone(customerPhone, params)
    } catch (error) {
      console.error('Error getting customer stats (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to get customer stats')
    }
  }

  async getCustomerHistory(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerHistory> {
    try {
      const service = await this.getService()
      return service.getCustomerHistory(customerPhone, params)
    } catch (error) {
      console.error('Error getting customer history (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to get customer history')
    }
  }

  async getAIProfileConfig(salesProfileId: number): Promise<AIProfileConfig | null> {
    try {
      const service = await this.getService()
      return service.getAIProfileConfig(salesProfileId)
    } catch (error) {
      console.error('Error getting AI config (unified):', error)
      return null
    }
  }

  async updateAIProfileConfig(id: number, updates: Partial<AIProfileConfig>): Promise<AIProfileConfig> {
    try {
      const service = await this.getService()
      return service.updateAIProfileConfig(id, updates)
    } catch (error) {
      console.error('Error updating AI config (unified):', error)
      throw error
    }
  }

  async getAIContext(payload: AIContextPayload): Promise<AIContextResponse> {
    try {
      const service = await this.getService()
      return service.getAIContext(payload)
    } catch (error) {
      console.error('Error getting AI context (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to get AI context')
    }
  }

  async generateAIReply(payload: AIReplyPayload): Promise<AIReplyResponse> {
    try {
      const service = await this.getService()
      return service.generateAIReply(payload)
    } catch (error) {
      console.error('Error generating AI reply (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to generate AI reply')
    }
  }

  async logAIInteraction(payload: AIInteractionLogPayload): Promise<{ status: string }> {
    try {
      const service = await this.getService()
      return service.logAIInteraction(payload)
    } catch (error) {
      console.error('Error logging AI interaction (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to log AI interaction')
    }
  }

  async submitAITrainingExample(payload: TrainingSubmissionPayload): Promise<{ status: string }> {
    try {
      const service = await this.getService()
      return service.submitAITrainingExample(payload)
    } catch (error) {
      console.error('Error submitting AI training example (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to submit AI training example')
    }
  }

  async flagCustomerAsTroll(phoneNumber: string, reason: string): Promise<FlagTrollResponse> {
    try {
      const service = await this.getService()
      return service.flagCustomerAsTroll(phoneNumber, reason)
    } catch (error) {
      console.error('Error flagging customer as troll (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to flag customer as troll')
    }
  }

  async getStockHistory(productId: number, params?: any): Promise<StockHistory[]> {
    try {
      const service = await this.getService()
      return service.getStockHistory(productId, params)
    } catch (error) {
      console.error('Error getting stock history (unified):', error)
      return []
    }
  }

  async getLocationStockHistory(locationId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]> {
    try {
      const service = await this.getService()
      return service.getLocationStockHistory(locationId, params)
    } catch (error) {
      console.error('Error getting location stock history (unified):', error)
      return []
    }
  }

  async getProfileStockHistory(profileId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]> {
    try {
      const service = await this.getService()
      return service.getProfileStockHistory(profileId, params)
    } catch (error) {
      console.error('Error getting profile stock history (unified):', error)
      return []
    }
  }

  async createStockHistoryEntry(entry: StockHistoryCreateRequest): Promise<StockHistory> {
    try {
      const service = await this.getService()
      return service.createStockHistoryEntry(entry)
    } catch (error) {
      console.error('Error creating stock history entry (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to create stock history entry')
    }
  }

  async getProductStockStats(productId: number, days?: number): Promise<StockHistoryStats> {
    try {
      const service = await this.getService()
      return service.getProductStockStats(productId, days)
    } catch (error) {
      console.error('Error getting product stock stats (unified):', error)
      throw error instanceof Error ? error : new Error('Failed to get product stock stats')
    }
  }

  async listFAQs(params?: any): Promise<{ items: import('./types').FAQEntry[], total: number, pages: number }> {
    try {
      const service = await this.getService()
      return service.listFAQs(params)
    } catch (error) {
      console.error('Error listing FAQs (unified):', error)
      return { items: [], total: 0, pages: 0 }
    }
  }

  async createFAQ(faq: any): Promise<import('./types').FAQEntry> {
    try {
      const service = await this.getService()
      return service.createFAQ(faq)
    } catch (error) {
      console.error('Error creating FAQ (unified):', error)
      throw error
    }
  }

  async updateFAQ(id: number, updates: any): Promise<import('./types').FAQEntry> {
    try {
      const service = await this.getService()
      return service.updateFAQ(id, updates)
    } catch (error) {
      console.error('Error updating FAQ (unified):', error)
      throw error
    }
  }

  async deleteFAQ(id: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.deleteFAQ(id)
    } catch (error) {
      console.error('Error deleting FAQ (unified):', error)
      throw error
    }
  }

  async linkOrderToInteraction(customerPhone: string, orderId: number): Promise<void> {
    try {
      const service = await this.getService()
      return service.linkOrderToInteraction(customerPhone, orderId)
    } catch (error) {
      console.error('Error linking order to interaction (unified):', error)
    }
  }
}

class ApiInventoryService implements IInventoryService {
  async initializeData(): Promise<void> {
    await apiClient.initializeData()
  }

  async fetchProducts(
    profileSlug?: string,
    search?: string,
    includeInactive = false
  ): Promise<ProductWithStock[]> {
    return apiClient.fetchProducts(profileSlug, search, includeInactive)
  }

  async getProducts(): Promise<ProductWithStock[]> {
    return this.fetchProducts(undefined, undefined, true)
  }

  async createOrder(request: CreateOrderRequest): Promise<OrderWithItems> {
    return apiClient.createOrder(request)
  }

  async fetchOrders(salesProfileSlug?: string): Promise<OrderWithItems[]> {
    return apiClient.fetchOrders(salesProfileSlug)
  }

  async getOrders(): Promise<OrderWithItems[]> {
    return this.fetchOrders()
  }

  async createProfile(profile: Omit<Profile, 'id'>): Promise<Profile> {
    return apiClient.createProfile(profile.name, profile.slug)
  }

  async listProfiles(): Promise<Profile[]> {
    return apiClient.listProfiles()
  }

  async getProfiles(): Promise<Profile[]> {
    return this.listProfiles()
  }

  async listSalesProfiles(): Promise<SalesProfile[]> {
    return apiClient.listSalesProfiles()
  }

  async getSalesProfiles(): Promise<SalesProfile[]> {
    return this.listSalesProfiles()
  }

  async getSalesProfile(id: number): Promise<SalesProfile> {
    return apiClient.getSalesProfile(id)
  }

  async listLocations(): Promise<Location[]> {
    return apiClient.listLocations()
  }

  async getLocations(): Promise<Location[]> {
    return this.listLocations()
  }

  async getLocation(id: number): Promise<Location> {
    return apiClient.getLocation(id)
  }

  async createSalesProfile(profile: Omit<SalesProfile, 'id' | 'created_at' | 'updated_at'>): Promise<SalesProfile> {
    return apiClient.createSalesProfile(profile)
  }

  async updateSalesProfile(id: number, updates: Partial<SalesProfile>): Promise<SalesProfile> {
    return apiClient.updateSalesProfile(id, updates)
  }

  async deleteSalesProfile(id: number): Promise<void> {
    return apiClient.deleteSalesProfile(id)
  }

  async createLocation(location: Omit<Location, 'id' | 'created_at' | 'updated_at'>): Promise<Location> {
    return apiClient.createLocation(location)
  }

  async updateLocation(id: number, updates: Partial<Location>): Promise<Location> {
    return apiClient.updateLocation(id, updates)
  }

  async deleteLocation(id: number): Promise<void> {
    return apiClient.deleteLocation(id)
  }

  async updateProfile(profileId: number, updates: Partial<Profile>): Promise<Profile> {
    return apiClient.updateProfile(profileId, updates)
  }

  async updateOrderStatus(
    orderId: number,
    estado: Order['estado']
  ): Promise<OrderWithItems> {
    return apiClient.updateOrderStatus(orderId, estado)
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
        es_regalo_promocion?: boolean
        imeis?: string[]
      }>
    }
  ): Promise<OrderWithItems> {
    return apiClient.updateOrder(orderId, updates)
  }

  async addProduct(
    product: Omit<Product, 'id'>,
    initialStock: number,
    locationId?: number
  ): Promise<ProductWithStock> {
    return apiClient.createProduct(product as Omit<Product, 'id' | 'activo'>, initialStock, locationId)
  }

  async createProduct(product: Omit<ProductWithStock, 'id'>, locationId?: number): Promise<ProductWithStock> {
    const { stock_disponible, ...productData } = product
    return this.addProduct(productData as Omit<Product, 'id'>, stock_disponible, locationId)
  }

  async updateStock(productId: number, cantidad: number, locationId: number): Promise<void> {
    return apiClient.updateStock(productId, cantidad, locationId)
  }

  async updateStockByLocation(productId: number, locationId: number, cantidad: number): Promise<void> {
    return apiClient.updateStockByLocation(productId, locationId, cantidad)
  }

  async updateProduct(
    productId: number,
    updates: Partial<ProductWithStock>
  ): Promise<ProductWithStock> {
    return apiClient.updateProduct(productId, updates)
  }

  async deleteProduct(productId: number): Promise<void> {
    return apiClient.deleteProduct(productId)
  }

  async deleteOrder(orderId: number): Promise<void> {
    return apiClient.deleteOrder(orderId)
  }

  async bulkCreateProducts(productsData: Partial<ProductWithStock>[], locationId?: number): Promise<ProductWithStock[]> {
    return apiClient.bulkCreateProducts(productsData, locationId)
  }

  async createStockTransfer(request: CreateStockTransferRequest): Promise<StockTransfer> {
    return apiClient.createStockTransfer(request)
  }

  async listStockTransfers(filters?: any): Promise<StockTransfer[]> {
    return apiClient.listStockTransfers(filters)
  }

  async confirmStockTransfer(id: number, confirmedBy: string, scannedImeis?: string[]): Promise<StockTransfer> {
    return apiClient.confirmStockTransfer(id, confirmedBy, scannedImeis)
  }

  async rejectStockTransfer(id: number, rejectedBy: string, rejectionReason?: string): Promise<StockTransfer> {
    return apiClient.rejectStockTransfer(id, rejectedBy, rejectionReason)
  }

  async cancelStockTransfer(id: number): Promise<void> {
    return apiClient.cancelStockTransfer(id)
  }

  async listSuppliers(includeInactive?: boolean): Promise<Supplier[]> {
    return apiClient.listSuppliers(includeInactive)
  }

  async createSupplier(supplier: Omit<Supplier, 'id' | 'created_at' | 'updated_at'>): Promise<Supplier> {
    return apiClient.createSupplier(supplier)
  }

  async updateSupplier(id: number, updates: Partial<Supplier>): Promise<Supplier> {
    return apiClient.updateSupplier(id, updates)
  }

  async deleteSupplier(id: number): Promise<void> {
    return apiClient.deleteSupplier(id)
  }

  async getStockByLocation(productId: number): Promise<StockByLocation[]> {
    return apiClient.getStockByLocation(productId)
  }

  async getLocationStock(locationId: number): Promise<StockByLocation[]> {
    return apiClient.getLocationStock(locationId)
  }

  async getDashboardStats(params?: { sales_profile_slug?: string; location_id?: number }): Promise<DashboardStats> {
    return apiClient.getDashboardStats(params)
  }

  async getSalesReport(params?: { sales_profile_slug?: string; date_from?: string; date_to?: string; top_limit?: number }): Promise<SalesReport> {
    return apiClient.getSalesReport(params)
  }

  async getInventoryAlerts(params?: { location_id?: number }): Promise<InventoryAlert[]> {
    return apiClient.getInventoryAlerts(params)
  }

  async getStockSummaryByLocation(activeOnly?: boolean): Promise<StockSummaryByLocation[]> {
    return apiClient.getStockSummaryByLocation(activeOnly ?? true)
  }

  async getSalesSummaryByLocation(params?: { start_date?: string; end_date?: string }): Promise<SalesSummaryByLocation[]> {
    return apiClient.getSalesSummaryByLocation(params)
  }

  async getTopProductsByLocation(locationId: number, params?: { start_date?: string; end_date?: string; limit?: number }): Promise<TopProductByLocationEntry[]> {
    return apiClient.getTopProductsByLocation(locationId, params)
  }

  async generateBusinessInsights(params?: {
    sales_profile_slug?: string
    sales_profile_id?: number
    location_id?: number
    days?: number
    use_cache?: boolean
    force_refresh?: boolean
  }): Promise<BusinessInsightsResponse> {
    return apiClient.generateBusinessInsights(params)
  }

  async getForecasting(): Promise<SalesForecast[]> {
    return apiClient.getForecasting()
  }

  async getAIStatus(alertsLimit = 5): Promise<AIStatusResponse> {
    return apiClient.getAIStatus(alertsLimit)
  }

  async getPublicCatalog(filters?: PublicCatalogFilters): Promise<PaginatedResponse<PublicProduct>> {
    return apiClient.getPublicCatalog(filters)
  }

  async getAvailableIMEIs(productId: number, locationId: number): Promise<string[]> {
    return apiClient.getAvailableIMEIs(productId, locationId)
  }

  async createReturn(returnData: CreateReturnRequest): Promise<Return> {
    return apiClient.createReturn(returnData)
  }

  async getReturns(): Promise<Return[]> {
    return apiClient.getReturns()
  }

  async getBanks(activeOnly?: boolean): Promise<Bank[]> {
    return apiClient.getBanks(activeOnly ?? true)
  }

  async createBank(bank: Partial<Bank>): Promise<Bank> {
    return apiClient.createBank(bank)
  }

  async updateBank(id: number, updates: Partial<Bank>): Promise<Bank> {
    return apiClient.updateBank(id, updates)
  }

  async createFinancingOption(bankId: number, option: Partial<FinancingOption>): Promise<FinancingOption> {
    return apiClient.createFinancingOption(bankId, option)
  }

  async deleteFinancingOption(optionId: number): Promise<void> {
    return apiClient.deleteFinancingOption(optionId)
  }

  async getTradeInPolicies(): Promise<TradeInPolicy[]> {
    return apiClient.getTradeInPolicies()
  }

  async createTradeInPolicy(policy: Omit<TradeInPolicy, 'id' | 'created_at'>): Promise<TradeInPolicy> {
    return apiClient.createTradeInPolicy(policy)
  }

  async deleteTradeInPolicy(id: number): Promise<void> {
    return apiClient.deleteTradeInPolicy(id)
  }

  async listUsers(): Promise<User[]> {
    return apiClient.listUsers()
  }

  async createUser(user: CreateUserRequest): Promise<User> {
    return apiClient.createUser(user)
  }

  async deleteUser(userId: number): Promise<void> {
    return apiClient.deleteUser(userId)
  }

  async updateUserRole(userId: number, roleId: number): Promise<User> {
    return apiClient.updateUserRole(userId, roleId)
  }

  async updateUser(userId: number, updates: Partial<User> & { password?: string; role_id?: number }): Promise<User> {
    return apiClient.updateUser(userId, updates)
  }

  async listRoles(): Promise<Role[]> {
    return apiClient.listRoles()
  }

  async listPermissions(): Promise<Permission[]> {
    return apiClient.listPermissions()
  }

  async getIMEIHistory(imei: string): Promise<IMEIHistory[]> {
    return apiClient.getIMEIHistory(imei)
  }

  async checkWarrantyStatus(imei: string): Promise<WarrantyStatus> {
    return apiClient.checkWarrantyStatus(imei)
  }

  async listTrainingQueue(status?: string): Promise<TrainingQueueItem[]> {
    return apiClient.listTrainingQueue(status)
  }

  async updateTrainingQueueItem(id: number, updates: Partial<TrainingQueueItem>): Promise<TrainingQueueItem> {
    return apiClient.updateTrainingQueueItem(id, updates)
  }

  async resolveTrainingQueueItem(id: number, action: 'approve' | 'reject' | 'convert_to_faq', correction?: string): Promise<void> {
    return apiClient.resolveTrainingItem(id, action, correction)
  }

  async getCustomers(search?: string): Promise<Customer[]> {
    return apiClient.getCustomers(search)
  }

  async updateCustomer(id: number, updates: Partial<Customer>): Promise<Customer> {
    return apiClient.updateCustomer(id, updates)
  }

  async listCustomerStats(params?: { sales_profile_slug?: string; page?: number; per_page?: number }): Promise<CustomerStats[]> {
    return apiClient.listCustomerStats(params)
  }

  async getCustomerStatsByPhone(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerStats> {
    return apiClient.getCustomerStatsByPhone(customerPhone, params)
  }

  async getCustomerHistory(customerPhone: string, params?: { sales_profile_slug?: string }): Promise<CustomerHistory> {
    return apiClient.getCustomerHistory(customerPhone, params)
  }

  async getAIProfileConfig(salesProfileId: number): Promise<AIProfileConfig | null> {
    return apiClient.getAIProfileConfig(salesProfileId)
  }

  async updateAIProfileConfig(id: number, updates: Partial<AIProfileConfig>): Promise<AIProfileConfig> {
    return apiClient.updateAIProfileConfig(id, updates)
  }

  async getAIContext(payload: AIContextPayload): Promise<AIContextResponse> {
    return apiClient.getAIContext(payload)
  }

  async generateAIReply(payload: AIReplyPayload): Promise<AIReplyResponse> {
    return apiClient.generateAIReply(payload)
  }

  async logAIInteraction(payload: AIInteractionLogPayload): Promise<{ status: string }> {
    return apiClient.logAIInteraction(payload)
  }

  async submitAITrainingExample(payload: TrainingSubmissionPayload): Promise<{ status: string }> {
    return apiClient.submitAITrainingExample(payload)
  }

  async flagCustomerAsTroll(phoneNumber: string, reason: string): Promise<FlagTrollResponse> {
    return apiClient.flagCustomerAsTroll(phoneNumber, reason)
  }

  async getStockHistory(productId: number, params?: any): Promise<StockHistory[]> {
    return apiClient.getStockHistory(productId, params)
  }

  async getLocationStockHistory(locationId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]> {
    return apiClient.getLocationStockHistory(locationId, params)
  }

  async getProfileStockHistory(profileId: number, params?: { limit?: number; tipo_cambio?: string; days?: number }): Promise<StockHistory[]> {
    return apiClient.getProfileStockHistory(profileId, params)
  }

  async createStockHistoryEntry(entry: StockHistoryCreateRequest): Promise<StockHistory> {
    return apiClient.createStockHistoryEntry(entry)
  }

  async getProductStockStats(productId: number, days?: number): Promise<StockHistoryStats> {
    return apiClient.getProductStockStats(productId, days ?? 30)
  }

  async listFAQs(params?: any): Promise<{ items: import('./types').FAQEntry[], total: number, pages: number }> {
    return apiClient.listFAQs(params)
  }

  async createFAQ(faq: any): Promise<import('./types').FAQEntry> {
    return apiClient.createFAQ(faq)
  }

  async updateFAQ(id: number, updates: any): Promise<import('./types').FAQEntry> {
    return apiClient.updateFAQ(id, updates)
  }

  async deleteFAQ(id: number): Promise<void> {
    return apiClient.deleteFAQ(id)
  }

  async linkOrderToInteraction(customerPhone: string, orderId: number): Promise<void> {
    return apiClient.linkOrderToInteraction(customerPhone, orderId)
  }
}

export function inventoryServiceFactory(_useAPI: boolean, _apiUrl: string): IInventoryService {
  return new UnifiedInventoryService()
}

export const inventoryServiceInstance: IInventoryService = new UnifiedInventoryService()

export { getUseApiSetting }
