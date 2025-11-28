import { useState, useEffect } from 'react'
import { useKV } from '@github/spark/hooks'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Toaster, toast } from 'sonner'
import { Package, ShoppingCart, UserCircle, MagnifyingGlass, Plus, Gear, Keyboard, Download, CloudArrowUp, Database } from '@phosphor-icons/react'
import type { Profile, ProductWithStock, OrderWithItems } from '@/lib/types'
import { ProductCard } from '@/components/ProductCard'
import { OrderCard } from '@/components/OrderCard'
import { ProfileCard } from '@/components/ProfileCard'
import { NewProductDialog } from '@/components/NewProductDialog'
import { NewOrderDialog } from '@/components/NewOrderDialog'
import { NewProfileDialog } from '@/components/NewProfileDialog'
import { EditProductDialog } from '@/components/EditProductDialog'
import { EditProfileDialog } from '@/components/EditProfileDialog'
import { SettingsDialog } from '@/components/SettingsDialog'
import { KeyboardShortcutsDialog } from '@/components/KeyboardShortcutsDialog'
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
  const [editingProduct, setEditingProduct] = useState<ProductWithStock | null>(null)
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null)
  const [useAPI, setUseAPI] = useKV<boolean>('inventory-use-api', false)
  const [apiUrl, setApiUrl] = useKV<string>('inventory-api-url', 'http://localhost:8000')

  const service = inventoryServiceFactory(useAPI ?? false, apiUrl ?? 'http://localhost:8000')

  useEffect(() => {
    const loadData = async () => {
      try {
        const [loadedProducts, loadedOrders, loadedProfiles] = await Promise.all([
          service.getProducts(),
          service.getOrders(),
          service.getProfiles()
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
  }, [useAPI, apiUrl])

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

  const filteredProducts = (products ?? []).filter(p => {
    if (selectedProfile !== 'all') {
      const profile = (profiles ?? []).find(pr => pr.slug === selectedProfile)
      if (!profile || p.profile_id !== profile.id) return false
    }
    
    if (!showInactive && !p.activo) return false
    
    if (categoryFilter !== 'all' && p.categoria !== categoryFilter) return false
    
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      return (
        p.nombre?.toLowerCase().includes(term) ||
        p.marca?.toLowerCase().includes(term) ||
        p.modelo?.toLowerCase().includes(term)
      )
    }
    
    return true
  })

  const filteredOrders = (orders ?? []).filter(o => {
    if (selectedProfile !== 'all') {
      const profile = (profiles ?? []).find(p => p.slug === selectedProfile)
      if (!profile || o.profile_id !== profile.id) return false
    }
    
    if (orderStatusFilter !== 'all' && o.estado !== orderStatusFilter) return false
    
    if (customerSearchTerm) {
      const term = customerSearchTerm.toLowerCase()
      return (
        o.customer_name?.toLowerCase().includes(term) ||
        o.customer_phone?.toLowerCase().includes(term)
      )
    }
    
    return true
  })

  const activeProfiles = (profiles ?? []).filter(p => p.active)

  return (
    <div className="min-h-screen bg-background">
      <Toaster position="top-right" richColors />
      
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
        <Tabs value={activeTab} onValueChange={setActiveTab}>
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
                    <SelectItem value="accesorio">Accesorios</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex gap-2 w-full sm:w-auto">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleExportProducts}
                  title="Exportar a CSV"
                >
                  <Download size={18} />
                </Button>
                <Button onClick={() => setShowNewProductDialog(true)} className="flex-1 sm:flex-none">
                  <Plus size={18} className="mr-2" />
                  Nuevo Producto
                </Button>
              </div>
            </div>

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
                  <ProductCard
                    key={product.id}
                    product={product}
                    onEdit={setEditingProduct}
                    onToggleActive={async (p) => {
                      const updated = await service.updateProduct(p.id, { ...p, activo: !p.activo })
                      setProducts(current => (current ?? []).map(pr => pr.id === updated.id ? updated : pr))
                      toast.success(`Producto ${updated.activo ? 'activado' : 'desactivado'}`)
                    }}
                  />
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
                  <OrderCard
                    key={order.id}
                    order={order}
                    onStatusChange={async (orderId, newStatus) => {
                      const updated = await service.updateOrderStatus(orderId, newStatus)
                      setOrders(current => (current ?? []).map(o => o.id === updated.id ? updated : o))
                      toast.success('Estado de orden actualizado')
                    }}
                  />
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
          
          for (const item of newOrder.items) {
            setProducts(current =>
              (current ?? []).map(p =>
                p.id === item.product_id
                  ? { ...p, stock_disponible: p.stock_disponible - item.cantidad }
                  : p
              )
            )
          }
          
          toast.success('Orden creada exitosamente')
          setShowNewOrderDialog(false)
        }}
      />

      <NewProfileDialog
        open={showNewProfileDialog}
        onOpenChange={setShowNewProfileDialog}
        onSubmit={async (name, slug) => {
          const created = await service.createProfile({ name, slug, active: true })
          setProfiles(current => [...(current ?? []), created])
          toast.success('Perfil creado exitosamente')
          setShowNewProfileDialog(false)
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

      <SettingsDialog
        open={showSettingsDialog}
        onOpenChange={setShowSettingsDialog}
      />

      <KeyboardShortcutsDialog
        open={showKeyboardDialog}
        onOpenChange={setShowKeyboardDialog}
      />
    </div>
  )
}
