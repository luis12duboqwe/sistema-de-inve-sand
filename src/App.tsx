import { useState, useEffect } from 'react'
import { useKV } from '@/hooks/use-kv'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { Package, ShoppingCart, MagnifyingGlass, Plus, Gear, Keyboard, Download, CloudArrowUp, Database, Upload, CheckSquare, Square, Trash, CheckCircle, XCircle, Power, Pulse, FunnelSimple, ChartLine, Sparkle, Lightbulb, MapPin, Robot, ArrowsLeftRight } from '@phosphor-icons/react'
import type { Profile, ProductWithStock, OrderWithItems, AdvancedSearchFilters, SalesProfile, Location } from '@/lib/types'
import { ProductCard } from '@/components/ProductCard'
import { OrderCard } from '@/components/OrderCard'
// import { ProfileCard } from '@/components/ProfileCard' // DEPRECATED V1.0
import { NewProductDialog } from '@/components/NewProductDialog'
import { NewOrderDialog } from '@/components/NewOrderDialog'
// import { NewProfileDialog } from '@/components/NewProfileDialog' // DEPRECATED V1.0
import { EditProductDialog } from '@/components/EditProductDialog'
import { TransferStockDialog } from '@/components/TransferStockDialog'
import { TransferListDialog } from '@/components/TransferListDialog'
import { EditOrderDialog } from '@/components/EditOrderDialog'
import { SettingsDialog } from '@/components/SettingsDialog'
import { KeyboardShortcutsDialog } from '@/components/KeyboardShortcutsDialog'
import { ImportProductsDialog } from '@/components/ImportProductsDialog'
// import { ProfileSettingsDialog } from '@/components/ProfileSettingsDialog' // DEPRECATED V1.0
// import { ProfileDetailsDialog } from '@/components/ProfileDetailsDialog' // DEPRECATED V1.0
// import { ProfileSetupGuide } from '@/components/ProfileSetupGuide' // DEPRECATED V1.0
import { DashboardStats } from '@/components/DashboardStats'
import { HealthCheckDialog } from '@/components/HealthCheckDialog'
import { LowStockAlert } from '@/components/LowStockAlert'
// import { ProfileConfigPrompt } from '@/components/ProfileConfigPrompt' // DEPRECATED V1.0
// import { ProfilesConfigSummary } from '@/components/ProfilesConfigSummary' // DEPRECATED V1.0
import { NotificationCenter } from '@/components/NotificationCenter'
import { NotificationSettingsDialog } from '@/components/NotificationSettingsDialog'
import { LowStockReportDialog } from '@/components/LowStockReportDialog'
import { AdvancedSearchDialog } from '@/components/AdvancedSearchDialog'
import { ReportsDialog } from '@/components/ReportsDialog'
import { CustomerHistoryDialog } from '@/components/CustomerHistoryDialog'
import { AIForecastingDialog } from '@/components/AIForecastingDialog'
import { ForecastingWidget } from '@/components/ForecastingWidget'
import { OptimizationInsightsDialog } from '@/components/OptimizationInsightsDialog'
import { SyncIndicator } from '@/components/SyncIndicator'
import { BackendConnectionCheck } from '@/components/BackendConnectionCheck'
import { StockHistoryDialog } from '@/components/StockHistoryDialog'
import { LocationsList } from '@/components/LocationsList'
import { SalesProfilesList } from '@/components/SalesProfilesList'
import { initializeDefaultData } from '@/lib/dataInitializer'
import { SyncSettingsDialog } from '@/components/SyncSettingsDialog'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'
import { useInitializeData } from '@/hooks/use-initialize-data'
import { useHealthCheck } from '@/hooks/use-health-check'
import { useForecasting } from '@/hooks/use-forecasting'
import { useRealtimeSync } from '@/hooks/use-realtime-sync'
import { exportProductsToCSV, exportOrdersToCSV } from '@/lib/exportUtils'
import { generateOrderPDF } from '@/lib/pdfExport'
import { filterOrdersByAdvancedSearch, generateReportData } from '@/lib/reportUtils'
import { inventoryServiceFactory, inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { motion } from 'framer-motion'

export default function App() {
  const [backendConnected, setBackendConnected] = useState(false)
  const { isInitialized, isLoading } = useInitializeData()
  const [products, setProducts] = useKV<ProductWithStock[]>('inventory-products', [])
  const [orders, setOrders] = useKV<OrderWithItems[]>('inventory-orders', [])
  const [profiles, setProfiles] = useKV<Profile[]>('inventory-profiles', [])
  const [salesProfiles, setSalesProfiles] = useState<SalesProfile[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [dataLoaded, setDataLoaded] = useState(false)
  // V2.0: Renamed for clarity - this filters views by sales channel, not business segment
  const [selectedSalesChannel, setSelectedSalesChannel] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [orderStatusFilter, setOrderStatusFilter] = useState<string>('all')
  const [showInactive, setShowInactive] = useState(false)
  const [customerSearchTerm, setCustomerSearchTerm] = useState('')
  const [orderDateFrom, setOrderDateFrom] = useState<string>('')
  const [orderDateTo, setOrderDateTo] = useState<string>('')
  const [activeTab, setActiveTab] = useState('products')
  const [showNewProductDialog, setShowNewProductDialog] = useState(false)
  const [showNewOrderDialog, setShowNewOrderDialog] = useState(false)
  // V1.0 LEGACY: const [showNewProfileDialog, setShowNewProfileDialog] = useState(false)
  const [showSettingsDialog, setShowSettingsDialog] = useState(false)
  const [showKeyboardDialog, setShowKeyboardDialog] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [showHealthCheckDialog, setShowHealthCheckDialog] = useState(false)
  const [showNotificationSettings, setShowNotificationSettings] = useState(false)
  const [showLowStockReport, setShowLowStockReport] = useState(false)
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false)
  const [showReportsDialog, setShowReportsDialog] = useState(false)
  const [showCustomerHistory, setShowCustomerHistory] = useState(false)
  const [showForecastingDialog, setShowForecastingDialog] = useState(false)
  const [showOptimizationDialog, setShowOptimizationDialog] = useState(false)
  const [showSyncSettings, setShowSyncSettings] = useState(false)
  const [selectedCustomerPhone, setSelectedCustomerPhone] = useState('')
  const [advancedFilters, setAdvancedFilters] = useState<AdvancedSearchFilters | null>(null)
  const [editingProduct, setEditingProduct] = useState<ProductWithStock | null>(null)
  const [transferringProduct, setTransferringProduct] = useState<ProductWithStock | null>(null)
  const [showTransferListDialog, setShowTransferListDialog] = useState(false)
  const [viewingProductHistory, setViewingProductHistory] = useState<ProductWithStock | null>(null)
  // const [editingProfile, setEditingProfile] = useState<Profile | null>(null)
  const [editingOrder, setEditingOrder] = useState<OrderWithItems | null>(null)
  // const [profileWithSettings, setProfileWithSettings] = useState<Profile | null>(null)
  // const [viewingProfile, setViewingProfile] = useState<Profile | null>(null)
  const [useAPI] = useKV<boolean>('settings_use_api', false)
  const [apiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')
  const [selectedProducts, setSelectedProducts] = useState<Set<number>>(new Set())
  const [selectedOrders, setSelectedOrders] = useState<Set<number>>(new Set())
  const [bulkActionMode, setBulkActionMode] = useState(false)

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

  const service = inventoryServiceFactory(useAPI ?? false, apiUrl ?? 'http://localhost:8000/api')

  useEffect(() => {
    const loadData = async () => {
      if (!isInitialized) return
      
      try {
        console.log('🔄 Cargando datos iniciales...')
        console.log('📊 useAPI:', useAPI, 'apiUrl:', apiUrl)
        
        // Inicializar datos por defecto si no existen
        await initializeDefaultData()
        
        const currentService = inventoryServiceFactory(useAPI ?? false, apiUrl ?? 'http://localhost:8000/api')
        const [loadedProducts, loadedOrders, loadedProfiles, loadedSalesProfiles, loadedLocations] = await Promise.all([
          currentService.getProducts(),
          currentService.getOrders(),
          currentService.getProfiles(),
          currentService.getSalesProfiles ? currentService.getSalesProfiles() : Promise.resolve([]),
          currentService.getLocations ? currentService.getLocations() : Promise.resolve([])
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
  }, [isInitialized, useAPI, apiUrl, setProducts, setOrders, setProfiles, setSalesProfiles, setLocations])

  const handleBulkDeleteProducts = async () => {
    if (selectedProducts.size === 0) return
    
    try {
      markSyncStart()
      const updatedProducts = (products ?? []).filter(p => !selectedProducts.has(p.id))
      setProducts(updatedProducts)
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
      const updatedProducts = (products ?? []).map(p =>
        selectedProducts.has(p.id) ? { ...p, activo: !p.activo } : p
      )
      setProducts(updatedProducts)
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
      const updatedOrders = (orders ?? []).map(o =>
        selectedOrders.has(o.id) ? { ...o, estado: newStatus } : o
      )
      setOrders(updatedOrders)
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
      const updatedOrders = (orders ?? []).filter(o => !selectedOrders.has(o.id))
      setOrders(updatedOrders)
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
      action: () => setShowSettingsDialog(true),
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
      action: () => setShowForecastingDialog(true),
      description: 'Ver pronóstico de ventas IA',
      category: 'general'
    },
    {
      id: 'view-optimization',
      key: 'o',
      altKey: true,
      action: () => setShowOptimizationDialog(true),
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
      action: () => setActiveTab('orders'),
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
        if (activeTab === 'products') setShowNewProductDialog(true)
        else if (activeTab === 'orders') setShowNewOrderDialog(true)
        // V1.0 LEGACY: profiles tab removed
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
        if (activeTab === 'products') setShowImportDialog(true)
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

  const handleImportProducts = async (productsData: Partial<ProductWithStock>[]) => {
    try {
      const importedProducts = await service.bulkCreateProducts(productsData)
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

    return filtered
  })()

  const activeProfiles = (profiles ?? []).filter(p => p.active)
  const activeSalesProfiles = (salesProfiles ?? []).filter(sp => sp.active)
  const channelOptions = activeSalesProfiles.length ? activeSalesProfiles : activeProfiles

  const handleTabChange = (value: string) => {
    setActiveTab(value)
    setBulkActionMode(false)
    setSelectedProducts(new Set())
    setSelectedOrders(new Set())
  }

  // V1.0 LEGACY: Función no usada - comentada
  // const handleUpdateProfileSettings = async (profileId: number, settings: ProfileSettings) => {
  //   try {
  //     const updatedProfile = (profiles ?? []).find(p => p.id === profileId)
  //     if (!updatedProfile) return

  //     const profileWithNewSettings = { ...updatedProfile, settings }
  //     setProfiles(current => (current ?? []).map(p => p.id === profileId ? profileWithNewSettings : p))
  //     toast.success('Configuración guardada exitosamente')
  //     setProfileWithSettings(null)
  //   } catch (error) {
  //     console.error('Error updating profile settings:', error)
  //     toast.error('Error al guardar configuración')
  //   }
  // }

  // Verificar conexión del backend primero
  if (!backendConnected) {
    return <BackendConnectionCheck onSuccess={() => setBackendConnected(true)} />
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
              <SyncIndicator syncStatus={syncStatus} />
              
              <Badge variant={useAPI ? "default" : "secondary"} className="hidden sm:flex items-center gap-1">
                {useAPI ? <CloudArrowUp size={14} /> : <Database size={14} />}
                {useAPI ? 'API' : 'Local'}
              </Badge>
              
              <NotificationCenter
                products={products ?? []}
                profiles={profiles ?? []}
                orders={orders ?? []}
                onOpenOptimization={() => setShowOptimizationDialog(true)}
              />
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowOptimizationDialog(true)}
                title="Insights de Optimización (Alt + O)"
                className="relative hover:bg-accent/20"
              >
                <Lightbulb size={20} weight="duotone" className="text-accent" />
              </Button>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowForecastingDialog(true)}
                title="Pronóstico de Ventas IA (Alt + F)"
                className="relative hover:bg-primary/10"
              >
                <Sparkle size={20} weight="duotone" />
                {getCriticalAlerts().length > 0 && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full text-xs flex items-center justify-center font-bold">
                    {getCriticalAlerts().length}
                  </span>
                )}
              </Button>
              
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
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowSettingsDialog(true)}
                title="Configuración (Ctrl + ,)"
                className="hover:bg-primary/10"
              >
                <Gear size={20} />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList className="grid w-full grid-cols-5 max-w-4xl mb-6">
            <TabsTrigger value="products" className="flex items-center gap-2">
              <Package size={18} />
              <span className="hidden sm:inline">Productos</span>
            </TabsTrigger>
            <TabsTrigger value="orders" className="flex items-center gap-2">
              <ShoppingCart size={18} />
              <span className="hidden sm:inline">Órdenes</span>
            </TabsTrigger>
            <TabsTrigger value="transfers" className="flex items-center gap-2">
              <ArrowsLeftRight size={18} />
              <span className="hidden sm:inline">Transferencias</span>
            </TabsTrigger>
            <TabsTrigger value="locations" className="flex items-center gap-2">
              <MapPin size={18} />
              <span className="hidden sm:inline">Ubicaciones</span>
            </TabsTrigger>
            <TabsTrigger value="sales-profiles" className="flex items-center gap-2">
              <Robot size={18} />
              <span className="hidden sm:inline">Canales</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="products" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <DashboardStats
                  products={products ?? []}
                  orders={orders ?? []}
                  onViewLowStockReport={() => setShowLowStockReport(true)}
                />
              </div>
              <div>
                <ForecastingWidget
                  summary={forecastingSummary ?? null}
                  criticalAlerts={getCriticalAlerts()}
                  lastUpdated={forecastingLastUpdated ?? null}
                  isGenerating={isForecastingGenerating}
                  onViewDetails={() => setShowForecastingDialog(true)}
                  onRefresh={generateForecastData}
                />
              </div>
            </div>
            
            {/* V2.0 TODO: LowStockAlert should filter by LOCATION not sales channel */}
            {selectedSalesChannel !== 'all' && (() => {
              const profile = (profiles ?? []).find(p => p.slug === selectedSalesChannel)
              return profile ? (
                <LowStockAlert
                  products={products ?? []}
                  profile={profile}
                  onProductClick={setEditingProduct}
                />
              ) : null
            })()}
            
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
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleExportProducts}
                  title="Exportar a CSV"
                >
                  <Download size={18} />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setShowImportDialog(true)}
                  title="Importar desde CSV"
                >
                  <Upload size={18} />
                </Button>
                <Button onClick={() => setShowNewProductDialog(true)} className="flex-1 sm:flex-none">
                  Nuevo Producto
                </Button>
              </div>
            </div>

            {bulkActionMode && selectedProducts.size > 0 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-4 bg-accent rounded-lg">
                <span className="text-sm font-medium">
                  {selectedProducts.size} producto{selectedProducts.size !== 1 ? 's' : ''} seleccionado{selectedProducts.size !== 1 ? 's' : ''}
                </span>
                <div className="flex gap-2 ml-auto">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleBulkToggleProductStatus}
                  >
                    <Power size={16} className="mr-2" />
                    Cambiar Estado
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBulkDeleteProducts}
                  >
                    <Trash size={16} className="mr-2" />
                    Eliminar
                  </Button>
                </div>
              </div>
            )}

            <div className="flex items-center gap-2">
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

            {filteredProducts.length === 0 ? (
              <div className="text-center py-12">
                <Package size={64} className="mx-auto text-muted-foreground mb-4" weight="duotone" />
                <h3 className="text-lg font-semibold text-card-foreground mb-2">
                  No hay productos
                </h3>
                <p className="text-muted-foreground mb-4">
                  Comienza agregando tu primer producto al inventario
                </p>
                <Button onClick={() => setShowNewProductDialog(true)}>
                  <Plus size={18} className="mr-2" />
                  Agregar Producto
                </Button>
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
                      onEdit={setEditingProduct}
                      onTransfer={setTransferringProduct}
                      onViewHistory={setViewingProductHistory}
                      onToggleActive={async (p) => {
                        const updated = await service.updateProduct(p.id, { ...p, activo: !p.activo })
                        setProducts((current: ProductWithStock[]) => (current ?? []).map(pr => pr.id === updated.id ? updated : pr))
                        toast.success(`Producto ${updated.activo ? 'activado' : 'desactivado'}`)
                      }}
                      onDelete={async (p) => {
                        if (!confirm(`¿Estás seguro de eliminar "${p.nombre}"?\n\nEsta acción no se puede deshacer.`)) {
                          return
                        }
                        
                        try {
                          await service.deleteProduct(p.id)
                          setProducts((current: ProductWithStock[]) => (current ?? []).filter(pr => pr.id !== p.id))
                          toast.success('Producto eliminado exitosamente')
                        } catch (error) {
                          console.error('Error deleting product:', error)
                          const message = error instanceof Error ? error.message : 'Error desconocido'
                          toast.error(`Error al eliminar producto: ${message}`)
                        }
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

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
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleExportOrders}
                  title="Exportar a CSV"
                >
                  <Download size={18} />
                </Button>
                <Button onClick={() => setShowNewOrderDialog(true)} className="flex-1 sm:flex-none">
                  <Plus size={18} className="mr-2" />
                  Nueva Orden
                </Button>
              </div>
            </div>

            {bulkActionMode && activeTab === 'orders' && selectedOrders.size > 0 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-4 bg-accent rounded-lg">
                <span className="text-sm font-medium">
                  {selectedOrders.size} orden{selectedOrders.size !== 1 ? 'es' : ''} seleccionada{selectedOrders.size !== 1 ? 's' : ''}
                </span>
                <div className="flex flex-wrap gap-2 sm:ml-auto">
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
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBulkDeleteOrders}
                  >
                    <Trash size={16} className="mr-2" />
                    Eliminar
                  </Button>
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
                <Button onClick={() => setShowNewOrderDialog(true)}>
                  <Plus size={18} className="mr-2" />
                  Crear Orden
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
                      onStatusChange={async (orderId, newStatus) => {
                        console.log(`🔄 Cambiando estado de orden ${orderId} a: ${newStatus}`)
                        const updated = await service.updateOrderStatus(orderId, newStatus)
                        console.log('✅ Orden actualizada:', updated)
                        setOrders((current: OrderWithItems[]) => (current ?? []).map(o => o.id === updated.id ? updated : o))
                        toast.success('Estado de orden actualizado')
                        
                        // Recargar productos para reflejar cambios en stock
                        console.log('🔄 Recargando productos después de cambio de estado...')
                        const updatedProducts = await service.getProducts()
                        setProducts(updatedProducts)
                      }}
                      onEdit={setEditingOrder}
                      onViewCustomerHistory={(phone) => {
                        setSelectedCustomerPhone(phone)
                        setShowCustomerHistory(true)
                      }}
                      onExportPDF={(order) => {
                        const profile = (profiles ?? []).find(p => p.id === order.profile_id)
                        if (profile) {
                          generateOrderPDF(order, profile)
                        }
                      }}
                      onDelete={async (order) => {
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
                          console.error('❌ Error al eliminar orden:', error)
                          toast.error(`Error al eliminar orden: ${message}`)
                        }
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

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

              {/* Instrucciones mejoradas */}
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
                  <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                    <ArrowsLeftRight size={20} weight="bold" />
                    Cómo hacer una transferencia:
                  </h3>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
                    <li>Ve a la pestaña <strong>"Productos"</strong></li>
                    <li>Busca el producto que quieres transferir</li>
                    <li>Haz clic en el botón <ArrowsLeftRight className="inline w-4 h-4 mx-1" /> <strong>Transferir</strong></li>
                    <li>Selecciona ubicación origen y destino</li>
                    <li>Ingresa la cantidad y confirma</li>
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
                    {(products ?? []).filter(p => p.stock_items && p.stock_items.length > 1).length} productos en múltiples ubicaciones
                  </Badge>
                </div>
                
                {(products ?? []).filter(p => p.stock_items && p.stock_items.length > 0).length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground border rounded-lg bg-muted/20">
                    <ArrowsLeftRight size={48} className="mx-auto mb-4 opacity-50" weight="duotone" />
                    <p className="font-medium">No hay productos con stock asignado a ubicaciones</p>
                    <p className="text-sm mt-2">Agrega productos y asígnalos a ubicaciones en la pestaña <strong>Productos</strong></p>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {(products ?? [])
                      .filter(p => p.stock_items && p.stock_items.length > 0)
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
            <SalesProfilesList />
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
            setShowNewProductDialog(false)
          } catch (error) {
            console.error('❌ Error al crear producto:', error)
            toast.error(`Error al crear producto: ${error instanceof Error ? error.message : 'Error desconocido'}`)
          }
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
          const created = await service.createOrder(newOrder)
          setOrders((current: OrderWithItems[]) => [created, ...(current ?? [])])
          
          const updatedProducts = await service.getProducts()
          setProducts(updatedProducts)
          
          toast.success('Orden creada exitosamente')
          setShowNewOrderDialog(false)
        }}
      />

      {/* DEPRECATED V1.0 - Profile Business Units
      <NewProfileDialog
        open={showNewProfileDialog}
        onOpenChange={setShowNewProfileDialog}
        onSubmit={async (name, slug) => {
          try {
            console.log('Creating profile:', { name, slug })
            const created = await service.createProfile({ name, slug, active: true })
            console.log('Profile created:', created)
            
            // Actualizar estado de forma segura
            setProfiles(current => {
              const updated = [...(current ?? []), created]
              console.log('Updated profiles list:', updated)
              return updated
            })
            
            toast.success('Perfil creado exitosamente')
            setShowNewProfileDialog(false)
          } catch (error) {
            console.error('Error creating profile:', error)
            toast.error(error instanceof Error ? error.message : 'Error al crear perfil')
          }
        }}
      />
      */}

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

      {/* DEPRECATED V1.0 - Edit Profile Business Units
      {editingProfile && (
        <EditProfileDialog
          open={true}
          profile={editingProfile}
          onOpenChange={(open) => !open && setEditingProfile(null)}
          onSubmit={async (profileId, name, active) => {
            const savedProfile = await service.updateProfile(profileId, { name, active })
            setProfiles(current => (current ?? []).map(p => p.id === savedProfile.id ? savedProfile : p))
            toast.success('Perfil actualizado exitosamente')
            setEditingProfile(null)
          }}
        />
      )}
      */}

      {editingOrder && (
        <EditOrderDialog
          open={true}
          order={editingOrder}
          products={(products ?? []).filter(p => p.activo)}
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

      <KeyboardShortcutsDialog
        open={showKeyboardDialog}
        onOpenChange={setShowKeyboardDialog}
      />

      <ImportProductsDialog
        open={showImportDialog}
        onOpenChange={setShowImportDialog}
        onImport={handleImportProducts}
      />

      {/* DEPRECATED V1.0 - Profile Settings
      {profileWithSettings && (
        <ProfileSettingsDialog
          open={true}
          profile={profileWithSettings}
          onOpenChange={(open) => !open && setProfileWithSettings(null)}
          onSubmit={handleUpdateProfileSettings}
        />
      )}
      */}

      {/* DEPRECATED V1.0 - Profile Details
      {viewingProfile && (
        <ProfileDetailsDialog
          open={true}
          profile={viewingProfile}
          productCount={(products ?? []).filter(p => p.profile_id === viewingProfile.id && p.activo).length}
          orderCount={(orders ?? []).filter(o => o.profile_id === viewingProfile.id).length}
          onOpenChange={(open) => !open && setViewingProfile(null)}
          onEdit={setEditingProfile}
          onSettings={setProfileWithSettings}
        />
      )}
      */}

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

      {viewingProductHistory && (
        <StockHistoryDialog
          open={!!viewingProductHistory}
          onOpenChange={(open) => !open && setViewingProductHistory(null)}
          product={viewingProductHistory}
        />
      )}
    </div>
  )
}
