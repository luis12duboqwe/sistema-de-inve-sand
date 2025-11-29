import { useState, useEffect } from 'react'
import { useKV } from '@github/spark/hooks'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { Package, ShoppingCart, UserCircle, MagnifyingGlass, Plus, Gear, Keyboard, Download, CloudArrowUp, Database, Upload, CheckSquare, Square, Trash, CheckCircle, XCircle, Power } from '@phosphor-icons/react'
import type { Profile, ProductWithStock, OrderWithItems } from '@/lib/types'
import { ProductCard } from '@/components/ProductCard'
import { OrderCard } from '@/components/OrderCard'
import { ProfileCard } from '@/components/ProfileCard'
import { NewProductDialog } from '@/components/NewProductDialog'
import { NewOrderDialog } from '@/components/NewOrderDialog'
import { NewProfileDialog } from '@/components/NewProfileDialog'
import { EditProductDialog } from '@/components/EditProductDialog'
import { EditProfileDialog } from '@/components/EditProfileDialog'
import { EditOrderDialog } from '@/components/EditOrderDialog'
import { SettingsDialog } from '@/components/SettingsDialog'
import { KeyboardShortcutsDialog } from '@/components/KeyboardShortcutsDialog'
import { ImportProductsDialog } from '@/components/ImportProductsDialog'
import { DashboardStats } from '@/components/DashboardStats'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'
import { exportProductsToCSV, exportOrdersToCSV } from '@/lib/exportUtils'
import { inventoryServiceFactory } from '@/lib/inventoryServiceFactory'

