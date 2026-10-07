[Reading 1000 lines from start (total: 2791 lines, 1791 remaining)]

import { useState, useEffect, useMemo } from 'react'
import { useKV } from '@/hooks/use-kv'
import { getKV } from '@/lib/kvStorage'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { toast } from 'sonner'
import { Package, ShoppingCart, MagnifyingGlass, Plus, Gear, Keyboard, Download, CloudArrowUp, Database, Upload, CheckSquare, Square, Trash, CheckCircle, XCircle, Power, Pulse, FunnelSimple, ChartLine, Sparkle, Lightbulb, MapPin, Robot, ArrowsLeftRight, User as UserIcon, GraduationCap, ShieldCheck, CreditCard, Wrench, ArrowCounterClockwise, Camera, SquaresFour, Rows, Printer } from '@phosphor-icons/react'
import type { User, Profile, ProductWithStock, OrderWithItems, AdvancedSearchFilters, SalesProfile, Location } from '@/lib/types'
import { ProductCard } from '@/components/ProductCard'
import { PrintLabelsDialog } from '@/components/PrintLabelsDialog'
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
import { SuperAdminControlPanelDialog } from '@/components/SuperAdminControlPanelDialog'
import { LoginPage } from '@/components/LoginPage'
import { PendingTradeInsDialog } from '@/components/PendingTradeInsDialog'
import { PhotoRequestsDashboardDialog } from '@/components/PhotoRequestsDashboardDialog'
import { apiClient } from '@/lib/apiClient'
import { initializeDefaultData, clearAllData } from '@/lib/dataInitializer'
import { SyncSettingsDialog } from '@/components/SyncSettingsDialog'
import { DailyCloseDialog } from '@/components/DailyCloseDialog'
import { MultiStoreControlDialog } from '@/components/MultiStoreControlDialog'
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
import { updateOrderStatusWithoutDailyClose } from '@/lib/orderStatusActions'
import { buildMultiStoreViewModel, hasAppPermission } from '@/lib/appViewModel'
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
  const [activeTab, setActiveTab] = useState('dashboard')
  const [showNewProductDialog, setShowNewProductDialog] = useState(false)
  const [showBulkPrintLabels, setShowBulkPrintLabels] = useState(false)
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
  const [showTransferStockDialog, setShowTransferStockDialog] = useState(false)
  const [transferringProduct, setTransferringProduct] = useState<ProductWithStock | null>(null)
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
  const [showSuperAdminPanel, setShowSuperAdminPanel] = useState(false)
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
  
  // Auth State
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [showLoginDialog, setShowLoginDialog] = useState(false)

  useEffect(() => {
    const token = apiClient.getToken()
    const storedUser = localStorage.getItem('auth_user')
    let cancelled = false
    
    // Only show login if using API mode
    if (useAPI) {
      if (token && storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser)
          setCurrentUser(parsedUser)

          apiClient.getCurrentUser()
            .then((freshUser) => {
              if (cancelled) return
              setCurrentUser(freshUser)
              localStorage.setItem('auth_user', JSON.stringify(freshUser))
            })
            .catch((error) => {
              if (cancelled) return
              console.warn('No se pudo refrescar el usuario autenticado:', error)
            })
        } catch (error) {
          console.error('Error parsing auth_user from storage', error)
          setShowLoginDialog(true)
        }
      } else {
        setShowLoginDialog(true)
      }
    }

    return () => {
      cancelled = true
    }
  }, [useAPI])

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

  const hasPermission = (slug: string): boolean => hasAppPermission(Boolean(useAPI), currentUser, slug)

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
  const {
    activeLocations,
    productsWithLocationTracking,
    totalTrackedUnits,
    outOfStockProducts,
    locatedOrders,
    locationSnapshots,
  } = useMemo(
    () => buildMultiStoreViewModel(locations ?? [], products ?? [], orders ?? []),
    [locations, products, orders]
  )

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
        
        // AUTO-RESET: Limpiar datos locales una sola vez para asegurar limpieza
        const kv = getKV()
        const resetDone = await kv.get('v2_reset_complete_final')
        if (!resetDone && !useAPI) {
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

  const handleBulkUpdateOrderStatus = async (newStatus: OrderWithItems['estado']) => {
    if (selectedOrders.size === 0) return
    
    try {
      if (useAPI) {
        for (const orderId of selectedOrders) {
          await updateOrderStatusWithoutDailyClose(service, orderId, newStatus)
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
            Softmobile
          </h2>
          <p className="text-muted-foreground">Inicializando sistema inteligente...</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/50 bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-3 py-3 sm:px-4 sm:py-4">
          <div className="flex items-center justify-between gap-2 sm:gap-4">
            <motion.div 
              className="flex min-w-0 items-center gap-2 sm:gap-3"
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
                <h1 className="truncate text-lg font-bold bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent sm:text-2xl">
                  Softmobile
                </h1>
                <p className="hidden text-sm text-muted-foreground sm:block">Gestión comercial</p>
              </div>
            </motion.div>
            
            <div className="flex shrink-0 items-center gap-1 sm:gap-2">
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
              {(syncStatus.syncError || syncStatus.isSyncing) && (
                <SyncIndicator syncStatus={syncStatus} />
              )}
              
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
                  className="relative hover:bg-primary/10 text-primary"
                >
                  <Robot size={20} />
                  {isAIStatusAvailable && aiAttentionCount > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[20px] h-5 bg-amber-500 text-white rounded-full text-[10px] flex items-center justify-center px-1 font-bold">
                      {aiAttentionCount > 99 ? '99+' : aiAttentionCount}
                    </span>
                  )}

[executed on device: srv1656045 (50056b71-ec54-49e5-8524-4feb4c6efa74)]