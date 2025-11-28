import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { ProductCard } from '@/components/ProductCard'
import { OrderCard } from '@/components/OrderCard'
import { ProfileCard } from '@/components/ProfileCard'
import { DashboardStats } from '@/components/DashboardStats'
import { NewOrderDialog } from '@/components/NewOrderDialog'
import { NewProductDialog } from '@/components/NewProductDialog'
import { EditProductDialog } from '@/components/EditProductDialog'
import { NewProfileDialog } from '@/components/NewProfileDialog'
import { EditProfileDialog } from '@/components/EditProfileDialog'
import { SettingsDialog } from '@/components/SettingsDialog'
import { KeyboardShortcutsDialog } from '@/components/KeyboardShortcutsDialog'
import { inventoryServiceInstance as inventoryService } from '@/lib/inventoryServiceFactory'
import {
  initialProfiles,
  initialProducts,
  initialStock,
  initialOrders,
  initialOrderItems
} from '@/lib/initialData'
import type { Profile, ProductWithStock, OrderWithItems, CreateOrderRequest, Order, Product } from '@/lib/types'
import { MagnifyingGlass, Package, ShoppingCart, Plus, Storefront, Gear, Download, Database, CloudArrowUp, Keyboard, SortAscending } from '@phosphor-icons/react'
import { toast } from 'sonner'
import { motion } from 'framer-motion'
import { exportProductsToCSV, exportOrdersToCSV } from '@/lib/exportUtils'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'