export default function App() {
  const [products, setProducts] = useKV<ProductWithStock[]>('inventory-products', [])
  const [orders, setOrders] = useKV<OrderWithItems[]>('inventory-orders', [])
  const [profiles, setProfiles] = useKV<Profile[]>('inventory-profiles', [])
  const [selectedProfile, setSelectedProfile] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [orderStatusFilter, setOrderStatusFilter] = useState<string>('all')
  const [showInactive, setShowInactive] = useState(false)
  const [customerSearchTerm, setCustomerSearchTerm] = useState('')
  const [activeTab, setActiveTab] = useState('products')
  const [showNewProductDialog, setShowNewProductDialog] = useState(false)
  const [showNewOrderDialog, setShowNewOrderDialog] = useState(false)
  const [showNewProfileDialog, setShowNewProfileDialog] = useState(false)
  const [showSettingsDialog, setShowSettingsDialog] = useState(false)
  const [showKeyboardDialog, setShowKeyboardDialog] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [editingProduct, setEditingProduct] = useState<ProductWithStock | null>(null)
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null)
  const [editingOrder, setEditingOrder] = useState<OrderWithItems | null>(null)
  const [useAPI, setUseAPI] = useKV<boolean>('settings_use_api', false)
  const [apiUrl, setApiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')
  const [selectedProducts, setSelectedProducts] = useState<Set<number>>(new Set())
  const [selectedOrders, setSelectedOrders] = useState<Set<number>>(new Set())
  const [bulkActionMode, setBulkActionMode] = useState(false)

  const service = inventoryServiceFactory(useAPI ?? false, apiUrl ?? 'http://localhost:8000/api')

  useEffect(() => {
    const loadData = async () => {
      try {
        const currentService = inventoryServiceFactory(useAPI ?? false, apiUrl ?? 'http://localhost:8000/api')
        const [loadedProducts, loadedOrders, loadedProfiles] = await Promise.all([
          currentService.getProducts(),
          currentService.getOrders(),
          currentService.getProfiles()
        ])
        
        setProducts(loadedProducts)
        setOrders(loadedOrders)
        setProfiles(loadedProfiles)
      } catch (error) {
        console.error('Error loading data:', error)
        toast.error('Error al cargar datos del inventario')
      }
    }

    loadData()
  }, [useAPI, apiUrl, setProducts, setOrders, setProfiles])

  const handleBulkDeleteProducts = async () => {
    if (selectedProducts.size === 0) return
    
    try {
      const updatedProducts = (products ?? []).filter(p => !selectedProducts.has(p.id))
      setProducts(updatedProducts)
      toast.success(`${selectedProducts.size} productos eliminados`)
      setSelectedProducts(new Set())
      setBulkActionMode(false)
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
      key: 'n',
      ctrlKey: true,
      callback: () => {
        if (activeTab === 'products') setShowNewProductDialog(true)
        else if (activeTab === 'orders') setShowNewOrderDialog(true)
        else if (activeTab === 'profiles') setShowNewProfileDialog(true)
      },
      description: 'Crear nuevo elemento'
    },
    {
      key: 'k',
      ctrlKey: true,
      callback: () => {
        const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement
        searchInput?.focus()
      },
      description: 'Enfocar búsqueda'
    },
    {
      key: ',',
      ctrlKey: true,
      callback: () => setShowSettingsDialog(true),
      description: 'Abrir configuración'
    },
    {
      key: '?',
      shiftKey: true,
      callback: () => setShowKeyboardDialog(true),
      description: 'Mostrar atajos de teclado'
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
      setProducts(current => [...(current ?? []), ...importedProducts])
      toast.success(`${importedProducts.length} productos importados exitosamente`)
    } catch (error) {
      console.error('Error importing products:', error)
      toast.error('Error al importar productos')
      throw error
    }
  }

  const filteredProducts = (products ?? []).filter(p => {
    if (selectedProfile !== 'all') {
      const profile = (profiles ?? []).find(pr => pr.slug === selectedProfile)
      if (!profile || p.profile_id !== profile.id) return false
    }
    
    if (!showInactive && !p.activo) return false
    
    if (categoryFilter && categoryFilter !== 'all' && p.categoria !== categoryFilter) return false
    
    if (searchTerm && typeof searchTerm === 'string' && searchTerm.trim()) {
      const term = String(searchTerm).toLowerCase()
      const nombre = p.nombre ? String(p.nombre).toLowerCase() : ''
      const marca = p.marca ? String(p.marca).toLowerCase() : ''
      const modelo = p.modelo ? String(p.modelo).toLowerCase() : ''
      return nombre.includes(term) || marca.includes(term) || modelo.includes(term)
    }
    
    return true
  })

  const filteredOrders = (orders ?? []).filter(o => {
    if (selectedProfile !== 'all') {
      const profile = (profiles ?? []).find(p => p.slug === selectedProfile)
      if (!profile || o.profile_id !== profile.id) return false
    }
    
    if (orderStatusFilter && orderStatusFilter !== 'all' && o.estado !== orderStatusFilter) return false
    
    if (customerSearchTerm && typeof customerSearchTerm === 'string' && customerSearchTerm.trim()) {
      const term = String(customerSearchTerm).toLowerCase()
      const customerName = o.customer_name ? String(o.customer_name).toLowerCase() : ''
      const customerPhone = o.customer_phone ? String(o.customer_phone).toLowerCase() : ''
      return customerName.includes(term) || customerPhone.includes(term)
    }
    
    return true
  })

  const activeProfiles = (profiles ?? []).filter(p => p.active)

  const handleTabChange = (value: string) => {
    setActiveTab(value)
    setBulkActionMode(false)
    setSelectedProducts(new Set())
    setSelectedOrders(new Set())
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Package size={32} className="text-primary" weight="duotone" />
              <div>
                <h1 className="text-2xl font-bold text-card-foreground">Sistema de Inventario</h1>
                <p className="text-sm text-muted-foreground">Gestión de productos y órdenes</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Badge variant={useAPI ? "default" : "secondary"} className="hidden sm:flex items-center gap-1">
                {useAPI ? <CloudArrowUp size={14} /> : <Database size={14} />}
                {useAPI ? 'API' : 'Local'}
              </Badge>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowKeyboardDialog(true)}
                title="Atajos de teclado (Shift + ?)"
              >
                <Keyboard size={20} />
              </Button>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowSettingsDialog(true)}
                title="Configuración (Ctrl + ,)"
              >
                <Gear size={20} />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList className="grid w-full grid-cols-3 max-w-md mb-6">
            <TabsTrigger value="products" className="flex items-center gap-2">
              <Package size={18} />
              <span className="hidden sm:inline">Productos</span>
            </TabsTrigger>
            <TabsTrigger value="orders" className="flex items-center gap-2">
              <ShoppingCart size={18} />
              <span className="hidden sm:inline">Órdenes</span>
            </TabsTrigger>
            <TabsTrigger value="profiles" className="flex items-center gap-2">
              <UserCircle size={18} />
              <span className="hidden sm:inline">Perfiles</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="products" className="space-y-6">
            <DashboardStats products={products ?? []} orders={orders ?? []} />
            
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
                
                <Select value={selectedProfile} onValueChange={setSelectedProfile}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Perfil" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los perfiles</SelectItem>
                    {activeProfiles.map(profile => (
                      <SelectItem key={profile.id} value={profile.slug}>
                        {profile.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

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
                      onToggleActive={async (p) => {
                        const updated = await service.updateProduct(p.id, { ...p, activo: !p.activo })
                        setProducts(current => (current ?? []).map(pr => pr.id === updated.id ? updated : pr))
                        toast.success(`Producto ${updated.activo ? 'activado' : 'desactivado'}`)
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

                <Select value={selectedProfile} onValueChange={setSelectedProfile}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Perfil" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los perfiles</SelectItem>
                    {activeProfiles.map(profile => (
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
              </div>

              <div className="flex gap-2 w-full sm:w-auto">
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
                        const updated = await service.updateOrderStatus(orderId, newStatus)
                        setOrders(current => (current ?? []).map(o => o.id === updated.id ? updated : o))
                        toast.success('Estado de orden actualizado')
                      }}
                      onEdit={setEditingOrder}
                    />
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="profiles" className="space-y-6">
            <div className="flex justify-end">
              <Button onClick={() => setShowNewProfileDialog(true)}>
                <Plus size={18} className="mr-2" />
                Nuevo Perfil
              </Button>
            </div>

            {(profiles ?? []).length === 0 ? (
              <div className="text-center py-12">
                <UserCircle size={64} className="mx-auto text-muted-foreground mb-4" weight="duotone" />
                <h3 className="text-lg font-semibold text-card-foreground mb-2">
                  No hay perfiles
                </h3>
                <p className="text-muted-foreground mb-4">
                  Crea tu primer perfil de negocio
                </p>
                <Button onClick={() => setShowNewProfileDialog(true)}>
                  <Plus size={18} className="mr-2" />
                  Crear Perfil
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(profiles ?? []).map(profile => (
                  <ProfileCard
                    key={profile.id}
                    profile={profile}
                    productCount={(products ?? []).filter(p => p.profile_id === profile.id && p.activo).length}
                    orderCount={(orders ?? []).filter(o => o.profile_id === profile.id).length}
                    onEdit={setEditingProfile}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      <NewProductDialog
        open={showNewProductDialog}
        onOpenChange={setShowNewProductDialog}
        profiles={activeProfiles}
        onSubmit={async (newProduct, stock) => {
          const productWithStock = { ...newProduct, activo: true, stock_disponible: stock }
          const created = await service.createProduct(productWithStock)
          setProducts(current => [...(current ?? []), created])
          toast.success('Producto creado exitosamente')
          setShowNewProductDialog(false)
        }}
      />

      <NewOrderDialog
        open={showNewOrderDialog}
        onOpenChange={setShowNewOrderDialog}
        profiles={activeProfiles}
        products={(products ?? []).filter(p => p.activo && p.stock_disponible > 0)}
        onSubmit={async (newOrder) => {
          const created = await service.createOrder(newOrder)
          setOrders(current => [created, ...(current ?? [])])
          
          const updatedProducts = await service.getProducts()
          setProducts(updatedProducts)
          
          toast.success('Orden creada exitosamente')
          setShowNewOrderDialog(false)
        }}
      />

      <NewProfileDialog
        open={showNewProfileDialog}
        onOpenChange={setShowNewProfileDialog}
        onSubmit={async (name, slug) => {
          try {
            const created = await service.createProfile({ name, slug, active: true })
            setProfiles(current => [...(current ?? []), created])
            toast.success('Perfil creado exitosamente')
            setShowNewProfileDialog(false)
          } catch (error) {
            console.error('Error creating profile:', error)
            toast.error(error instanceof Error ? error.message : 'Error al crear perfil')
            throw error
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
            setProducts(current => (current ?? []).map(p => p.id === savedProduct.id ? savedProduct : p))
            toast.success('Producto actualizado exitosamente')
            setEditingProduct(null)
          }}
        />
      )}

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

      {editingOrder && (
        <EditOrderDialog
          open={true}
          order={editingOrder}
          products={(products ?? []).filter(p => p.activo)}
          onOpenChange={(open) => !open && setEditingOrder(null)}
          onSubmit={async (orderId, updates) => {
            const savedOrder = await service.updateOrder(orderId, updates)
            setOrders(current => (current ?? []).map(o => o.id === savedOrder.id ? savedOrder : o))
            
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
      />

      <KeyboardShortcutsDialog
        open={showKeyboardDialog}
        onOpenChange={setShowKeyboardDialog}
      />

      <ImportProductsDialog
        open={showImportDialog}
        onOpenChange={setShowImportDialog}
        profiles={activeProfiles}
        onImport={handleImportProducts}
      />
    </div>
  )
}
