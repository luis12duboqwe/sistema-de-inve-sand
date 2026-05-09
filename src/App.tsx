import { useState, useEffect, useMemo } from 'react'
import { useKV } from '@/hooks/use-kv'
import { getKV } from '@/lib/kvStorage'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { toast } from 'sonner'
import { Package, ShoppingCart, MagnifyingGlass, Plus, Gear, Keyboard, Download, CloudArrowUp, Database, Upload, CheckSquare, Square, Trash, CheckCircle, XCircle, Power, Pulse, FunnelSimple, ChartLine, Sparkle, Lightbulb, MapPin, Robot, ArrowsLeftRight, User as UserIcon, GraduationCap, ShieldCheck, CreditCard, Wrench, ArrowCounterClockwise, Camera, CaretUpDown, SquaresFour, Rows } from '@phosphor-icons/react'
import type { User, Profile, ProductWithStock, OrderWithItems, AdvancedSearchFilters, SalesProfile, Location } from '@/lib/types'
import { ProductCard } from '@/components/ProductCard'
import { OrderCard } from '@/components/OrderCard'
import { ManageSuppliersDialog } from '@/components/ManageSuppliersDialog'
import { ReturnsListDialog } from '@/components/ReturnsListDialog'
import { WarrantyCheckDialog } from '@/components/WarrantyCheckDialog'
import { FinancingSettings } from '@/components/FinancingSettings'
import { NewProductDialog } from '@/components/NewProductDialog'
import { RestockProductDialog } from '@/components/RestockProductDialog'
import { NewOrderDialog } from '@/components/NewOrderDialog'
import { EditProductDialog } from '@/components/EditProductDialog'
import { TransferStockDialog } from '@/components/TransferStockDialog'
import { TransferListDialog } from '@/components/TransferListDialog'
import { EditOrderDialog } from '@/components/EditOrderDialog'
import { SettingsDialog } from '@/components/SettingsDialog'
import { KeyboardShortcutsDialog } from '@/components/KeyboardShortcutsDialog'
import { ImportProductsDialog } from '@/components/ImportProductsDialog'
import { DashboardStats } from '@/components/DashboardStats'
import { HealthCheckDialog } from '@/components/HealthCheckDialog'
import { LowStockAlert } from '@/components/LowStockAlert'
import { NotificationCenter } from '@/components/NotificationCenter'
import { NotificationSettingsDialog } from '@/components/NotificationSettingsDialog'
import { LowStockReportDialog } from '@/components/LowStockReportDialog'
import { AdvancedSearchDialog } from '@/components/AdvancedSearchDialog'
import { ReportsDialog } from '@/components/ReportsDialog'
import { SalesHistoryDialog } from '@/components/SalesHistoryDialog'
import { CustomerHistoryDialog } from '@/components/CustomerHistoryDialog'
import { AIForecastingDialog } from '@/components/AIForecastingDialog'
import { ForecastingWidget } from '@/components/ForecastingWidget'
import { AIStatusWidget } from '@/components/AIStatusWidget'
import { AIStatusDialog } from '@/components/AIStatusDialog'
import { OptimizationInsightsDialog } from '@/components/OptimizationInsightsDialog'
import { SyncIndicator } from '@/components/SyncIndicator'
import { BackendConnectionCheck } from '@/components/BackendConnectionCheck'
import { StockHistoryDialog } from '@/components/StockHistoryDialog'
import { LocationsList } from '@/components/LocationsList'
import { SalesProfilesList } from '@/components/SalesProfilesList'
import { AITrainingCenter } from '@/components/AITrainingCenter'
import { CustomerInsights } from '@/components/CustomerInsights'
import { AIChatOrchestratorDialog } from '@/components/AIChatOrchestratorDialog'
import { ChannelHealthDialog } from '@/components/ChannelHealthDialog'
import { ManageUsersDialog } from '@/components/ManageUsersDialog'
import { LoginPage } from '@/components/LoginPage'
import { PendingTradeInsDialog } from '@/components/PendingTradeInsDialog'
import { PhotoRequestsDashboardDialog } from '@/components/PhotoRequestsDashboardDialog'
import { apiClient } from '@/lib/apiClient'
import { initializeDefaultData, clearAllData } from '@/lib/dataInitializer'
import { SyncSettingsDialog } from '@/components/SyncSettingsDialog'
import { DailyCloseDialog } from '@/components/DailyCloseDialog'
import { MultiStoreControlDialog } from '@/components/MultiStoreControlDialog'
import { ValidationCodeDialog } from '@/components/ValidationCodeDialog'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'
import { useInitializeData } from '@/hooks/use-initialize-data'
import { useHealthCheck } from '@/hooks/use-health-check'
import { useForecasting } from '@/hooks/use-forecasting'
import { useAIStatus } from '@/hooks/use-ai-status'
import { useRealtimeSync } from '@/hooks/use-realtime-sync'
import { exportProductsToCSV, exportOrdersToCSV } from '@/lib/exportUtils'
import { generateOrderPDF } from '@/lib/pdfExport'
import { filterOrdersByAdvancedSearch, generateReportData } from '@/lib/reportUtils'
import { inventoryServiceFactory, inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { motion } from 'framer-motion'
import PublicCatalog from '@/components/PublicCatalog'

function MainApp() {
  const [backendConnected, setBackendConnected] = useState(false)
  const { isInitialized, isLoading } = useInitializeData()
  const [products, setProducts] = useKV<ProductWithStock[]>('inventory-products', [])
  const [orders, setOrders] = useKV<OrderWithItems[]>('inventory-orders', [])
  const [profiles, setProfiles] = useKV<Profile[]>('inventory-profiles', [])
  const [salesProfiles, setSalesProfiles] = useState<SalesProfile[]>([])
  const [locations, setLocations] = useKV<Location[]>('inventory-locations', [])
  const [dataLoaded, setDataLoaded] = useState(false)
  // V2.0: Renamed for clarity - this filters views by sales channel, not business segment
  const [selectedSalesChannel, setSelectedSalesChannel] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [orderStatusFilter, setOrderStatusFilter] = useState<string>('all')
  const [showInactive, setShowInactive] = useState(false)
  const [productViewMode, setProductViewMode] = useKV<'grid' | 'list'>('inventory_product_view_mode', 'grid')
  const [customerSearchTerm, setCustomerSearchTerm] = useState('')
  const [orderDateFrom, setOrderDateFrom] = useState<string>('')
  const [orderDateTo, setOrderDateTo] = useState<string>('')
  const [activeTab, setActiveTab] = useState('products')
  const [showNewProductDialog, setShowNewProductDialog] = useState(false)
  const [showRestockDialog, setShowRestockDialog] = useState(false)
  const [showNewOrderDialog, setShowNewOrderDialog] = useState(false)
  const [showSettingsDialog, setShowSettingsDialog] = useState(false)
  const [showDailyCloseDialog, setShowDailyCloseDialog] = useState(false)
  const [showMultiStoreControl, setShowMultiStoreControl] = useState(false)
  const [multiStoreInitialTab, setMultiStoreInitialTab] = useState<string>('receipts')
  const [showKeyboardDialog, setShowKeyboardDialog] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [showSuppliersDialog, setShowSuppliersDialog] = useState(false)
  const [showHealthCheckDialog, setShowHealthCheckDialog] = useState(false)
  const [showNotificationSettings, setShowNotificationSettings] = useState(false)
  const [showLowStockReport, setShowLowStockReport] = useState(false)
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false)
  const [showReportsDialog, setShowReportsDialog] = useState(false)
  const [showSalesHistoryDialog, setShowSalesHistoryDialog] = useState(false)
  const [showCustomerHistory, setShowCustomerHistory] = useState(false)
  const [showForecastingDialog, setShowForecastingDialog] = useState(false)
  const [showOptimizationDialog, setShowOptimizationDialog] = useState(false)
  const [showSyncSettings, setShowSyncSettings] = useState(false)
  const [selectedCustomerPhone, setSelectedCustomerPhone] = useState('')
  const [advancedFilters, setAdvancedFilters] = useState<AdvancedSearchFilters | null>(null)
  const [editingProduct, setEditingProduct] = useState<ProductWithStock | null>(null)
  const [transferringProduct, setTransferringProduct] = useState<ProductWithStock | null>(null)
  const [quickTransferProductId, setQuickTransferProductId] = useState<string>('')
  const [quickTransferSearchTerm, setQuickTransferSearchTerm] = useState('')
  const [quickTransferProductOpen, setQuickTransferProductOpen] = useState(false)
  const [transferOriginFilter, setTransferOriginFilter] = useState<string>('all')
  const [quickTransferToLocationId, setQuickTransferToLocationId] = useState<string>('all')
  const [showTransferListDialog, setShowTransferListDialog] = useState(false)
  const [showAITraining, setShowAITraining] = useState(false)
  const [showAIStatusDialog, setShowAIStatusDialog] = useState(false)
  const [showCustomerInsights, setShowCustomerInsights] = useState(false)
  const [showAIChatOrchestrator, setShowAIChatOrchestrator] = useState(false)
  const [showChannelHealthDialog, setShowChannelHealthDialog] = useState(false)
  const [channelHealthReady, setChannelHealthReady] = useState<boolean | null>(null)
  const [, setIsChannelHealthLoading] = useState(false)
  const [showManageUsersDialog, setShowManageUsersDialog] = useState(false)
  const [showPendingTradeIns, setShowPendingTradeIns] = useState(false)
  const [showPhotoRequestsDialog, setShowPhotoRequestsDialog] = useState(false)
  const [photoRequestPendingCount, setPhotoRequestPendingCount] = useState(0)
  const [showReturnsListDialog, setShowReturnsListDialog] = useState(false)
  const [showWarrantyCheck, setShowWarrantyCheck] = useState(false)
  const [viewingProductHistory, setViewingProductHistory] = useState<ProductWithStock | null>(null)
  const [editingOrder, setEditingOrder] = useState<OrderWithItems | null>(null)
  const [useAPI] = useKV<boolean>('settings_use_api', false)
  const [apiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')
  const [selectedProducts, setSelectedProducts] = useState<Set<number>>(new Set())
  const [selectedOrders, setSelectedOrders] = useState<Set<number>>(new Set())
  const [bulkActionMode, setBulkActionMode] = useState(false)
  const [validationCodeRequest, setValidationCodeRequest] = useState<{
    title: string
    description: string
    resolve: (code: string | null) => void
  } | null>(null)
  
  // Auth State
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [showLoginDialog, setShowLoginDialog] = useState(false)

  useEffect(() => {
    const token = apiClient.getToken()
    const storedUser = localStorage.getItem('auth_user')
    
    // Only show login if using API mode
    if (useAPI) {
      if (token && storedUser) {
        try {
          setCurrentUser(JSON.parse(storedUser))
        } catch (error) {
          console.error('Error parsing auth_user from storage', error)
          setShowLoginDialog(true)
        }
      } else {
        setShowLoginDialog(true)
      }
    }
  }, [useAPI])

  useEffect(() => {
    if (currentUser) {
      console.log('👤 Current User:', currentUser)
      console.log('🛡️ Role:', currentUser.role?.name)
      console.log('🔐 Is System Role:', currentUser.role?.is_system_role)
    }
  }, [currentUser])

  useEffect(() => {
    if (!useAPI) {
      setChannelHealthReady(null)
      setIsChannelHealthLoading(false)
      return
    }

    let mounted = true

    const refreshChannelHealth = async () => {
      if (!mounted) return
      setIsChannelHealthLoading(true)
      try {
        const health = await apiClient.getChannelsHealth()
        if (!mounted) return
        setChannelHealthReady(Boolean(health.ready))
      } catch (error) {
        if (!mounted) return
        console.warn('No se pudo obtener estado de canales:', error)
        setChannelHealthReady(null)
      } finally {
        if (mounted) {
          setIsChannelHealthLoading(false)
        }
      }
    }

    refreshChannelHealth()
    const intervalId = window.setInterval(refreshChannelHealth, 120000)

    return () => {
      mounted = false
      window.clearInterval(intervalId)
    }
  }, [useAPI])

  useEffect(() => {
    if (!useAPI || !currentUser) {
      setPhotoRequestPendingCount(0)
      return
    }

    let mounted = true

    const refreshPhotoSummary = async () => {
      try {
        const summary = await apiClient.getPhotoRequestSummary()
        if (!mounted) return
        setPhotoRequestPendingCount(summary.assigned_to_me || summary.pending_total || 0)
      } catch (error) {
        if (!mounted) return
        console.warn('No se pudo obtener resumen de solicitudes de fotos:', error)
      }
    }

    void refreshPhotoSummary()
    const intervalId = window.setInterval(() => {
      void refreshPhotoSummary()
    }, 20000)

    return () => {
      mounted = false
      window.clearInterval(intervalId)
    }
  }, [useAPI, currentUser])

  const handleLoginSuccess = (user: User, _token: string) => {
    console.log('✅ Login Success:', user)
    setCurrentUser(user)
    localStorage.setItem('auth_user', JSON.stringify(user))
    setShowLoginDialog(false)
  }

  const handleLogout = () => {
    apiClient.logout()
    localStorage.removeItem('auth_user')
    setCurrentUser(null)
    setShowLoginDialog(true)
  }

  // Listen for unauthorized events from apiClient
  useEffect(() => {
    const handleUnauthorized = () => {
      console.log('🔒 Sesión expirada detectada, cerrando sesión...')
      handleLogout()
      toast.error('Tu sesión ha expirado. Por favor inicia sesión nuevamente.')
    }

    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized)
    }
  }, [])

  const { result: healthCheckResult, isRunning: isHealthCheckRunning, runCheck, performAutoFix } = useHealthCheck(
    products ?? [],
    orders ?? [],
    profiles ?? []
  )

  const { syncStatus, markSyncStart, markSyncComplete } = useRealtimeSync()

  // useSyncDetection removed - useKV already handles cross-tab sync via storage events
  // No need to manually update state, useKV automatically syncs between tabs

  // V2.0: For features that need a specific sales channel (reports, forecasting)
  const currentProfile = selectedSalesChannel !== 'all' 
    ? (profiles ?? []).find(p => p.slug === selectedSalesChannel) || null
    : (profiles ?? [])[0] || null

  const {
    summary: forecastingSummary,
    lastUpdated: forecastingLastUpdated,
    isGenerating: isForecastingGenerating,
    generateForecastData,
    getCriticalAlerts,
  } = useForecasting(
    products ?? [],
    orders ?? [],
    currentProfile,
    false
  )

  const hasPermission = (slug: string): boolean => {
    if (!useAPI) return true
    if (currentUser?.is_superuser) return true
    return currentUser?.role?.permissions?.some(permission => permission.slug === slug) ?? false
  }

  const canViewSettings = hasPermission('settings:view')
  const canEditSettings = hasPermission('settings:edit')
  const canViewReports = hasPermission('reports:view')
  const canViewInventory = hasPermission('inventory:view')
  const canCreateInventory = hasPermission('inventory:create')
  const canEditInventory = hasPermission('inventory:edit')
  const canDeleteInventory = hasPermission('inventory:delete')
  const canAdjustInventory = hasPermission('inventory:adjust')
  const canCountInventory = hasPermission('inventory:count')
  const canManagePurchases = hasPermission('purchases:manage')
  const canViewOrders = hasPermission('orders:view')
  const canViewLocations = hasPermission('locations:view') || hasPermission('locations:manage')
  const canManageLocations = hasPermission('locations:manage')
  const canManageLocationAccess = hasPermission('locations:access_manage')
  const canCreateOrders = hasPermission('orders:create')
  const canEditOrders = hasPermission('orders:edit')
  const canDeleteOrders = hasPermission('orders:delete')
  const canManageUsers = hasPermission('users:manage')
  const canManageCashCloses = hasPermission('cash_closes:manage')
  const canViewAudit = hasPermission('audit:view')
  const isSuperUser = !useAPI || currentUser?.is_superuser === true

  const canValidateDailyClose = !useAPI || canEditOrders
  const canAccessAIOps = hasPermission('ai:manage')
  const canAccessMultiStoreControl = isSuperUser || canViewInventory || canCountInventory || canAdjustInventory || canManagePurchases || canManageCashCloses || canManageLocationAccess || canViewAudit || canViewReports
  const activeLocations = useMemo(() => (locations ?? []).filter(location => location.activo), [locations])
  const productsWithLocationTracking = useMemo(
    () => (products ?? []).filter(product => (product.stock_items?.length ?? 0) > 0),
    [products]
  )
  const totalTrackedUnits = useMemo(
    () => (products ?? []).reduce((total, product) => total + Number(product.stock_disponible || 0), 0),
    [products]
  )
  const outOfStockProducts = useMemo(
    () => (products ?? []).filter(product => Number(product.stock_disponible || 0) <= 0).length,
    [products]
  )
  const locatedOrders = useMemo(
    () => (orders ?? []).filter(order => order.source_location_id).length,
    [orders]
  )
  const locationSnapshots = useMemo(() => {
    return activeLocations
      .map(location => {
        const productsAtLocation = (products ?? []).filter(product =>
          product.stock_items?.some(stockItem => stockItem.location_id === location.id && Number(stockItem.cantidad_disponible || 0) > 0)
        )

        const unitsAtLocation = (products ?? []).reduce((total, product) => {
          const stockItem = product.stock_items?.find(item => item.location_id === location.id)
          return total + Number(stockItem?.cantidad_disponible || 0)
        }, 0)

        return {
          id: location.id,
          nombre: location.nombre,
          tipo: location.tipo,
          productsAtLocation: productsAtLocation.length,
          unitsAtLocation,
        }
      })
      .sort((a, b) => b.unitsAtLocation - a.unitsAtLocation)
      .slice(0, 4)
  }, [activeLocations, products])

  const openMultiStoreSection = (tab: string) => {
    setMultiStoreInitialTab(tab)
    setShowMultiStoreControl(true)
  }
  const transferProducts = (products ?? []).filter(product => {
    if (!product.stock_items || product.stock_items.length === 0) return false
    if (transferOriginFilter === 'all') return true

    return product.stock_items.some(stockItem => {
      const sameLocation = String(stockItem.location_id) === transferOriginFilter
      const stockLibre = Math.max(0, (stockItem.cantidad_disponible || 0) - (stockItem.cantidad_reservada || 0))
      return sameLocation && stockLibre > 0
    })
  })

  const getTransferAvailableStock = (product: ProductWithStock, locationId?: string) => {
    if (!locationId || locationId === 'all') return product.stock_disponible ?? 0

    const stockItem = product.stock_items?.find(item => String(item.location_id) === locationId)
    if (!stockItem) return 0

    return Math.max(0, (stockItem.cantidad_disponible || 0) - (stockItem.cantidad_reservada || 0))
  }

  const filteredTransferProducts = transferProducts
    .filter(product => {
      const term = quickTransferSearchTerm.trim().toLowerCase()
      if (!term) return true
      const nombre = String(product.nombre ?? '').toLowerCase()
      const marca = String(product.marca ?? '').toLowerCase()
      const modelo = String(product.modelo ?? '').toLowerCase()
      const sku = String(product.sku ?? '').toLowerCase()
      return (
        nombre.includes(term) ||
        marca.includes(term) ||
        modelo.includes(term) ||
        sku.includes(term)
      )
    })
    .sort((a, b) => {
      const stockA = getTransferAvailableStock(a, transferOriginFilter)
      const stockB = getTransferAvailableStock(b, transferOriginFilter)
      if (stockB !== stockA) return stockB - stockA
      return a.nombre.localeCompare(b.nombre)
    })

  const selectedQuickTransferProduct = (products ?? []).find(product => String(product.id) === quickTransferProductId) ?? null

  const {
    status: aiStatus,
    isLoading: isAIStatusLoading,
    error: aiStatusError,
    refresh: refreshAIStatus,
    isApiMode: isAIStatusAvailable,
  } = useAIStatus(useAPI && canAccessAIOps ? 180000 : 0, !useAPI || canAccessAIOps)

  const service = inventoryServiceFactory(useAPI ?? false, apiUrl ?? 'http://localhost:8000/api')
  const aiAttentionCount = Math.min(
    99,
    (aiStatus?.forecasting_alerts?.length ?? 0) + (aiStatus?.training_backlog ?? 0)
  )

  useEffect(() => {
    const loadData = async () => {
      if (!isInitialized) return
      if (useAPI && !currentUser) return
      
      try {
        console.log('🔄 Cargando datos iniciales...')
        console.log('📊 useAPI:', useAPI, 'apiUrl:', apiUrl)
        
        // AUTO-RESET: Limpiar datos locales una sola vez para asegurar limpieza
        const kv = getKV()
        const resetDone = await kv.get('v2_reset_complete_final')
        if (!resetDone && !useAPI) {
          console.log('🧹 Ejecutando limpieza automática de datos locales...')
          await clearAllData()
          await kv.set('v2_reset_complete_final', true)
          window.location.reload()
          return
        }

        // Inicializar datos por defecto si no existen
        await initializeDefaultData()
        
        const currentService = inventoryServiceFactory(useAPI ?? false, apiUrl ?? 'http://localhost:8000/api')
        const [loadedProducts, loadedOrders, loadedProfiles, loadedSalesProfiles, loadedLocations] = await Promise.all([
          canViewInventory ? currentService.getProducts() : Promise.resolve([]),
          canViewOrders ? currentService.getOrders() : Promise.resolve([]),
          canViewSettings ? currentService.getProfiles() : Promise.resolve([]),
          (canViewSettings || canViewOrders || canCreateOrders) && currentService.getSalesProfiles ? currentService.getSalesProfiles() : Promise.resolve([]),
          (canViewSettings || canViewLocations || canCreateOrders || canAccessMultiStoreControl) && currentService.getLocations ? currentService.getLocations() : Promise.resolve([])
        ])
        
        console.log('✅ Datos cargados:', {
          productos: loadedProducts.length,
          ordenes: loadedOrders.length,
          perfiles: loadedProfiles.length,
          salesProfiles: loadedSalesProfiles.length,
          locations: loadedLocations.length
        })
        
        setProducts(loadedProducts)
        setOrders(loadedOrders)
        setProfiles(loadedProfiles)
        setSalesProfiles(loadedSalesProfiles)
        setLocations(loadedLocations)
        setDataLoaded(true)
      } catch (error) {
        console.error('❌ Error loading data:', error)
        toast.error(`Error al cargar datos: ${error instanceof Error ? error.message : 'Error desconocido'}`)
        setDataLoaded(true)
      }
    }

    loadData()
  }, [isInitialized, useAPI, apiUrl, currentUser, canViewInventory, canViewOrders, canViewSettings, canCreateOrders, canViewLocations, canAccessMultiStoreControl, setProducts, setOrders, setProfiles, setSalesProfiles, setLocations])

  const handleBulkDeleteProducts = async () => {
    if (selectedProducts.size === 0) return
    
    try {
      markSyncStart()
      if (useAPI) {
        // En modo API, eliminar en el backend para evitar deriva de estado
        for (const productId of selectedProducts) {
          await service.deleteProduct(productId)
        }
        const refreshed = await inventoryServiceInstance.getProducts()
        setProducts(refreshed)
      } else {
        const updatedProducts = (products ?? []).filter(p => !selectedProducts.has(p.id))
        setProducts(updatedProducts)
      }
      toast.success(`${selectedProducts.size} productos eliminados`)
      setSelectedProducts(new Set())
      setBulkActionMode(false)
      markSyncComplete()
    } catch (error) {
      console.error('Error deleting products:', error)
      toast.error('Error al eliminar productos')
    }
  }

  const handleBulkToggleProductStatus = async () => {
    if (selectedProducts.size === 0) return
    
    try {
      if (useAPI) {
        // Sin endpoint bulk: actualizar uno por uno para mantener consistencia
        for (const product of products ?? []) {
          if (selectedProducts.has(product.id)) {
            await service.updateProduct(product.id, { activo: !product.activo })
          }
        }
        const refreshed = await inventoryServiceInstance.getProducts()
        setProducts(refreshed)
      } else {
        const updatedProducts = (products ?? []).map(p =>
          selectedProducts.has(p.id) ? { ...p, activo: !p.activo } : p
        )
        setProducts(updatedProducts)
      }
      toast.success(`Estado actualizado para ${selectedProducts.size} productos`)
      setSelectedProducts(new Set())
      setBulkActionMode(false)
    } catch (error) {
      console.error('Error updating products:', error)
      toast.error('Error al actualizar productos')
    }
  }

  const getCompletionValidationCode = async (newStatus: OrderWithItems['estado']): Promise<string | undefined | null> => {
    if (!useAPI || newStatus !== 'completada') return undefined

    try {
      const config = await apiClient.getDailyCloseConfig()
      if (!config.configured) return undefined
    } catch (error) {
      console.error('Error checking daily close validation config:', error)
      toast.error('No se pudo verificar el código de validación')
      return null
    }

    return new Promise(resolve => {
      setValidationCodeRequest({
        title: 'Validar venta',
        description: 'Ingrese el código configurado para completar y validar esta venta.',
        resolve,
      })
    })
  }

  const handleBulkUpdateOrderStatus = async (newStatus: OrderWithItems['estado']) => {
    if (selectedOrders.size === 0) return
    
    try {
      const validationCode = await getCompletionValidationCode(newStatus)
      if (validationCode === null) return

      if (useAPI) {
        for (const orderId of selectedOrders) {
          await service.updateOrderStatus(orderId, newStatus, validationCode)
        }
        const refreshed = await inventoryServiceInstance.getOrders()
        setOrders(refreshed)
      } else {
        const updatedOrders = (orders ?? []).map(o =>
          selectedOrders.has(o.id) ? { ...o, estado: newStatus } : o
        )
        setOrders(updatedOrders)
      }
      toast.success(`${selectedOrders.size} órdenes actualizadas a ${newStatus}`)
      setSelectedOrders(new Set())
      setBulkActionMode(false)
    } catch (error) {
      console.error('Error updating orders:', error)
      toast.error('Error al actualizar órdenes')
    }
  }

  const handleBulkDeleteOrders = async () => {
    if (selectedOrders.size === 0) return
    
    try {
      if (useAPI) {
        for (const orderId of selectedOrders) {
          await service.deleteOrder(orderId)
        }
        const refreshed = await inventoryServiceInstance.getOrders()
        setOrders(refreshed)
      } else {
        const updatedOrders = (orders ?? []).filter(o => !selectedOrders.has(o.id))
        setOrders(updatedOrders)
      }
      toast.success(`${selectedOrders.size} órdenes eliminadas`)
      setSelectedOrders(new Set())
      setBulkActionMode(false)
    } catch (error) {
      console.error('Error deleting orders:', error)
      toast.error('Error al eliminar órdenes')
    }
  }

  const toggleProductSelection = (productId: number) => {
    setSelectedProducts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(productId)) {
        newSet.delete(productId)
      } else {
        newSet.add(productId)
      }
      return newSet
    })
  }

  const toggleOrderSelection = (orderId: number) => {
    setSelectedOrders(prev => {
      const newSet = new Set(prev)
      if (newSet.has(orderId)) {
        newSet.delete(orderId)
      } else {
        newSet.add(orderId)
      }
      return newSet
    })
  }

  const selectAllProducts = () => {
    if (selectedProducts.size === filteredProducts.length) {
      setSelectedProducts(new Set())
    } else {
      setSelectedProducts(new Set(filteredProducts.map(p => p.id)))
    }
  }

  const selectAllOrders = () => {
    if (selectedOrders.size === filteredOrders.length) {
      setSelectedOrders(new Set())
    } else {
      setSelectedOrders(new Set(filteredOrders.map(o => o.id)))
    }
  }

  useKeyboardShortcuts([
    {
      id: 'show-help',
      key: '?',
      shiftKey: true,
      action: () => setShowKeyboardDialog(true),
      description: 'Mostrar atajos de teclado',
      category: 'general'
    },
    {
      id: 'focus-search',
      key: 'k',
      ctrlKey: true,
      action: () => {
        const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement
        searchInput?.focus()
      },
      description: 'Enfocar búsqueda',
      category: 'general'
    },
    {
      id: 'open-settings',
      key: ',',
      ctrlKey: true,
      action: () => {
        if (canViewSettings) {
          setShowSettingsDialog(true)
        }
      },
      description: 'Abrir configuración',
      category: 'general'
    },
    {
      id: 'open-notifications',
      key: 'n',
      altKey: true,
      action: () => {
        const notificationButton = document.querySelector('[data-notification-trigger]') as HTMLButtonElement
        notificationButton?.click()
      },
      description: 'Abrir notificaciones',
      category: 'general'
    },
    {
      id: 'view-low-stock',
      key: 'l',
      altKey: true,
      action: () => setShowLowStockReport(true),
      description: 'Ver reporte de stock bajo',
      category: 'general'
    },
    {
      id: 'view-forecasting',
      key: 'f',
      altKey: true,
      action: () => {
        if (canAccessAIOps) {
          setShowForecastingDialog(true)
        }
      },
      description: 'Ver pronóstico de ventas IA',
      category: 'general'
    },
    {
      id: 'view-optimization',
      key: 'o',
      altKey: true,
      action: () => {
        if (canAccessAIOps) {
          setShowOptimizationDialog(true)
        }
      },
      description: 'Ver insights de optimización',
      category: 'general'
    },
    {
      id: 'open-sync-settings',
      key: 's',
      altKey: true,
      action: () => setShowSyncSettings(true),
      description: 'Configuración de sincronización',
      category: 'general'
    },
    {
      id: 'nav-products',
      key: '1',
      action: () => setActiveTab('products'),
      description: 'Ir a Productos',
      category: 'navigation'
    },
    {
      id: 'nav-orders',
      key: '2',
      action: () => {
        if (canViewOrders) {
          setActiveTab('orders')
        }
      },
      description: 'Ir a Órdenes',
      category: 'navigation'
    },
    {
      id: 'nav-profiles',
      key: '3',
      action: () => setActiveTab('profiles'),
      description: 'Ir a Perfiles',
      category: 'navigation'
    },
    {
      id: 'create-new',
      key: 'n',
      ctrlKey: true,
      action: () => {
        if (activeTab === 'products') {
          if (canCreateInventory) {
            setShowNewProductDialog(true)
          }
        } else if (activeTab === 'orders') {
          if (canCreateOrders) {
            setShowNewOrderDialog(true)
          }
        }
      },
      description: 'Crear nuevo elemento',
      category: 'actions'
    },
    {
      id: 'export-csv',
      key: 'e',
      ctrlKey: true,
      action: () => {
        if (activeTab === 'products') handleExportProducts()
        else if (activeTab === 'orders') handleExportOrders()
      },
      description: 'Exportar a CSV',
      category: 'actions'
    },
    {
      id: 'import-csv',
      key: 'i',
      ctrlKey: true,
      action: () => {
        if (activeTab === 'products') {
          if (canCreateInventory) {
            setShowImportDialog(true)
          }
        }
      },
      description: 'Importar desde CSV',
      category: 'actions'
    },
    {
      id: 'bulk-mode',
      key: 'b',
      ctrlKey: true,
      action: () => {
        setBulkActionMode(!bulkActionMode)
      },
      description: 'Modo selección múltiple',
      category: 'actions'
    },
    {
      id: 'clear-search',
      key: 'Escape',
      action: () => {
        setSearchTerm('')
        setCustomerSearchTerm('')
        setOrderDateFrom('')
        setOrderDateTo('')
      },
      description: 'Limpiar búsqueda',
      category: 'search'
    },
    {
      id: 'select-all',
      key: 'a',
      ctrlKey: true,
      action: () => {
        if (bulkActionMode) {
          if (activeTab === 'products') selectAllProducts()
          else if (activeTab === 'orders') selectAllOrders()
        }
      },
      description: 'Seleccionar todos',
      category: 'search'
    }
  ])

  const handleExportProducts = () => {
    const filtered = filteredProducts
    exportProductsToCSV(filtered)
    toast.success(`${filtered.length} productos exportados`)
  }

  const handleExportOrders = () => {
    const filtered = filteredOrders
    exportOrdersToCSV(filtered)
    toast.success(`${filtered.length} órdenes exportadas`)
  }

  const handleImportProducts = async (productsData: Partial<ProductWithStock>[], locationId: number | null) => {
    try {
      const importedProducts = await service.bulkCreateProducts(productsData, locationId ?? undefined)
      setProducts((current: ProductWithStock[]) => [...(current ?? []), ...importedProducts])
      toast.success(`${importedProducts.length} productos importados exitosamente`)
    } catch (error) {
      console.error('Error importing products:', error)
      toast.error('Error al importar productos')
      throw error
    }
  }

  // V2.0: Products are ALWAYS global - never filter by profile
  const filteredProducts = (products ?? []).filter(p => {
    if (!showInactive && !p.activo) return false
    
    if (categoryFilter && categoryFilter !== 'all' && p.categoria !== categoryFilter) return false
    
    if (searchTerm && searchTerm.trim()) {
      const term = searchTerm.toLowerCase()
      const nombre = String(p.nombre ?? '').toLowerCase()
      const marca = String(p.marca ?? '').toLowerCase()
      const modelo = String(p.modelo ?? '').toLowerCase()
      const sku = String(p.sku ?? '').toLowerCase()
      return nombre.includes(term) || marca.includes(term) || modelo.includes(term) || sku.includes(term)
    }
    
    return true
  })

  const filteredOrders = (() => {
    let filtered = (orders ?? []).filter(o => {
      // V2.0: Filter by sales channel if selected
      if (selectedSalesChannel !== 'all') {
        const salesProfile = (salesProfiles ?? []).find(sp => sp.slug === selectedSalesChannel)
        if (salesProfile) {
          if (o.sales_profile_id !== salesProfile.id) return false
        } else {
          // LEGACY fallback: use V1 profiles if sales profiles no existen
          const legacyProfile = (profiles ?? []).find(p => p.slug === selectedSalesChannel)
          if (!legacyProfile) return false
          if (o.profile_id !== legacyProfile.id && o.sales_profile_id !== legacyProfile.id) return false
        }
      }
      
      if (orderStatusFilter && orderStatusFilter !== 'all' && o.estado !== orderStatusFilter) return false
      
      if (customerSearchTerm && customerSearchTerm.trim()) {
        const term = customerSearchTerm.toLowerCase()
        const customerName = String(o.customer_name ?? '').toLowerCase()
        const customerPhone = String(o.customer_phone ?? '').toLowerCase()
        return customerName.includes(term) || customerPhone.includes(term)
      }

      // Filtro por fecha desde
      if (orderDateFrom) {
        const orderDate = new Date(o.created_at)
        const fromDate = new Date(orderDateFrom)
        if (orderDate < fromDate) return false
      }

      // Filtro por fecha hasta
      if (orderDateTo) {
        const orderDate = new Date(o.created_at)
        const toDate = new Date(orderDateTo)
        toDate.setHours(23, 59, 59, 999) // Incluir todo el día
        if (orderDate > toDate) return false
      }
      
      return true
    })

    if (advancedFilters) {
      filtered = filterOrdersByAdvancedSearch(filtered, advancedFilters)
    }

    // Sort by date descending (newest first)
    return filtered.sort((a, b) => {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  })()

  const activeProfiles = (profiles ?? []).filter(p => p.active)
  const activeSalesProfiles = (salesProfiles ?? []).filter(sp => sp.active)
  const channelOptions = activeSalesProfiles.length ? activeSalesProfiles : activeProfiles

  const handleTabChange = (value: string) => {
    if (value === 'products' && !canViewInventory) return
    if (value === 'orders' && !canViewOrders) return
    if (value === 'locations' && !canManageLocations) return
    if (value === 'sales-profiles' && !canViewSettings) return
    if (value === 'financing' && !canEditSettings) return
    if (value === 'ai-ops' && !canAccessAIOps) return

    setActiveTab(value)
    setBulkActionMode(false)
    setSelectedProducts(new Set())
    setSelectedOrders(new Set())
  }

  useEffect(() => {
    if (activeTab === 'products' && !canViewInventory) {
      if (canViewOrders) {
        setActiveTab('orders')
      } else if (canViewReports) {
        setActiveTab('charts')
      } else if (canManageLocations) {
        setActiveTab('locations')
      }
      return
    }
    if (activeTab === 'orders' && !canViewOrders) {
      setActiveTab('products')
    }
    if (activeTab === 'ai-ops' && !canAccessAIOps) {
      setActiveTab('products')
    }
  }, [activeTab, canViewInventory, canViewOrders, canViewReports, canManageLocations, canAccessAIOps])

  // Verificar conexión del backend primero
  if (!backendConnected) {
    return <BackendConnectionCheck onSuccess={() => setBackendConnected(true)} />
  }

  if (useAPI && showLoginDialog) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />
  }

  if (isLoading || !dataLoaded) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <motion.div 
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <motion.div
            animate={{ 
              scale: [1, 1.1, 1],
              rotate: [0, 10, -10, 0]
            }}
            transition={{ 
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          >
            <Sparkle size={64} className="mx-auto text-primary mb-4" weight="duotone" />
          </motion.div>
          <h2 className="text-2xl font-bold mb-2 bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
            Stellar Inventory
          </h2>
          <p className="text-muted-foreground">Inicializando sistema inteligente...</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/50 bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between gap-4">
            <motion.div 
              className="flex items-center gap-3"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="relative">
                <Sparkle size={32} className="text-primary" weight="duotone" />
                <motion.div
                  className="absolute inset-0"
                  animate={{ 
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 0, 0.5]
                  }}
                  transition={{ 
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                >
                  <Sparkle size={32} className="text-accent" weight="duotone" />
                </motion.div>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
                  Stellar Inventory
                </h1>
                <p className="text-sm text-muted-foreground">AI-Powered Management</p>
              </div>
            </motion.div>
            
            <div className="flex items-center gap-2">
              {currentUser && (
                <div className="flex items-center gap-2 mr-2 border-r pr-2 border-border/50">
                  <div className="flex flex-col items-end">
                    <span className="text-sm font-medium hidden md:inline-block">
                      {currentUser.full_name || currentUser.username}
                    </span>
                    <span className="text-xs text-muted-foreground hidden md:inline-block">
                      {currentUser.is_superuser ? 'Super Admin' : (currentUser.role?.name || 'Usuario')}
                    </span>
                  </div>
                  <Button variant="ghost" size="icon" onClick={handleLogout} title="Cerrar Sesión">
                    <Power size={20} className="text-destructive" />
                  </Button>
                </div>
              )}
              <SyncIndicator syncStatus={syncStatus} />
              
              <Badge variant={useAPI ? "default" : "secondary"} className="hidden sm:flex items-center gap-1">
                {useAPI ? <CloudArrowUp size={14} /> : <Database size={14} />}
                {useAPI ? 'API' : 'Local'}
              </Badge>
              
              <NotificationCenter
                products={products ?? []}
                profiles={profiles ?? []}
                locations={locations ?? []}
              />
              
              {canAccessAIOps && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setActiveTab('ai-ops')}
                  title="Ir a Centro IA"
                  className="relative hover:bg-accent/20"
                >
                  <Lightbulb size={20} weight="duotone" className="text-accent" />
                </Button>
              )}
              
              {canAccessAIOps && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setActiveTab('ai-ops')}
                  title="Ir a Centro IA"
                  className="relative hover:bg-primary/10 text-primary"
                >
                  <Robot size={20} />
                  {isAIStatusAvailable && aiAttentionCount > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[20px] h-5 bg-amber-500 text-white rounded-full text-[10px] flex items-center justify-center px-1 font-bold">
                      {aiAttentionCount > 99 ? '99+' : aiAttentionCount}
                    </span>
                  )}
                </Button>
              )}

              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowHealthCheckDialog(true)}
                title="Diagnóstico de Salud"
                className="relative hover:bg-primary/10"
              >
                <Pulse size={20} />
              </Button>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowKeyboardDialog(true)}
                title="Atajos de teclado (Shift + ?)"
                className="relative hover:bg-primary/10"
              >
                <Keyboard size={20} />
              </Button>
              
              {canViewSettings && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowSettingsDialog(true)}
                  title="Configuración (Ctrl + ,)"
                  className="hover:bg-primary/10"
                >
                  <Gear size={20} />
                </Button>
              )}
              
              {canManageUsers && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowManageUsersDialog(true)}
                  title="Gestionar Usuarios"
                  className="hover:bg-primary/10"
                >
                  <ShieldCheck size={20} />
                </Button>
              )}

              {canValidateDailyClose && useAPI && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowDailyCloseDialog(true)}
                  title="Cierre de Día — Validar Ventas"
                  className="hover:bg-emerald-100 dark:hover:bg-emerald-900/30 text-emerald-600"
                >
                  <CheckCircle size={20} weight="fill" />
                </Button>
              )}

              {canAccessMultiStoreControl && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowMultiStoreControl(true)}
                  title="Control Multitienda"
                  className="hover:bg-primary/10 text-primary"
                >
                  <Database size={20} />
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList className="grid w-full grid-cols-8 max-w-7xl mb-6">
            {canViewInventory && (
              <TabsTrigger value="products" className="flex items-center gap-2">
                <Package size={18} />
                <span className="hidden sm:inline">Productos</span>
              </TabsTrigger>
            )}
            {canViewReports && (
              <TabsTrigger value="charts" className="flex items-center gap-2">
                <ChartLine size={18} />
                <span className="hidden sm:inline">Gráficas</span>
              </TabsTrigger>
            )}
            {canAccessMultiStoreControl && (
              <TabsTrigger value="multistore-control" className="flex items-center gap-2">
                <Database size={18} />
                <span className="hidden sm:inline">Multitienda</span>
              </TabsTrigger>
            )}
            {canViewOrders && (
              <TabsTrigger value="orders" className="flex items-center gap-2">
                <ShoppingCart size={18} />
                <span className="hidden sm:inline">Órdenes</span>
              </TabsTrigger>
            )}
            
            {/* Solo mostrar Transferencias si tiene permiso de inventory:edit o es admin */}
            {canEditInventory && (
              <TabsTrigger value="transfers" className="flex items-center gap-2">
                <ArrowsLeftRight size={18} />
                <span className="hidden sm:inline">Transferencias</span>
              </TabsTrigger>
            )}

            {/* Solo mostrar Ubicaciones si tiene permiso locations:manage */}
            {canManageLocations && (
              <TabsTrigger value="locations" className="flex items-center gap-2">
                <MapPin size={18} />
                <span className="hidden sm:inline">Ubicaciones</span>
              </TabsTrigger>
            )}

            {/* Solo mostrar Canales si es admin */}
            {canViewSettings && (
              <TabsTrigger value="sales-profiles" className="flex items-center gap-2">
                <Robot size={18} />
                <span className="hidden sm:inline">Canales</span>
              </TabsTrigger>
            )}

            {/* Solo mostrar Financiamiento si es admin */}
            {canEditSettings && (
              <TabsTrigger value="financing" className="flex items-center gap-2">
                <CreditCard size={18} />
                <span className="hidden sm:inline">Financiamiento</span>
              </TabsTrigger>
            )}

            {canAccessAIOps && (
              <TabsTrigger value="ai-ops" className="flex items-center gap-2">
                <Robot size={18} />
                <span className="hidden sm:inline">Centro IA</span>
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="products" className="space-y-6">
            {/* V2.0: LowStockAlert filters by LOCATION */}
            <LowStockAlert
              products={products ?? []}
              locations={locations ?? []}
              onProductClick={setEditingProduct}
            />
            
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
              <div className="flex flex-col sm:flex-row gap-3 flex-1 w-full">
                <div className="relative flex-1 max-w-md">
                  <MagnifyingGlass size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Buscar productos..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>

                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Categoría" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas</SelectItem>
                    <SelectItem value="celular">Celulares</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex gap-2 w-full sm:w-auto">
                <Button
                  variant={bulkActionMode ? "default" : "outline"}
                  size="icon"
                  onClick={() => {
                    setBulkActionMode(!bulkActionMode)
                  }}
                  title="Modo selección múltiple"
                >
                  {bulkActionMode ? <CheckSquare size={18} /> : <Square size={18} />}
                </Button>
                {canViewReports && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowSalesHistoryDialog(true)}
                    title="Ver historial completo de ventas"
                  >
                    <ChartLine size={16} className="mr-2" />
                    Historial
                  </Button>
                )}
                {canViewReports && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleExportProducts}
                    title="Exportar a CSV"
                  >
                    <Download size={18} />
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setShowWarrantyCheck(true)}
                  title="Verificar Garantía"
                >
                  <ShieldCheck size={18} />
                </Button>
                
                {canCreateInventory && (
                  <>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setShowImportDialog(true)}
                      title="Importar desde CSV"
                    >
                      <Upload size={18} />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setShowSuppliersDialog(true)}
                      title="Gestionar Proveedores"
                    >
                      <UserIcon size={18} />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setShowPendingTradeIns(true)}
                      title="Retomas Pendientes"
                      className="text-amber-600 border-amber-200 hover:bg-amber-50"
                    >
                      <Wrench size={18} />
                    </Button>
                    <Button onClick={() => setShowNewProductDialog(true)} className="flex-1 sm:flex-none">
                      Nuevo Producto
                    </Button>
                    <Button variant="secondary" onClick={() => setShowRestockDialog(true)} className="flex-1 sm:flex-none">
                      Agregar más
                    </Button>
                  </>
                )}
              </div>
            </div>

            {bulkActionMode && selectedProducts.size > 0 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-4 bg-accent rounded-lg">
                <span className="text-sm font-medium">
                  {selectedProducts.size} producto{selectedProducts.size !== 1 ? 's' : ''} seleccionado{selectedProducts.size !== 1 ? 's' : ''}
                </span>
                <div className="flex gap-2 ml-auto">
                  {canEditInventory && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleBulkToggleProductStatus}
                    >
                      <Power size={16} className="mr-2" />
                      Cambiar Estado
                    </Button>
                  )}
                  {canDeleteInventory && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleBulkDeleteProducts}
                    >
                      <Trash size={16} className="mr-2" />
                      Eliminar
                    </Button>
                  )}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2 rounded-lg border p-1">
                <Button
                  variant={productViewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setProductViewMode('grid')}
                  className="gap-2"
                >
                  <SquaresFour size={16} />
                  Cuadrícula
                </Button>
                <Button
                  variant={productViewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setProductViewMode('list')}
                  className="gap-2"
                >
                  <Rows size={16} />
                  Lista
                </Button>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
              <input
                type="checkbox"
                id="show-inactive"
                checked={showInactive}
                onChange={(e) => setShowInactive(e.target.checked)}
                className="rounded"
              />
              <label htmlFor="show-inactive" className="text-sm text-muted-foreground cursor-pointer">
                Mostrar productos inactivos
              </label>
              {bulkActionMode && filteredProducts.length > 0 && (
                <>
                  <span className="mx-2 text-muted-foreground">|</span>
                  <button
                    onClick={selectAllProducts}
                    className="text-sm text-primary hover:underline cursor-pointer"
                  >
                    {selectedProducts.size === filteredProducts.length ? 'Deseleccionar todos' : 'Seleccionar todos'}
                  </button>
                </>
              )}
              </div>
            </div>

            {filteredProducts.length === 0 ? (
              <div className="text-center py-12">
                <Package size={64} className="mx-auto text-muted-foreground mb-4" weight="duotone" />
                <h3 className="text-lg font-semibold text-card-foreground mb-2">
                  No hay productos
                </h3>
                <p className="text-muted-foreground mb-4">
                  Comienza agregando tu primer producto al inventario
                </p>
                {canCreateInventory && (
                  <Button onClick={() => setShowNewProductDialog(true)}>
                    <Plus size={18} className="mr-2" />
                    Agregar Producto
                  </Button>
                )}
              </div>
            ) : productViewMode === 'list' ? (
              <div className="space-y-3">
                {filteredProducts.map(product => (
                  <div key={product.id} className="relative rounded-xl border bg-card p-4 shadow-sm transition-shadow hover:shadow-md">
                    {bulkActionMode && (
                      <div className="absolute top-3 left-3 z-10">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleProductSelection(product.id)
                          }}
                          className="w-6 h-6 rounded bg-background border-2 border-primary flex items-center justify-center hover:bg-accent transition-colors"
                        >
                          {selectedProducts.has(product.id) && (
                            <CheckCircle size={20} weight="fill" className="text-primary" />
                          )}
                        </button>
                      </div>
                    )}

                    <div className={`grid gap-4 ${bulkActionMode ? 'pl-10' : ''} lg:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)_auto] items-start`}>
                      <div className="min-w-0 space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-lg truncate">{product.nombre}</h3>
                          <Badge variant="outline">{product.categoria === 'celular' ? 'Celular' : 'Accesorio'}</Badge>
                          {!product.activo && <Badge variant="outline">Inactivo</Badge>}
                          {product.is_serialized && <Badge className="bg-blue-600 text-white">Serializado</Badge>}
                        </div>
                        <div className="text-sm text-muted-foreground flex flex-wrap gap-x-4 gap-y-1">
                          <span>SKU: {product.sku || 'N/A'}</span>
                          <span>Marca: {product.marca || 'N/A'}</span>
                          <span>Modelo: {product.modelo || 'N/A'}</span>
                          <span>Capacidad: {product.capacidad || 'N/A'}</span>
                          <span>Condición: {product.condicion || 'N/A'}</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <p className="text-muted-foreground">Precio</p>
                          <p className="font-semibold text-primary">{product.moneda} {product.precio.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Stock</p>
                          <Badge variant={product.stock_disponible > 0 ? 'default' : 'secondary'}>
                            {product.stock_disponible} unidades
                          </Badge>
                        </div>
                        <div className="col-span-2 text-xs text-muted-foreground">
                          Garantía: {product.garantia_meses > 0 ? `${product.garantia_meses} meses` : 'Sin garantía'}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {canEditInventory && (
                          <Button variant="outline" size="sm" onClick={() => setEditingProduct(product)}>
                            Editar
                          </Button>
                        )}
                        {canEditInventory && (
                          <Button variant="outline" size="sm" onClick={() => setTransferringProduct(product)}>
                            Transferir
                          </Button>
                        )}
                        <Button variant="outline" size="sm" onClick={() => setViewingProductHistory(product)}>
                          Historial
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredProducts.map(product => (
                  <div key={product.id} className="relative">
                    {bulkActionMode && (
                      <div className="absolute top-3 left-3 z-10">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleProductSelection(product.id)
                          }}
                          className="w-6 h-6 rounded bg-background border-2 border-primary flex items-center justify-center hover:bg-accent transition-colors"
                        >
                          {selectedProducts.has(product.id) && (
                            <CheckCircle size={20} weight="fill" className="text-primary" />
                          )}
                        </button>
                      </div>
                    )}
                    <ProductCard
                      product={product}
                      onEdit={canEditInventory ? setEditingProduct : undefined}
                      onTransfer={canEditInventory ? setTransferringProduct : undefined}
                      onViewHistory={setViewingProductHistory}
                      onToggleActive={canEditInventory ? async (p) => {
                        const updated = await service.updateProduct(p.id, { ...p, activo: !p.activo })
                        setProducts((current: ProductWithStock[]) => (current ?? []).map(pr => pr.id === updated.id ? updated : pr))
                        toast.success(`Producto ${updated.activo ? 'activado' : 'desactivado'}`)
                      } : undefined}
                      onDelete={canDeleteInventory ? async (p) => {
                        if (!confirm(`¿Estás seguro de eliminar "${p.nombre}"?\n\nEsta acción no se puede deshacer.`)) {
                          return
                        }

                        try {
                          await service.deleteProduct(p.id)
                          setProducts((current: ProductWithStock[]) => (current ?? []).filter(pr => pr.id !== p.id))
                          toast.success('Producto eliminado exitosamente')
                        } catch (error) {
                          const message = error instanceof Error ? error.message : 'Error desconocido'

                          if (message.includes('referenciado') || message.includes('orders') || message.includes('históricas')) {
                             console.log('Delete prevented due to existing references (expected behavior)')

                             if (confirm(`No se puede eliminar el producto "${p.nombre}" porque tiene historial de ventas.\n\n¿Deseas desactivarlo en su lugar para que no aparezca en nuevas ventas?`)) {
                                try {
                                    const updated = await service.updateProduct(p.id, { ...p, activo: false })
                                    setProducts((current: ProductWithStock[]) => (current ?? []).map(pr => pr.id === updated.id ? updated : pr))
                                    toast.success('Producto desactivado correctamente')
                                } catch (updateError) {
                                    console.error('Error deactivating product:', updateError)
                                    toast.error('Error al desactivar producto')
                                }
                             }
                          } else {
                              console.error('Error deleting product:', error)
                              toast.error(`Error al eliminar producto: ${message}`)
                          }
                        }
                      } : undefined}
                    />
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="multistore-control" className="space-y-6">
            <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,0.9fr)] gap-6">
              <div className="space-y-6">
                <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-card via-card to-primary/5">
                  <CardHeader className="space-y-3">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <CardTitle className="flex items-center gap-2 text-xl">
                          <Database size={22} className="text-primary" weight="duotone" />
                          Control Multitienda
                        </CardTitle>
                        <CardDescription className="mt-1 max-w-2xl">
                          Centro operativo para recepciones, conteos físicos, cierres de caja, conciliación bancaria,
                          accesos por ubicación y auditoría distribuida.
                        </CardDescription>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary">{activeLocations.length} ubicaciones activas</Badge>
                        <Badge variant="outline">{productsWithLocationTracking.length} productos trazados</Badge>
                        <Badge variant="outline">{locatedOrders} órdenes con origen</Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                      <div className="rounded-xl border bg-background/80 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Ubicaciones activas</p>
                        <p className="mt-2 text-3xl font-semibold">{activeLocations.length}</p>
                        <p className="mt-1 text-sm text-muted-foreground">Tiendas, bodegas y oficinas operativas.</p>
                      </div>
                      <div className="rounded-xl border bg-background/80 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Unidades trazadas</p>
                        <p className="mt-2 text-3xl font-semibold">{totalTrackedUnits.toLocaleString('es-HN')}</p>
                        <p className="mt-1 text-sm text-muted-foreground">Stock consolidado entre ubicaciones.</p>
                      </div>
                      <div className="rounded-xl border bg-background/80 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Productos sin stock</p>
                        <p className="mt-2 text-3xl font-semibold">{outOfStockProducts}</p>
                        <p className="mt-1 text-sm text-muted-foreground">Catálogo con oportunidad de reposición.</p>
                      </div>
                      <div className="rounded-xl border bg-background/80 p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Órdenes ubicadas</p>
                        <p className="mt-2 text-3xl font-semibold">{locatedOrders}</p>
                        <p className="mt-1 text-sm text-muted-foreground">Ventas registradas con ubicación de origen.</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      <Card className="border-border/70 bg-background/70">
                        <CardHeader>
                          <CardTitle className="text-base">Flujos operativos</CardTitle>
                          <CardDescription>Entrá directo al proceso que necesitás ejecutar.</CardDescription>
                        </CardHeader>
                        <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {(canViewInventory || canManagePurchases) && (
                            <Button variant="outline" className="justify-start h-auto py-3" onClick={() => openMultiStoreSection('receipts')}>
                              <Package size={18} className="mr-2" />
                              Recepciones y entradas
                            </Button>
                          )}
                          {(canViewInventory || canCountInventory || canAdjustInventory) && (
                            <Button variant="outline" className="justify-start h-auto py-3" onClick={() => openMultiStoreSection('counts')}>
                              <CheckSquare size={18} className="mr-2" />
                              Conteos y ajustes
                            </Button>
                          )}
                          {canManageCashCloses && (
                            <Button variant="outline" className="justify-start h-auto py-3" onClick={() => openMultiStoreSection('closes')}>
                              <CreditCard size={18} className="mr-2" />
                              Cierres por tienda
                            </Button>
                          )}
                          {canViewReports && (
                            <Button variant="outline" className="justify-start h-auto py-3" onClick={() => openMultiStoreSection('bank')}>
                              <ChartLine size={18} className="mr-2" />
                              Conciliación bancaria
                            </Button>
                          )}
                          {canManageLocationAccess && (
                            <Button variant="outline" className="justify-start h-auto py-3" onClick={() => openMultiStoreSection('access')}>
                              <ShieldCheck size={18} className="mr-2" />
                              Accesos por ubicación
                            </Button>
                          )}
                          {canViewAudit && (
                            <Button variant="outline" className="justify-start h-auto py-3" onClick={() => openMultiStoreSection('audit')}>
                              <Database size={18} className="mr-2" />
                              Bitácora y auditoría
                            </Button>
                          )}
                        </CardContent>
                      </Card>

                      <Card className="border-border/70 bg-background/70">
                        <CardHeader>
                          <CardTitle className="text-base">Cobertura por ubicación</CardTitle>
                          <CardDescription>Resumen rápido de las ubicaciones con mayor carga operativa.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {locationSnapshots.length > 0 ? locationSnapshots.map(location => (
                            <div key={location.id} className="rounded-lg border p-3 flex items-center justify-between gap-3">
                              <div>
                                <p className="font-medium">{location.nombre}</p>
                                <p className="text-sm text-muted-foreground capitalize">{location.tipo}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-medium">{location.unitsAtLocation.toLocaleString('es-HN')} uds</p>
                                <p className="text-xs text-muted-foreground">{location.productsAtLocation} productos con stock</p>
                              </div>
                            </div>
                          )) : (
                            <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                              Aún no hay suficiente información de ubicaciones para construir este resumen.
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Visión del módulo</CardTitle>
                    <CardDescription>Qué resuelve esta área dentro del sistema.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4 text-sm text-muted-foreground">
                    <div className="rounded-lg border p-3">
                      <p className="font-medium text-foreground">Inventario por sede</p>
                      <p className="mt-1">Permite recibir compras, contar físico vs sistema y ajustar diferencias con trazabilidad.</p>
                    </div>
                    <div className="rounded-lg border p-3">
                      <p className="font-medium text-foreground">Caja y bancos</p>
                      <p className="mt-1">Centraliza cierres diarios por tienda y conciliación de transferencias bancarias.</p>
                    </div>
                    <div className="rounded-lg border p-3">
                      <p className="font-medium text-foreground">Gobierno operativo</p>
                      <p className="mt-1">Administra accesos por ubicación y consulta la bitácora de acciones críticas.</p>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Acción principal</CardTitle>
                    <CardDescription>Abrí el panel completo del módulo con todas las pestañas habilitadas para tu rol.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button onClick={() => openMultiStoreSection(multiStoreInitialTab || 'receipts')} className="w-full gap-2">
                      <Database size={18} />
                      Abrir Panel Multitienda
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {canAccessAIOps && (
          <TabsContent value="ai-ops" className="space-y-6">
            <DashboardStats
              products={products ?? []}
              orders={orders ?? []}
              currentUser={currentUser}
              onViewLowStockReport={() => setShowLowStockReport(true)}
              insightsOnly
            />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <div className="rounded-xl border border-border bg-card p-4 sm:p-6">
                  <h3 className="text-lg font-semibold mb-1">Centro IA Operativo</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Herramientas de IA y monitoreo operativo disponibles para Super Admin.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Button variant="outline" onClick={() => setShowAIStatusDialog(true)} disabled={!isAIStatusAvailable} className="justify-start">
                      <ChartLine size={18} className="mr-2" />
                      Panel IA
                    </Button>

                    <Button variant="outline" onClick={() => setShowOptimizationDialog(true)} className="justify-start">
                      <Lightbulb size={18} className="mr-2" />
                      Insights de Optimización
                    </Button>

                    <Button variant="outline" onClick={() => setShowForecastingDialog(true)} className="justify-start">
                      <Sparkle size={18} className="mr-2" />
                      Pronóstico de Ventas IA
                    </Button>

                    <Button variant="outline" onClick={() => setShowAITraining(true)} className="justify-start text-blue-600 border-blue-200 hover:bg-blue-50">
                      <GraduationCap size={18} className="mr-2" />
                      Centro de Entrenamiento
                    </Button>

                    <Button variant="outline" onClick={() => setShowCustomerInsights(true)} className="justify-start text-purple-600 border-purple-200 hover:bg-purple-50">
                      <ShieldCheck size={18} className="mr-2" />
                      Insights de Clientes
                    </Button>

                    <Button variant="outline" onClick={() => setShowAIChatOrchestrator(true)} className="justify-start text-emerald-600 border-emerald-200 hover:bg-emerald-50">
                      <Robot size={18} className="mr-2" />
                      Chat IA Operativo
                    </Button>

                    <Button variant="outline" onClick={() => setShowPhotoRequestsDialog(true)} className="justify-start text-violet-600 border-violet-200 hover:bg-violet-50">
                      <Camera size={18} className="mr-2" />
                      Solicitudes de fotos {photoRequestPendingCount > 0 ? `(${photoRequestPendingCount})` : ''}
                    </Button>

                    <Button
                      variant="outline"
                      onClick={() => setShowChannelHealthDialog(true)}
                      className="justify-start text-sky-600 border-sky-200 hover:bg-sky-50 sm:col-span-2"
                    >
                      <CloudArrowUp size={18} className="mr-2" />
                      Diagnóstico de Canales {channelHealthReady === null ? '(estado desconocido)' : channelHealthReady ? '(ready)' : '(incompleto)'}
                    </Button>
                  </div>
                </div>
              </div>

              <div>
                <div className="space-y-6">
                  <ForecastingWidget
                    summary={forecastingSummary ?? null}
                    criticalAlerts={getCriticalAlerts()}
                    lastUpdated={forecastingLastUpdated ?? null}
                    isGenerating={isForecastingGenerating}
                    onViewDetails={() => setShowForecastingDialog(true)}
                    onRefresh={generateForecastData}
                  />
                  <AIStatusWidget
                    status={aiStatus}
                    isLoading={isAIStatusLoading}
                    error={aiStatusError}
                    isApiMode={isAIStatusAvailable}
                    onRefresh={refreshAIStatus}
                    onOpenDetails={() => setShowAIStatusDialog(true)}
                  />
                </div>
              </div>
            </div>
          </TabsContent>
          )}

          {canViewReports && (
            <TabsContent value="charts" className="space-y-6">
              <DashboardStats
                products={products ?? []}
                orders={orders ?? []}
                currentUser={currentUser}
                onViewLowStockReport={() => setShowLowStockReport(true)}
                showInsights={false}
                chartsOnly
              />
            </TabsContent>
          )}

          {canViewOrders && (
          <TabsContent value="orders" className="space-y-6">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
              <div className="flex flex-col sm:flex-row gap-3 flex-1 w-full">
                <div className="relative flex-1 max-w-md">
                  <MagnifyingGlass size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Buscar por cliente o teléfono..."
                    value={customerSearchTerm}
                    onChange={(e) => setCustomerSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>

                {/* V2.0: Sales Channel selector - filters orders/reports by channel */}
                <Select value={selectedSalesChannel} onValueChange={setSelectedSalesChannel}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Canal de Ventas" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los canales</SelectItem>
                    {channelOptions.map(profile => (
                      <SelectItem key={profile.id} value={profile.slug}>
                        {profile.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={orderStatusFilter} onValueChange={setOrderStatusFilter}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Estado" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="pendiente">Pendiente</SelectItem>
                    <SelectItem value="por_entregar">Por Entregar</SelectItem>
                    <SelectItem value="completada">Completada</SelectItem>
                    <SelectItem value="validada">Validada</SelectItem>
                    <SelectItem value="cancelada">Cancelada</SelectItem>
                  </SelectContent>
                </Select>

                <div className="flex gap-2">
                  <Input
                    type="date"
                    value={orderDateFrom}
                    onChange={(e) => setOrderDateFrom(e.target.value)}
                    placeholder="Desde"
                    className="w-full sm:w-[140px]"
                  />
                  <Input
                    type="date"
                    value={orderDateTo}
                    onChange={(e) => setOrderDateTo(e.target.value)}
                    placeholder="Hasta"
                    className="w-full sm:w-[140px]"
                  />
                </div>
              </div>

              <div className="flex gap-2 w-full sm:w-auto">
                <Button
                  variant={advancedFilters ? "default" : "outline"}
                  size="icon"
                  onClick={() => setShowAdvancedSearch(true)}
                  title="Búsqueda avanzada"
                >
                  <FunnelSimple size={18} />
                </Button>
                {canViewReports && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      const currentProfile = selectedSalesChannel !== 'all' 
                        ? (profiles ?? []).find(p => p.slug === selectedSalesChannel)
                        : (profiles ?? [])[0]
                      
                      if (currentProfile) {
                        setShowReportsDialog(true)
                      } else {
                        toast.error('Selecciona un perfil primero')
                      }
                    }}
                    title="Ver reportes"
                  >
                    <ChartLine size={18} />
                  </Button>
                )}
                {canEditOrders && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setShowReturnsListDialog(true)}
                    title="Ver devoluciones"
                  >
                    <ArrowCounterClockwise size={18} />
                  </Button>
                )}
                <Button
                  variant={bulkActionMode && activeTab === 'orders' ? "default" : "outline"}
                  size="icon"
                  onClick={() => {
                    setBulkActionMode(!bulkActionMode)
                    setSelectedOrders(new Set())
                  }}
                  title="Modo selección múltiple"
                >
                  {bulkActionMode && activeTab === 'orders' ? <CheckSquare size={18} /> : <Square size={18} />}
                </Button>
                {canViewReports && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleExportOrders}
                    title="Exportar a CSV"
                  >
                    <Download size={18} />
                  </Button>
                )}
                {canCreateOrders && (
                <Button onClick={() => setShowNewOrderDialog(true)} className="flex-1 sm:flex-none">
                  <Plus size={18} className="mr-2" />
                  Nueva Orden
                </Button>
                )}
              </div>
            </div>

            {bulkActionMode && activeTab === 'orders' && selectedOrders.size > 0 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-4 bg-accent rounded-lg">
                <span className="text-sm font-medium">
                  {selectedOrders.size} orden{selectedOrders.size !== 1 ? 'es' : ''} seleccionada{selectedOrders.size !== 1 ? 's' : ''}
                </span>
                <div className="flex flex-wrap gap-2 sm:ml-auto">
                  {canEditOrders && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleBulkUpdateOrderStatus('pendiente')}
                      >
                        Pendiente
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleBulkUpdateOrderStatus('por_entregar')}
                      >
                        Por Entregar
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleBulkUpdateOrderStatus('completada')}
                      >
                        <CheckCircle size={16} className="mr-2" />
                        Completar
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleBulkUpdateOrderStatus('cancelada')}
                      >
                        <XCircle size={16} className="mr-2" />
                        Cancelar
                      </Button>
                    </>
                  )}
                  {canDeleteOrders && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleBulkDeleteOrders}
                    >
                      <Trash size={16} className="mr-2" />
                      Eliminar
                    </Button>
                  )}
                </div>
              </div>
            )}

            {bulkActionMode && activeTab === 'orders' && filteredOrders.length > 0 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={selectAllOrders}
                  className="text-sm text-primary hover:underline cursor-pointer"
                >
                  {selectedOrders.size === filteredOrders.length ? 'Deseleccionar todas' : 'Seleccionar todas'}
                </button>
              </div>
            )}

            {filteredOrders.length === 0 ? (
              <div className="text-center py-12">
                <ShoppingCart size={64} className="mx-auto text-muted-foreground mb-4" weight="duotone" />
                <h3 className="text-lg font-semibold text-card-foreground mb-2">
                  No hay órdenes
                </h3>
                <p className="text-muted-foreground mb-4">
                  Crea tu primera orden de venta
                </p>
                {canCreateOrders && (
                  <Button onClick={() => setShowNewOrderDialog(true)}>
                    <Plus size={18} className="mr-2" />
                    Crear Orden
                  </Button>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-4 max-w-4xl mx-auto">
                {filteredOrders.map(order => (
                  <div key={order.id} className="relative">
                    {bulkActionMode && activeTab === 'orders' && (
                      <div className="absolute top-3 left-3 z-10">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleOrderSelection(order.id)
                          }}
                          className="w-6 h-6 rounded bg-background border-2 border-primary flex items-center justify-center hover:bg-accent transition-colors"
                        >
                          {selectedOrders.has(order.id) && (
                            <CheckCircle size={20} weight="fill" className="text-primary" />
                          )}
                        </button>
                      </div>
                    )}
                    <OrderCard
                      order={order}
                      onStatusChange={canEditOrders ? async (orderId, newStatus) => {
                        console.log(`🔄 Cambiando estado de orden ${orderId} a: ${newStatus}`)
                        const validationCode = await getCompletionValidationCode(newStatus)
                        if (validationCode === null) return

                        const updated = await service.updateOrderStatus(orderId, newStatus, validationCode)
                        console.log('✅ Orden actualizada:', updated)
                        setOrders((current: OrderWithItems[]) => (current ?? []).map(o => o.id === updated.id ? updated : o))
                        toast.success('Estado de orden actualizado')
                        
                        // Recargar productos para reflejar cambios en stock
                        console.log('🔄 Recargando productos después de cambio de estado...')
                        const updatedProducts = await service.getProducts()
                        setProducts(updatedProducts)
                      } : undefined}
                      onEdit={canEditOrders ? setEditingOrder : undefined}
                      onViewCustomerHistory={(phone) => {
                        setSelectedCustomerPhone(phone)
                        setShowCustomerHistory(true)
                      }}
                      onExportPDF={(order) => {
                        // V2.0 FIX: Soporte para órdenes sin perfil legacy (basadas en ubicación)
                        let profile = (profiles ?? []).find(p => p.id === order.profile_id)
                        
                        if (!profile && order.source_location_id) {
                          const location = (locations ?? []).find(l => l.id === order.source_location_id)
                          if (location) {
                            // Construir perfil temporal basado en la ubicación
                            profile = {
                              id: 0,
                              slug: `location-${location.id}`,
                              name: location.nombre,
                              type: 'tienda',
                              theme: { primary: '#4f46e5', secondary: '#ffffff' },
                              settings: {
                                address: location.direccion || '',
                                phone: '',
                                footer_text: 'Gracias por su preferencia'
                              }
                            } as any
                          }
                        }

                        // Fallback final
                        if (!profile) {
                           profile = {
                              id: 0,
                              slug: 'default',
                              name: 'Mi Negocio',
                              type: 'tienda',
                              theme: { primary: '#4f46e5', secondary: '#ffffff' },
                              settings: {}
                           } as any
                        }

                        if (profile) {
                          generateOrderPDF(order, profile)
                        }
                      }}
                      onDelete={canDeleteOrders ? async (order) => {
                        console.log('🗑️ Intentando eliminar orden:', order.id)
                        if (!confirm(`¿Estás seguro de eliminar la orden #${order.id}?\n\nEsta acción no se puede deshacer y se repondrá el stock de los productos.`)) {
                          console.log('❌ Eliminación cancelada por el usuario')
                          return
                        }
                        try {
                          console.log('📡 Llamando a service.deleteOrder...')
                          await service.deleteOrder(order.id)
                          console.log('✅ Orden eliminada del backend, actualizando estado local...')
                          setOrders((current: OrderWithItems[]) => (current ?? []).filter(o => o.id !== order.id))
                          toast.success('Orden eliminada exitosamente')
                        } catch (error) {
                          const message = error instanceof Error ? error.message : 'Error desconocido'
                          
                          if (message.includes('completada') || message.includes('cancelar')) {
                              console.log('Delete prevented for completed order (expected behavior)')
                              if (confirm(`No se puede eliminar una orden completada.\n\n¿Deseas cancelarla en su lugar? Esto repondrá el stock automáticamente.`)) {
                                  try {
                                      const cancelledOrder = await service.cancelOrder(order.id, 'Cancelación solicitada por usuario al intentar eliminar')
                                      setOrders((current: OrderWithItems[]) => (current ?? []).map(o => o.id === cancelledOrder.id ? cancelledOrder : o))
                                      toast.success('Orden cancelada exitosamente')
                                  } catch (cancelError) {
                                      console.error('Error cancelling order:', cancelError)
                                      toast.error('Error al cancelar orden')
                                  }
                              }
                          } else {
                              console.error('❌ Error al eliminar orden:', error)
                              toast.error(`Error al eliminar orden: ${message}`)
                          }
                        }
                      } : undefined}
                    />
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
          )}

          <TabsContent value="locations" className="space-y-6">
            <LocationsList />
          </TabsContent>

          <TabsContent value="transfers" className="space-y-6">
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold">Transferencias de Stock</h2>
                  <p className="text-muted-foreground">Transfiere inventario entre ubicaciones (tiendas/bodegas)</p>
                </div>
                <Button
                  variant="default"
                  onClick={() => setShowTransferListDialog(true)}
                  className="gap-2"
                >
                  <Package size={20} />
                  Ver Transferencias
                </Button>
              </div>

              <div className="rounded-lg border p-4 space-y-3">
                <h3 className="font-semibold">Nueva transferencia rápida</h3>
                <p className="text-sm text-muted-foreground">
                  Elige el origen, el destino y el producto; luego haz clic en <strong>Iniciar transferencia</strong>.
                </p>

                {/* Fila 1: Origen → Destino */}
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1">
                      <MapPin size={12} weight="fill" /> Ubicación de origen
                    </p>
                    <Select
                      value={transferOriginFilter}
                      onValueChange={(value) => {
                        setTransferOriginFilter(value)
                        setQuickTransferProductId('')
                        setQuickTransferSearchTerm('')
                        setQuickTransferProductOpen(false)
                        if (value !== 'all' && value === quickTransferToLocationId) setQuickTransferToLocationId('all')
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona origen" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Cualquier ubicación</SelectItem>
                        {(locations ?? [])
                          .filter(location => location.activo)
                          .sort((a, b) => a.nombre.localeCompare(b.nombre))
                          .map(location => (
                            <SelectItem key={location.id} value={String(location.id)}>
                              {location.nombre}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1">
                      <MapPin size={12} weight="fill" /> Ubicación de destino
                    </p>
                    <Select
                      value={quickTransferToLocationId}
                      onValueChange={(value) => {
                        setQuickTransferToLocationId(value)
                        setQuickTransferProductOpen(false)
                        if (value !== 'all' && value === transferOriginFilter) setTransferOriginFilter('all')
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona destino" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Cualquier ubicación</SelectItem>
                        {(locations ?? [])
                          .filter(location => location.activo)
                          .sort((a, b) => a.nombre.localeCompare(b.nombre))
                          .map(location => (
                            <SelectItem key={location.id} value={String(location.id)}>
                              {location.nombre}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Indicador visual cuando se seleccionan ambas */}
                {transferOriginFilter !== 'all' && quickTransferToLocationId !== 'all' && (
                  <div className="flex items-center gap-2 text-sm bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-2">
                    <MapPin size={14} weight="fill" className="text-blue-600 shrink-0" />
                    <span className="font-medium text-blue-900 dark:text-blue-100">
                      {(locations ?? []).find(l => String(l.id) === transferOriginFilter)?.nombre}
                    </span>
                    <ArrowsLeftRight size={14} weight="bold" className="text-blue-500 shrink-0" />
                    <MapPin size={14} weight="fill" className="text-blue-600 shrink-0" />
                    <span className="font-medium text-blue-900 dark:text-blue-100">
                      {(locations ?? []).find(l => String(l.id) === quickTransferToLocationId)?.nombre}
                    </span>
                  </div>
                )}

                {/* Fila 2: Producto + Botón */}
                <div className="grid gap-3 sm:grid-cols-[1fr_auto] items-end">
                  <div className="space-y-1">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Producto a transferir
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {filteredTransferProducts.length} producto(s) encontrado(s)
                    </p>
                    <Popover open={quickTransferProductOpen} onOpenChange={setQuickTransferProductOpen}>
                      <PopoverTrigger asChild>
                        <Button
                          type="button"
                          variant="outline"
                          role="combobox"
                          aria-expanded={quickTransferProductOpen}
                          className="w-full justify-between font-normal"
                        >
                          <span className="truncate text-left">
                            {selectedQuickTransferProduct
                              ? `${selectedQuickTransferProduct.nombre} · ${selectedQuickTransferProduct.sku} · ${getTransferAvailableStock(selectedQuickTransferProduct, transferOriginFilter)} uds`
                              : 'Buscar y seleccionar producto'}
                          </span>
                          <CaretUpDown size={16} className="ml-2 shrink-0 opacity-50" />
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
                        <Command shouldFilter={false}>
                          <CommandInput
                            value={quickTransferSearchTerm}
                            onValueChange={(value) => {
                              setQuickTransferSearchTerm(value)
                              setQuickTransferProductId('')
                            }}
                            placeholder="Buscar por nombre, marca, modelo o SKU..."
                          />
                          <CommandList>
                            <CommandEmpty>No se encontraron productos.</CommandEmpty>
                            {filteredTransferProducts.map(product => (
                              <CommandItem
                                key={product.id}
                                value={String(product.id)}
                                onSelect={() => {
                                  setQuickTransferProductId(String(product.id))
                                  setQuickTransferSearchTerm('')
                                  setQuickTransferProductOpen(false)
                                }}
                              >
                                <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
                                  <div className="min-w-0">
                                    <p className="truncate font-medium">{product.nombre}</p>
                                    <p className="truncate text-xs text-muted-foreground">
                                      {product.marca || 'Sin marca'} {product.modelo || ''} · SKU: {product.sku || 'Sin SKU'}
                                    </p>
                                  </div>
                                  <Badge variant="secondary" className="shrink-0">
                                    {getTransferAvailableStock(product, transferOriginFilter)} uds
                                  </Badge>
                                </div>
                                {quickTransferProductId === String(product.id) && (
                                  <CheckCircle size={16} weight="fill" className="ml-auto text-primary" />
                                )}
                              </CommandItem>
                            ))}
                          </CommandList>
                        </Command>
                      </PopoverContent>
                    </Popover>
                  </div>

                  <Button
                    onClick={() => {
                      const selected = (products ?? []).find(p => String(p.id) === quickTransferProductId)
                      if (!selected) {
                        toast.error('Selecciona un producto para transferir')
                        return
                      }
                      setTransferringProduct(selected)
                    }}
                    disabled={!canEditInventory || !quickTransferProductId}
                    className="gap-2"
                  >
                    <ArrowsLeftRight size={18} weight="bold" />
                    Iniciar transferencia
                  </Button>
                </div>
              </div>

              {/* Instrucciones mejoradas */}
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
                  <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                    <ArrowsLeftRight size={20} weight="bold" />
                    Cómo hacer una transferencia:
                  </h3>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
                    <li>Elige la <strong>ubicación de origen</strong> (de dónde sale el stock)</li>
                    <li>Elige la <strong>ubicación de destino</strong> (a dónde llega el stock)</li>
                    <li>Selecciona el <strong>producto</strong> a mover</li>
                    <li>Haz clic en <strong>Iniciar transferencia</strong></li>
                    <li>Confirma la cantidad y (si aplica) escanea los IMEIs</li>
                    <li>En recepción, confirma la llegada para completar la transferencia</li>
                    <li>Da seguimiento en <strong>Ver Transferencias</strong></li>
                  </ol>
                </div>

                <div className="rounded-lg border border-green-200 bg-green-50/50 p-4">
                  <h3 className="font-semibold text-green-900 mb-2 flex items-center gap-2">
                    <MapPin size={20} weight="bold" />
                    Gestión de stock por ubicación:
                  </h3>
                  <ul className="space-y-2 text-sm text-green-800">
                    <li className="flex items-start gap-2">
                      <span className="text-green-600">✓</span>
                      <span>Cada producto puede tener stock en múltiples ubicaciones</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-green-600">✓</span>
                      <span>Las transferencias mueven inventario entre tiendas y bodegas</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-green-600">✓</span>
                      <span>El stock total es la suma de todas las ubicaciones</span>
                    </li>
                  </ul>
                </div>
              </div>

              {/* Lista de productos con stock por ubicación */}
              <div className="grid gap-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold">Productos con Inventario Multi-Ubicación</h3>
                  <Badge variant="secondary">
                    {transferProducts.filter(p => (p.stock_items?.length || 0) > 1).length} productos en múltiples ubicaciones
                  </Badge>
                </div>
                
                {transferProducts.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground border rounded-lg bg-muted/20">
                    <ArrowsLeftRight size={48} className="mx-auto mb-4 opacity-50" weight="duotone" />
                    <p className="font-medium">No hay productos transferibles con el filtro actual</p>
                    <p className="text-sm mt-2">Prueba otra ubicación de origen o asigna stock a una tienda/bodega</p>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {transferProducts
                      .sort((a, b) => (b.stock_items?.length || 0) - (a.stock_items?.length || 0)) // Ordenar por cantidad de ubicaciones
                      .map(product => (
                        <div key={product.id} className="rounded-lg border p-4 hover:shadow-md transition-shadow">
                          <div className="flex justify-between items-start mb-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="font-semibold">{product.nombre}</h4>
                                {(product.stock_items?.length || 0) > 1 && (
                                  <Badge variant="default" className="text-xs">
                                    {product.stock_items?.length} ubicaciones
                                  </Badge>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground">SKU: {product.sku}</p>
                            </div>
                            <div className="text-right">
                              <Badge variant="outline" className="text-base px-3 py-1">
                                {product.stock_disponible} unidades
                              </Badge>
                              <p className="text-xs text-muted-foreground mt-1">Total</p>
                            </div>
                          </div>
                          
                          <div className="grid gap-2 mb-3">
                            <p className="text-sm font-medium flex items-center gap-1">
                              <MapPin size={14} weight="fill" />
                              Desglose por ubicación:
                            </p>
                            <div className="grid gap-1.5">
                              {product.stock_items?.map((stockItem) => {
                                const location = locations.find(l => l.id === stockItem.location_id)
                                // 🔒 BUG #33 FIX: Validar que stock sea >= 0
                                const stockLibre = Math.max(0, (stockItem.cantidad_disponible || 0) - (stockItem.cantidad_reservada || 0))
                                return (
                                  <div 
                                    key={stockItem.location_id} 
                                    className="flex justify-between items-center text-sm bg-muted/50 p-2.5 rounded hover:bg-muted transition-colors"
                                  >
                                    <span className="flex items-center gap-2">
                                      <MapPin size={14} weight="fill" className="text-primary" />
                                      <span className="font-medium">{location?.nombre || `Ubicación ${stockItem.location_id}`}</span>
                                      <Badge variant="secondary" className="text-xs capitalize">
                                        {location?.tipo}
                                      </Badge>
                                    </span>
                                    <div className="flex flex-col items-end gap-0.5">
                                      <Badge variant={stockItem.cantidad_disponible > 0 ? 'default' : 'secondary'}>
                                        {stockItem.cantidad_disponible} uds
                                      </Badge>
                                      {stockItem.cantidad_reservada > 0 && (
                                        <span className="text-xs text-amber-600">
                                          ({stockItem.cantidad_reservada} reservadas | {stockLibre} libres)
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                          
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full"
                            onClick={() => setTransferringProduct(product)}
                          >
                            <ArrowsLeftRight size={16} className="mr-2" weight="bold" />
                            Transferir Stock
                          </Button>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="sales-profiles" className="space-y-6">
            <SalesProfilesList onUpdate={async () => {
              const updated = await service.getSalesProfiles()
              setSalesProfiles(updated)
            }} canManageAI={canAccessAIOps} canManageTechnicalChannels={currentUser?.is_superuser === true} />
          </TabsContent>

          <TabsContent value="financing" className="space-y-6">
            <div className="bg-card rounded-lg border shadow-sm p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-primary/10 rounded-full text-primary">
                  <CreditCard size={24} />
                </div>
                <div>
                  <h2 className="text-xl font-semibold">Configuración de Financiamiento</h2>
                  <p className="text-sm text-muted-foreground">Gestiona los bancos y tasas para extrafinanciamiento y tarjetas</p>
                </div>
              </div>
              <FinancingSettings />
            </div>
          </TabsContent>
        </Tabs>
      </main>

      <NewProductDialog
        open={showNewProductDialog}
        onOpenChange={setShowNewProductDialog}
        profiles={activeProfiles}
        locations={locations.filter(l => l.activo)}
        onSubmit={async (newProduct, stock, locationId) => {
          try {
            console.log('📦 Creando producto V2.0:', { newProduct, stock, locationId })
            
            const productWithStock = { ...newProduct, activo: true, stock_disponible: stock }
            const created = await service.createProduct(productWithStock, locationId)
            
            console.log('✅ Producto creado en backend:', created)
            
            // Pequeña pausa para asegurar que el backend procesó la petición
            await new Promise(resolve => setTimeout(resolve, 300))
            
            // Recargar todos los productos desde el backend para asegurar sincronización
            console.log('🔄 Recargando productos desde el backend...')
            const updatedProducts = await service.getProducts()
            console.log('✅ Productos recargados:', updatedProducts.length, 'productos')
            
            setProducts(updatedProducts)
            
            toast.success(`Producto creado: ${newProduct.nombre}`)
            // No cerramos aquí, lo maneja el diálogo si hay impresión
            // setShowNewProductDialog(false) 
            return created
          } catch (error) {
            console.error('❌ Error al crear producto:', error)
            const rawMessage = error instanceof Error ? error.message : 'Error desconocido'
            const normalized = rawMessage.toLowerCase()

            if (normalized.includes('sku') && normalized.includes('ya existe')) {
              toast.error('Ese producto ya existe (SKU duplicado).')
              toast.info('Para agregar más inventario: abre el producto → "Ver por Ubicación" → ícono de lápiz y ajusta la cantidad.')
              return
            }

            toast.error(`Error al crear producto: ${rawMessage}`)
          }
        }}
      />

      <RestockProductDialog
        open={showRestockDialog}
        onOpenChange={setShowRestockDialog}
        products={products ?? []}
        locations={locations.filter(l => l.activo)}
        onSuccess={async () => {
          const updatedProducts = await service.getProducts()
          setProducts(updatedProducts)
        }}
      />

      <NewOrderDialog
        open={showNewOrderDialog}
        onOpenChange={setShowNewOrderDialog}
        profiles={activeProfiles}
        salesProfiles={activeSalesProfiles}
        locations={locations.filter(l => l.activo)}
        products={(products ?? []).filter(p => p.activo && p.stock_disponible > 0)}
        onSubmit={async (newOrder) => {
          try {
            const created = await service.createOrder(newOrder)
            setOrders((current: OrderWithItems[]) => [created, ...(current ?? [])])
            
            const updatedProducts = await service.getProducts()
            setProducts(updatedProducts)
            
            // Try to link order to AI interaction if phone number exists
            if (newOrder.customer_phone) {
              try {
                await service.linkOrderToInteraction(newOrder.customer_phone, created.id)
                console.log('✅ Orden vinculada a interacción AI')
              } catch (e) {
                console.warn('⚠️ No se pudo vincular orden a interacción:', e)
                // Don't fail the whole operation if linking fails
              }
            }
            
            toast.success('Orden creada exitosamente')
            setShowNewOrderDialog(false)
          } catch (error) {
            console.error('❌ Error al crear orden:', error)
            toast.error(`Error al crear orden: ${error instanceof Error ? error.message : 'Error desconocido'}`)
          }
        }}
      />

      {editingProduct && (
        <EditProductDialog
          open={true}
          product={editingProduct}
          onOpenChange={(open) => !open && setEditingProduct(null)}
          onSubmit={async (productId, updates) => {
            const savedProduct = await service.updateProduct(productId, updates)
            setProducts((current: ProductWithStock[]) => (current ?? []).map(p => p.id === savedProduct.id ? savedProduct : p))
            toast.success('Producto actualizado exitosamente')
            setEditingProduct(null)
          }}
        />
      )}

      {/* V2.0: TransferStockDialog para transferencias entre ubicaciones */}
      {transferringProduct && (
        <TransferStockDialog
          open={true}
          product={transferringProduct}
          onOpenChange={(open) => !open && setTransferringProduct(null)}
                    initialFromLocationId={transferOriginFilter !== 'all' ? Number(transferOriginFilter) : undefined}
                    initialToLocationId={quickTransferToLocationId !== 'all' ? Number(quickTransferToLocationId) : undefined}
          onTransferComplete={async () => {
            // Recargar productos después de la transferencia
            const updatedProducts = await inventoryServiceInstance.getProducts()
            setProducts(updatedProducts)
            setTransferringProduct(null)
            toast.success('Transferencia creada - pendiente de confirmación')
            // Abrir el diálogo de lista de transferencias
            setShowTransferListDialog(true)
          }}
        />
      )}

      {/* V2.0: TransferListDialog para gestionar transferencias pendientes y completadas */}
      {showTransferListDialog && (
        <TransferListDialog
          open={showTransferListDialog}
          onOpenChange={setShowTransferListDialog}
          locations={locations ?? []}
          onTransferUpdated={async () => {
            // Recargar productos cuando se confirme/rechace una transferencia
            const updatedProducts = await inventoryServiceInstance.getProducts()
            setProducts(updatedProducts)
            toast.success('Stock actualizado')
          }}
        />
      )}

      {editingOrder && (
        <EditOrderDialog
          open={true}
          order={editingOrder}
          products={(products ?? []).filter(p => p.activo)}
          salesProfiles={activeSalesProfiles}
          onOpenChange={(open) => !open && setEditingOrder(null)}
          onSubmit={async (orderId, updates) => {
            const savedOrder = await service.updateOrder(orderId, updates)
            setOrders((current: OrderWithItems[]) => (current ?? []).map(o => o.id === savedOrder.id ? savedOrder : o))
            
            const updatedProducts = await service.getProducts()
            setProducts(updatedProducts)
            
            toast.success('Orden actualizada exitosamente')
            setEditingOrder(null)
          }}
        />
      )}

      <SettingsDialog
        open={showSettingsDialog}
        onOpenChange={setShowSettingsDialog}
        onOpenNotificationSettings={() => setShowNotificationSettings(true)}
        onOpenSyncSettings={() => setShowSyncSettings(true)}
      />

      <DailyCloseDialog
        open={showDailyCloseDialog}
        onOpenChange={setShowDailyCloseDialog}
        onValidated={() => {
          // Recargar órdenes después de la validación
          if (useAPI) {
            apiClient.fetchOrders().then(data => setOrders(data)).catch(() => {})
          }
        }}
      />

      <MultiStoreControlDialog
        open={showMultiStoreControl}
        onOpenChange={setShowMultiStoreControl}
        locations={locations ?? []}
        products={products ?? []}
        permissions={{
          canViewInventory,
          canCountInventory,
          canAdjustInventory,
          canManagePurchases,
          canManageCashCloses,
          canManageLocationAccess,
          canViewAudit,
          canViewReports,
        }}
        onInventoryChanged={async () => {
          if (!canViewInventory) return
          const updatedProducts = await service.getProducts()
          setProducts(updatedProducts)
        }}
      />

      {validationCodeRequest && (
        <ValidationCodeDialog
          open={Boolean(validationCodeRequest)}
          title={validationCodeRequest.title}
          description={validationCodeRequest.description}
          confirmLabel="Validar"
          onCancel={() => {
            validationCodeRequest.resolve(null)
            setValidationCodeRequest(null)
          }}
          onConfirm={code => {
            validationCodeRequest.resolve(code)
            setValidationCodeRequest(null)
          }}
        />
      )}

      <KeyboardShortcutsDialog
        open={showKeyboardDialog}
        onOpenChange={setShowKeyboardDialog}
      />

      <ImportProductsDialog
        open={showImportDialog}
        onOpenChange={setShowImportDialog}
        onImport={handleImportProducts}
        locations={locations}
      />

      <ManageSuppliersDialog
        open={showSuppliersDialog}
        onOpenChange={setShowSuppliersDialog}
      />

      <HealthCheckDialog
        open={showHealthCheckDialog}
        onOpenChange={setShowHealthCheckDialog}
        result={healthCheckResult}
        isRunning={isHealthCheckRunning}
        onRunCheck={async () => {
          await runCheck()
        }}
        onAutoFix={() => {
          const fixes = performAutoFix()
          if (fixes) {
            setProducts(fixes.products)
            setOrders(fixes.orders)
            setProfiles(fixes.profiles)
            
            if (fixes.fixed.length > 0) {
              toast.success(`Auto-reparación completada: ${fixes.fixed.length} corrección(es)`)
              fixes.fixed.forEach(msg => toast.info(msg))
            } else {
              toast.info('No hay problemas auto-reparables')
            }
            
            runCheck()
          }
        }}
      />

      <NotificationSettingsDialog
        open={showNotificationSettings}
        onOpenChange={setShowNotificationSettings}
        profiles={profiles ?? []}
      />

      <LowStockReportDialog
        open={showLowStockReport}
        onOpenChange={setShowLowStockReport}
        products={products ?? []}
        profiles={profiles ?? []}
        locations={locations ?? []}
        onProductClick={(product) => {
          setShowLowStockReport(false)
          setEditingProduct(product)
        }}
      />

      <AdvancedSearchDialog
        open={showAdvancedSearch}
        onOpenChange={setShowAdvancedSearch}
        onSearch={(filters) => setAdvancedFilters(filters)}
        onClear={() => setAdvancedFilters(null)}
      />

      {showReportsDialog && (() => {
        const currentProfile = selectedSalesChannel !== 'all' 
          ? (profiles ?? []).find(p => p.slug === selectedSalesChannel)
          : (profiles ?? [])[0]
        
        if (!currentProfile) return null
        
        const reportData = generateReportData(orders ?? [], products ?? [])
        
        return (
          <ReportsDialog
            open={showReportsDialog}
            onOpenChange={setShowReportsDialog}
            reportData={reportData}
            profile={currentProfile}
          />
        )
      })()}

      <SalesHistoryDialog
        open={showSalesHistoryDialog}
        onOpenChange={setShowSalesHistoryDialog}
        orders={orders ?? []}
        locations={locations ?? []}
        salesProfiles={salesProfiles ?? []}
      />

      {showCustomerHistory && (
        <CustomerHistoryDialog
          open={showCustomerHistory}
          onOpenChange={setShowCustomerHistory}
          customerPhone={selectedCustomerPhone}
          orders={orders ?? []}
          profile={(profiles ?? [])[0] || { id: 0, name: 'Default', slug: 'default', active: true }}
          onViewOrder={(order) => {
            setEditingOrder(order)
            setShowCustomerHistory(false)
          }}
        />
      )}

      {currentProfile && (
        <AIForecastingDialog
          open={showForecastingDialog}
          onOpenChange={setShowForecastingDialog}
          products={products ?? []}
          orders={orders ?? []}
          profile={currentProfile}
          onProductClick={(product) => {
            setShowForecastingDialog(false)
            setEditingProduct(product)
          }}
        />
      )}

      <OptimizationInsightsDialog
        open={showOptimizationDialog}
        onOpenChange={setShowOptimizationDialog}
        products={products ?? []}
        orders={orders ?? []}
        profile={currentProfile}
        onProductClick={(product) => {
          setShowOptimizationDialog(false)
          setEditingProduct(product)
        }}
      />

      <SyncSettingsDialog
        open={showSyncSettings}
        onOpenChange={setShowSyncSettings}
      />

      <AITrainingCenter
        open={showAITraining}
        onOpenChange={setShowAITraining}
      />

      <AIStatusDialog
        open={showAIStatusDialog}
        onOpenChange={setShowAIStatusDialog}
        status={aiStatus}
        isLoading={isAIStatusLoading}
        error={aiStatusError}
        onRefresh={refreshAIStatus}
        isApiMode={isAIStatusAvailable}
      />

      <CustomerInsights
        open={showCustomerInsights}
        onOpenChange={setShowCustomerInsights}
      />

      <AIChatOrchestratorDialog
        open={showAIChatOrchestrator}
        onOpenChange={setShowAIChatOrchestrator}
        salesProfiles={activeSalesProfiles}
        locations={locations.filter(location => location.activo)}
      />

      <ChannelHealthDialog
        open={showChannelHealthDialog}
        onOpenChange={setShowChannelHealthDialog}
      />

      {viewingProductHistory && (
        <StockHistoryDialog
          open={!!viewingProductHistory}
          onOpenChange={(open) => !open && setViewingProductHistory(null)}
          product={viewingProductHistory}
        />
      )}

      <ManageUsersDialog
        open={showManageUsersDialog}
        onOpenChange={setShowManageUsersDialog}
      />

      <PendingTradeInsDialog
        open={showPendingTradeIns}
        onOpenChange={setShowPendingTradeIns}
      />

      <PhotoRequestsDashboardDialog
        open={showPhotoRequestsDialog}
        onOpenChange={setShowPhotoRequestsDialog}
      />

      <ReturnsListDialog
        open={showReturnsListDialog}
        onOpenChange={setShowReturnsListDialog}
      />

      <WarrantyCheckDialog
        open={showWarrantyCheck}
        onOpenChange={setShowWarrantyCheck}
      />
    </div>
  )
}

export default function App() {
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    const handlePopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  if (path === '/catalogo' || path.startsWith('/catalogo/')) {
    return <PublicCatalog />
  }

  return <MainApp />
}