function App() {
  const [activeTab, setActiveTab] = useState('products')
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [products, setProducts] = useState<ProductWithStock[]>([])
  const [orders, setOrders] = useState<OrderWithItems[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedProfile, setSelectedProfile] = useState<string>('all')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [showInactive, setShowInactive] = useState(false)
  const [minPrice, setMinPrice] = useState<string>('')
  const [maxPrice, setMaxPrice] = useState<string>('')
  const [selectedWarranty, setSelectedWarranty] = useState<string>('all')
  const [isNewOrderOpen, setIsNewOrderOpen] = useState(false)
  const [isNewProductOpen, setIsNewProductOpen] = useState(false)
  const [isEditProductOpen, setIsEditProductOpen] = useState(false)
  const [isNewProfileOpen, setIsNewProfileOpen] = useState(false)
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false)
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<ProductWithStock | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [orderStatusFilter, setOrderStatusFilter] = useState<string>('all')
  const [orderCategoryFilter, setOrderCategoryFilter] = useState<string>('all')
  const [useApi, setUseApi] = useState<boolean>(false)
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false)
  const [sortBy, setSortBy] = useState<string>('none')

  useEffect(() => {
    const checkApiStatus = async () => {
      const apiEnabled = await window.spark.kv.get<boolean>('settings_use_api')
      setUseApi(apiEnabled ?? false)
    }
    checkApiStatus()
  }, [isSettingsOpen])

  useKeyboardShortcuts([
    {
      key: 'n',
      ctrlKey: true,
      callback: () => {
        if (activeTab === 'products') {
          setIsNewProductOpen(true)
        } else if (activeTab === 'orders') {
          setIsNewOrderOpen(true)
        } else if (activeTab === 'profiles') {
          setIsNewProfileOpen(true)
        }
      },
      description: 'Crear nuevo elemento en la pestaña actual',
    },
    {
      key: 'k',
      ctrlKey: true,
      callback: () => {
        const searchInput = document.querySelector('input[placeholder*="Buscar"]') as HTMLInputElement
        searchInput?.focus()
      },
      description: 'Enfocar búsqueda',
    },
    {
      key: ',',
      ctrlKey: true,
      callback: () => setIsSettingsOpen(true),
      description: 'Abrir configuración',
    },
    {
      key: '?',
      shiftKey: true,
      callback: () => setIsShortcutsOpen(true),
      description: 'Mostrar atajos de teclado',
    },
  ])

  useEffect(() => {
    initializeData()
  }, [])

  useEffect(() => {
    if (!isLoading) {
      loadProducts()
    }
  }, [selectedProfile, searchTerm, selectedCategory, showInactive, minPrice, maxPrice, selectedWarranty, sortBy, isLoading])

  useEffect(() => {
    if (!isLoading && activeTab === 'orders') {
      loadOrders()
    }
  }, [activeTab, selectedProfile, isLoading])

  const initializeData = async () => {
    try {
      const existingProfiles = await inventoryService.listProfiles()
      
      if (existingProfiles.length === 0) {
        await inventoryService.initializeData(
          initialProfiles,
          initialProducts,
          initialStock,
          initialOrders,
          initialOrderItems
        )
      }

      const profilesList = await inventoryService.listProfiles()
      setProfiles(profilesList)
    } catch (error) {
      console.error('Error initializing data:', error)
      toast.error('Error al inicializar datos')
    } finally {
      setIsLoading(false)
    }
  }

  const loadProducts = async () => {
    try {
      const profileSlug = selectedProfile === 'all' ? undefined : selectedProfile
      const search = searchTerm.trim() || undefined
      let productsList = await inventoryService.fetchProducts(profileSlug, search, showInactive)

      if (selectedCategory !== 'all') {
        productsList = productsList.filter(p => p.categoria === selectedCategory)
      }

      if (minPrice !== '') {
        const min = parseFloat(minPrice)
        if (!isNaN(min)) {
          productsList = productsList.filter(p => p.precio >= min)
        }
      }

      if (maxPrice !== '') {
        const max = parseFloat(maxPrice)
        if (!isNaN(max)) {
          productsList = productsList.filter(p => p.precio <= max)
        }
      }

      if (selectedWarranty !== 'all') {
        const warranty = parseInt(selectedWarranty)
        if (!isNaN(warranty)) {
          productsList = productsList.filter(p => p.garantia_meses === warranty)
        }
      }

      if (sortBy !== 'none') {
        productsList = [...productsList].sort((a, b) => {
          switch (sortBy) {
            case 'price-asc':
              return a.precio - b.precio
            case 'price-desc':
              return b.precio - a.precio
            case 'name-asc':
              return a.nombre.localeCompare(b.nombre)
            case 'name-desc':
              return b.nombre.localeCompare(a.nombre)
            default:
              return 0
          }
        })
      }

      setProducts(productsList)
    } catch (error) {
      console.error('Error loading products:', error)
      toast.error('Error al cargar productos')
    }
  }

  const loadOrders = async () => {
    try {
      const profileSlug = selectedProfile === 'all' ? undefined : selectedProfile
      const ordersList = await inventoryService.fetchOrders(profileSlug)
      setOrders(ordersList)
    } catch (error) {
      console.error('Error loading orders:', error)
      toast.error('Error al cargar órdenes')
    }
  }

  const handleCreateOrder = async (orderRequest: CreateOrderRequest) => {
    try {
      await inventoryService.createOrder(orderRequest)
      toast.success('Orden creada exitosamente')
      await loadProducts()
      if (activeTab === 'orders') {
        await loadOrders()
      }
    } catch (error) {
      console.error('Error creating order:', error)
      toast.error(error instanceof Error ? error.message : 'Error al crear orden')
      throw error
    }
  }

  const handleStatusChange = async (orderId: number, newStatus: Order['estado']) => {
    try {
      await inventoryService.updateOrderStatus(orderId, newStatus)
      toast.success('Estado actualizado')
      await loadOrders()
    } catch (error) {
      console.error('Error updating order status:', error)
      toast.error('Error al actualizar estado')
    }
  }

  const handleCreateProduct = async (product: Omit<Product, 'id' | 'activo'>, stock: number) => {
    try {
      await inventoryService.addProduct({ ...product, activo: true }, stock)
      toast.success('Producto agregado exitosamente')
      await loadProducts()
    } catch (error) {
      console.error('Error creating product:', error)
      toast.error(error instanceof Error ? error.message : 'Error al agregar producto')
      throw error
    }
  }

  const handleEditProduct = (product: ProductWithStock) => {
    setEditingProduct(product)
    setIsEditProductOpen(true)
  }

  const handleUpdateProduct = async (productId: number, updates: Partial<Product>, newStock?: number) => {
    try {
      await inventoryService.updateProduct(productId, updates)
      if (newStock !== undefined) {
        await inventoryService.updateStock(productId, newStock)
      }
      toast.success('Producto actualizado exitosamente')
      await loadProducts()
    } catch (error) {
      console.error('Error updating product:', error)
      toast.error(error instanceof Error ? error.message : 'Error al actualizar producto')
      throw error
    }
  }

  const handleToggleProductActive = async (product: ProductWithStock) => {
    try {
      const newActiveState = !product.activo
      await inventoryService.updateProduct(product.id, { activo: newActiveState })
      toast.success(newActiveState ? 'Producto activado' : 'Producto desactivado')
      await loadProducts()
    } catch (error) {
      console.error('Error toggling product status:', error)
      toast.error('Error al cambiar estado del producto')
    }
  }

  const handleCreateProfile = async (name: string, slug: string) => {
    try {
      await inventoryService.createProfile(name, slug)
      toast.success('Perfil creado exitosamente')
      const profilesList = await inventoryService.listProfiles()
      setProfiles(profilesList)
    } catch (error) {
      console.error('Error creating profile:', error)
      toast.error(error instanceof Error ? error.message : 'Error al crear perfil')
      throw error
    }
  }

  const handleEditProfile = (profile: Profile) => {
    setEditingProfile(profile)
    setIsEditProfileOpen(true)
  }

  const handleUpdateProfile = async (profileId: number, name: string, active: boolean) => {
    try {
      await inventoryService.updateProfile(profileId, { name, active })
      toast.success('Perfil actualizado exitosamente')
      const profilesList = await inventoryService.listProfiles()
      setProfiles(profilesList)
      if (!active && selectedProfile === profiles.find(p => p.id === profileId)?.slug) {
        setSelectedProfile('all')
      }
    } catch (error) {
      console.error('Error updating profile:', error)
      toast.error(error instanceof Error ? error.message : 'Error al actualizar perfil')
      throw error
    }
  }

  const getProfileStats = (profileId: number) => {
    const profileProducts = products.filter(p => p.profile_id === profileId)
    const profileOrders = orders.filter(o => o.profile_id === profileId)
    return {
      productCount: profileProducts.length,
      orderCount: profileOrders.length
    }
  }

  const handleExportProducts = () => {
    try {
      const profileName = selectedProfile === 'all' 
        ? 'todos' 
        : profiles.find(p => p.slug === selectedProfile)?.name || 'desconocido'
      exportProductsToCSV(products, profileName)
      toast.success('Productos exportados exitosamente')
    } catch (error) {
      toast.error('Error al exportar productos')
    }
  }

  const handleExportOrders = () => {
    try {
      const profileName = selectedProfile === 'all' 
        ? 'todas' 
        : profiles.find(p => p.slug === selectedProfile)?.name || 'desconocido'
      exportOrdersToCSV(orders, profileName)
      toast.success('Órdenes exportadas exitosamente')
    } catch (error) {
      toast.error('Error al exportar órdenes')
    }
  }

  const getFilteredOrders = () => {
    return orders.filter(order => {
      if (orderStatusFilter !== 'all' && order.estado !== orderStatusFilter) {
        return false
      }

      if (orderCategoryFilter !== 'all') {
        const hasCategory = order.items.some(item => item.product.categoria === orderCategoryFilter)
        if (!hasCategory) {
          return false
        }
      }

      return true
    })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="text-center"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            <Package size={48} className="mx-auto mb-4 text-primary" />
          </motion.div>
          <p className="text-lg font-medium text-foreground">Cargando sistema...</p>
          <p className="text-sm text-muted-foreground mt-2">Inicializando inventario</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-foreground tracking-tight">
                Sistema de Inventario
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Gestión de productos y órdenes para chatbots de ventas
              </p>
            </div>
            <div className="flex items-center gap-3">
              {useApi ? (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-accent/10 border border-accent/20">
                  <CloudArrowUp size={16} className="text-accent" />
                  <span className="text-xs font-medium text-accent">API</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted border border-border">
                  <Database size={16} className="text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">Local</span>
                </div>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsShortcutsOpen(true)}
                className="text-muted-foreground hover:text-foreground"
                title="Atajos de teclado (Shift + ?)"
              >
                <Keyboard size={20} />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsSettingsOpen(true)}
                className="text-muted-foreground hover:text-foreground"
                title="Configuración (Ctrl + ,)"
              >
                <Gear size={20} />
              </Button>
              <Select value={selectedProfile} onValueChange={setSelectedProfile}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los perfiles</SelectItem>
                  {profiles.map(profile => (
                    <SelectItem key={profile.id} value={profile.slug}>
                      {profile.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="products" className="gap-2">
              <Package size={20} />
              Productos
            </TabsTrigger>
            <TabsTrigger value="orders" className="gap-2">
              <ShoppingCart size={20} />
              Órdenes
            </TabsTrigger>
            <TabsTrigger value="profiles" className="gap-2">
              <Storefront size={20} />
              Perfiles
            </TabsTrigger>
          </TabsList>

          <TabsContent value="products" className="space-y-6">
            <DashboardStats products={products} orders={orders} />
            
            <div className="flex flex-col gap-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <MagnifyingGlass
                    size={20}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />
                  <Input
                    placeholder="Buscar por nombre, marca o modelo..."
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                  <SelectTrigger className="w-full md:w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas las categorías</SelectItem>
                    <SelectItem value="celular">Celulares</SelectItem>
                    <SelectItem value="accesorio">Accesorios</SelectItem>
                  </SelectContent>
                </Select>
                <div className="flex items-center gap-2 px-3 border rounded-md">
                  <Switch
                    id="show-inactive"
                    checked={showInactive}
                    onCheckedChange={setShowInactive}
                  />
                  <Label htmlFor="show-inactive" className="cursor-pointer text-sm">
                    Mostrar inactivos
                  </Label>
                </div>
                <Button 
                  onClick={handleExportProducts} 
                  variant="outline" 
                  className="gap-2"
                  disabled={products.length === 0}
                >
                  <Download size={20} />
                  Exportar
                </Button>
                <Button onClick={() => setIsNewProductOpen(true)} variant="outline" className="gap-2">
                  <Plus size={20} />
                  Nuevo Producto
                </Button>
                <Button onClick={() => setIsNewOrderOpen(true)} className="gap-2">
                  <Plus size={20} />
                  Nueva Orden
                </Button>
              </div>

              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex gap-2 items-center">
                  <Label className="text-sm font-medium whitespace-nowrap">Rango de precio:</Label>
                  <Input
                    type="number"
                    placeholder="Min"
                    value={minPrice}
                    onChange={e => setMinPrice(e.target.value)}
                    className="w-28"
                    min="0"
                  />
                  <span className="text-muted-foreground">-</span>
                  <Input
                    type="number"
                    placeholder="Max"
                    value={maxPrice}
                    onChange={e => setMaxPrice(e.target.value)}
                    className="w-28"
                    min="0"
                  />
                  {(minPrice || maxPrice) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setMinPrice('')
                        setMaxPrice('')
                      }}
                      className="h-8 px-2"
                    >
                      Limpiar
                    </Button>
                  )}
                </div>
                <Select value={selectedWarranty} onValueChange={setSelectedWarranty}>
                  <SelectTrigger className="w-full md:w-52">
                    <SelectValue placeholder="Garantía" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas las garantías</SelectItem>
                    <SelectItem value="0">Sin garantía</SelectItem>
                    <SelectItem value="2">2 meses</SelectItem>
                    <SelectItem value="3">3 meses</SelectItem>
                    <SelectItem value="6">6 meses</SelectItem>
                    <SelectItem value="12">12 meses</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={sortBy} onValueChange={setSortBy}>
                  <SelectTrigger className="w-full md:w-52">
                    <SelectValue>
                      <div className="flex items-center gap-2">
                        <SortAscending size={16} />
                        <span>
                          {sortBy === 'none' && 'Ordenar por'}
                          {sortBy === 'price-asc' && 'Precio: Menor a Mayor'}
                          {sortBy === 'price-desc' && 'Precio: Mayor a Menor'}
                          {sortBy === 'name-asc' && 'Nombre: A - Z'}
                          {sortBy === 'name-desc' && 'Nombre: Z - A'}
                        </span>
                      </div>
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin ordenar</SelectItem>
                    <SelectItem value="price-asc">Precio: Menor a Mayor</SelectItem>
                    <SelectItem value="price-desc">Precio: Mayor a Menor</SelectItem>
                    <SelectItem value="name-asc">Nombre: A - Z</SelectItem>
                    <SelectItem value="name-desc">Nombre: Z - A</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {products.length === 0 ? (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                <Package size={64} className="mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">No hay productos disponibles</h3>
                <p className="text-muted-foreground mb-4">
                  {searchTerm
                    ? 'Intenta con otros términos de búsqueda'
                    : 'Agrega tu primer producto para comenzar'}
                </p>
                {!searchTerm && (
                  <Button onClick={() => setIsNewProductOpen(true)} className="gap-2">
                    <Plus size={20} />
                    Agregar Primer Producto
                  </Button>
                )}
              </motion.div>
            ) : (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              >
                {products.map((product, index) => (
                  <motion.div
                    key={product.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05, duration: 0.2 }}
                  >
                    <ProductCard 
                      product={product} 
                      onEdit={handleEditProduct}
                      onToggleActive={handleToggleProductActive}
                    />
                  </motion.div>
                ))}
              </motion.div>
            )}
          </TabsContent>

          <TabsContent value="orders" className="space-y-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <h2 className="text-xl font-semibold">
                  Órdenes ({getFilteredOrders().length})
                </h2>
                <Select value={orderStatusFilter} onValueChange={setOrderStatusFilter}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los estados</SelectItem>
                    <SelectItem value="pendiente">Pendiente</SelectItem>
                    <SelectItem value="por_entregar">Por Entregar</SelectItem>
                    <SelectItem value="completada">Completada</SelectItem>
                    <SelectItem value="cancelada">Cancelada</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={orderCategoryFilter} onValueChange={setOrderCategoryFilter}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas las categorías</SelectItem>
                    <SelectItem value="celular">Celulares</SelectItem>
                    <SelectItem value="accesorio">Accesorios</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button 
                  onClick={handleExportOrders} 
                  variant="outline" 
                  className="gap-2"
                  disabled={orders.length === 0}
                >
                  <Download size={20} />
                  Exportar
                </Button>
                <Button onClick={() => setIsNewOrderOpen(true)} className="gap-2">
                  <Plus size={20} />
                  Nueva Orden
                </Button>
              </div>
            </div>

            {getFilteredOrders().length === 0 ? (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                <ShoppingCart size={64} className="mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">No hay órdenes registradas</h3>
                <p className="text-muted-foreground mb-4">
                  Crea tu primera orden para comenzar a gestionar ventas
                </p>
                <Button onClick={() => setIsNewOrderOpen(true)} className="gap-2">
                  <Plus size={20} />
                  Crear Primera Orden
                </Button>
              </motion.div>
            ) : (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-6"
              >
                {getFilteredOrders().map((order, index) => (
                  <motion.div
                    key={order.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05, duration: 0.2 }}
                  >
                    <OrderCard
                      order={order}
                      onStatusChange={handleStatusChange}
                    />
                  </motion.div>
                ))}
              </motion.div>
            )}
          </TabsContent>

          <TabsContent value="profiles" className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">
                Perfiles de Negocio ({profiles.length})
              </h2>
              <Button onClick={() => setIsNewProfileOpen(true)} className="gap-2">
                <Plus size={20} />
                Nuevo Perfil
              </Button>
            </div>

            {profiles.length === 0 ? (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                <Storefront size={64} className="mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">No hay perfiles registrados</h3>
                <p className="text-muted-foreground mb-4">
                  Crea tu primer perfil de negocio para comenzar a gestionar inventario
                </p>
                <Button onClick={() => setIsNewProfileOpen(true)} className="gap-2">
                  <Plus size={20} />
                  Crear Primer Perfil
                </Button>
              </motion.div>
            ) : (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              >
                {profiles.map((profile, index) => {
                  const stats = getProfileStats(profile.id)
                  return (
                    <motion.div
                      key={profile.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05, duration: 0.2 }}
                    >
                      <ProfileCard
                        profile={profile}
                        productCount={stats.productCount}
                        orderCount={stats.orderCount}
                        onEdit={handleEditProfile}
                      />
                    </motion.div>
                  )
                })}
              </motion.div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      <NewOrderDialog
        open={isNewOrderOpen}
        onOpenChange={setIsNewOrderOpen}
        profiles={profiles}
        products={products}
        onSubmit={handleCreateOrder}
      />

      <NewProductDialog
        open={isNewProductOpen}
        onOpenChange={setIsNewProductOpen}
        profiles={profiles}
        onSubmit={handleCreateProduct}
      />

      <EditProductDialog
        open={isEditProductOpen}
        onOpenChange={setIsEditProductOpen}
        product={editingProduct}
        onSubmit={handleUpdateProduct}
      />

      <NewProfileDialog
        open={isNewProfileOpen}
        onOpenChange={setIsNewProfileOpen}
        onSubmit={handleCreateProfile}
      />

      <EditProfileDialog
        open={isEditProfileOpen}
        onOpenChange={setIsEditProfileOpen}
        profile={editingProfile}
        onSubmit={handleUpdateProfile}
      />

      <SettingsDialog
        open={isSettingsOpen}
        onOpenChange={setIsSettingsOpen}
      />

      <KeyboardShortcutsDialog
        open={isShortcutsOpen}
        onOpenChange={setIsShortcutsOpen}
      />
    </div>
  )
}

export default App