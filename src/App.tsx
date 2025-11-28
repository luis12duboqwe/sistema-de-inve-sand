import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { ProductCard } from '@/components/ProductCard'
import { OrderCard } from '@/components/OrderCard'
import { NewOrderDialog } from '@/components/NewOrderDialog'
import { inventoryService } from '@/lib/inventoryService'
import {
  initialProfiles,
  initialProducts,
  initialStock,
  initialOrders,
  initialOrderItems
} from '@/lib/initialData'
import type { Profile, ProductWithStock, OrderWithItems, CreateOrderRequest, Order } from '@/lib/types'
import { MagnifyingGlass, Package, ShoppingCart, Plus } from '@phosphor-icons/react'
import { toast } from 'sonner'

function App() {
  const [activeTab, setActiveTab] = useState('products')
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [products, setProducts] = useState<ProductWithStock[]>([])
  const [orders, setOrders] = useState<OrderWithItems[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedProfile, setSelectedProfile] = useState<string>('all')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [isNewOrderOpen, setIsNewOrderOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    initializeData()
  }, [])

  useEffect(() => {
    if (!isLoading) {
      loadProducts()
    }
  }, [selectedProfile, searchTerm, selectedCategory, isLoading])

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
      let productsList = await inventoryService.fetchProducts(profileSlug, search)

      if (selectedCategory !== 'all') {
        productsList = productsList.filter(p => p.categoria === selectedCategory)
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

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Package size={48} className="mx-auto mb-4 text-primary animate-pulse" />
          <p className="text-muted-foreground">Cargando sistema...</p>
        </div>
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
          </TabsList>

          <TabsContent value="products" className="space-y-6">
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
              <Button onClick={() => setIsNewOrderOpen(true)} className="gap-2">
                <Plus size={20} />
                Nueva Orden
              </Button>
            </div>

            {products.length === 0 ? (
              <div className="text-center py-12">
                <Package size={64} className="mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">No hay productos disponibles</h3>
                <p className="text-muted-foreground">
                  {searchTerm
                    ? 'Intenta con otros términos de búsqueda'
                    : 'No hay productos en stock en este momento'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {products.map(product => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="orders" className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">
                Órdenes ({orders.length})
              </h2>
              <Button onClick={() => setIsNewOrderOpen(true)} className="gap-2">
                <Plus size={20} />
                Nueva Orden
              </Button>
            </div>

            {orders.length === 0 ? (
              <div className="text-center py-12">
                <ShoppingCart size={64} className="mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">No hay órdenes registradas</h3>
                <p className="text-muted-foreground mb-4">
                  Crea tu primera orden para comenzar
                </p>
                <Button onClick={() => setIsNewOrderOpen(true)} className="gap-2">
                  <Plus size={20} />
                  Crear Primera Orden
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {orders.map(order => (
                  <OrderCard
                    key={order.id}
                    order={order}
                    onStatusChange={handleStatusChange}
                  />
                ))}
              </div>
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
    </div>
  )
}

export default App