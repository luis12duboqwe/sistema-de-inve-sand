import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  SelectContent,
  Select
} from '@
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
import { MagnifyingGlass, Package, ShoppingCart, Plus, Storefront, Gear, Download, Database, CloudArrowUp, Keyboard, SortAscending, CheckSquare, Square } from '@phosphor-icons/react'
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
  const [orderSearchTerm, setOrderSearchTerm] = useState<string>('')
  const [useApi, setUseApi] = useState<boolean>(false)
      const apiEnabled = await window.spark.kv.get<boolean>('se
    }
  }, [isSettingsOpen])

      key: 'n',
      callback: () => {
          setIsNewProductOpen(true)
          setIsNewOrderOpen(true)
     
      },
    },

      callback: () => {
     
      descripti
    {
      ctrlKey: true,
      description: 'Abrir configuración
    {
      shiftKey: true,
      description: 'Mostrar atajo
  ])
  useEffect(() => {
  }, [])
  useEff
      loadProducts()
  }, [
  use
      loadOrder
  }, [activeTab, sel
  const initializeData 
      const existingProfiles = await inventoryService.listProfiles()
      if (existingProfiles.l
        
          initialStock,
      
     
      const pro
    } catch (error) 
      toast.error('Error al inicializar datos'
      setIsLoading(false)
  }
  con
      const pro
      let productsLis
      if (selectedCategory !== 'all') {
      }
      
    


        const max = 
        

      if (selectedW
        if (!isNaN(wa
        }

        productsList = [...productsList].sort((a, b) => {

            case 'p
            case 'name-asc':
            case '
     
          }

      setProducts(productsList)
      con
    }

    try {
      const ordersList = await inventoryServic
    } catch (error) {
      toast.error('Error a
  }
  const handleCreateOrde
      await inventoryServic
      awa
       

      toast.error(error instanceof Error ? error.message : 'Erro
    }

    try {
      toast.success('Estado actualizado')
    } catch (er
      toast.error('Error 
  }
  c

      await loadProducts()
      con
      throw error
  }
  const handleEditProduct = (product: ProductWithStock) => {


    try {
      i

      await loadProducts()
      console.error('Error updating prod
      throw error
  }
  const h
      c

    } catch (error) {
      toast.error('Error al cambiar esta
  }
  const handleCreateProfile = async (name: string, slug: string) =
      awa
      c

      toast.error(error instanceof Erro
    }

    setEditingProfile(profile)
  }
  const

      const profilesList = awa
      if (!active && selectedProfile === profiles.find(p 
      }
      console.error('Error up
      throw error
  }
  const getProfileStats = (profileId: nu
    const profileOrders = or
      productCount: profileProducts.length,
    }

    try {
        ? 'todos' 
      expor
    } catc
    }

    try {
        ? 'todas' 
      exportOrdersToCSV(orders, profileName)
    } catch (error) {
    }


        return false

        const hasCategory = order.items.some(item => item.product.categoria === o
          return false
      }
      if (orderSearch
        const customerName = String(order.customer_
        const matchesCustomerName = customer
     
   

    })

    setSelectedOrders(prev => {
      if (newSet.has(orderId)) {
      } else {
      }
    })

    const filteredOrd
      setSelectedOrders(new Set())
      setSelectedOrders(new Set(filteredOrders.map(o => o.id)))
  }
  con
   

      toast.success(`${selectedOrders.size} órdenes actualizadas a ${newStatus}`)
      awa
      console.error('Error updating orders in bulk:', error)
    }

    return (
        <motion.div 
          animate={{ opacity: 1, scale: 1 }}
     
   

            <Package size={48} className="mx-auto mb-4 text-primary" />
         
        </motion.div>
    )

    <div className="m
        <div className="max-w-7xl mx-auto px-4 py-6">
            <div>
                S
     
   

                <div className="flex items-center gap-2 px-3
                  <span classN
              ) : (
   

              <Button
         
                className="text-muted-foreground hover:text-fo
              >
              </Button>
       
                onClick={() => setIsSettingsOpen(true)}
                title="Con
                <Gear
              <Select value={selectedProfile} onValue
                  <SelectValue />
                <
     
   

              </Select>
         
      </header>
      <main className="max-w-7xl mx-auto px-4 py-8">
          <TabsList className="mb-6">
              <Package siz
            </TabsTri
              <ShoppingCart size={20} />
            </TabsTrigger>
     
   

            <DashboardStats products={products} orders={orders} />
         
                <div className="flex-1 relative">
                    size={20}
                  />
                    placeholder
                    o
                  />
                <Select value={selectedCategory} onValueChange={setSelectedCategory
                 
     
   

                <div className="flex items-center g
                    id="show-i
                    onCheckedC
   

                <Button 
         
                  disabled={products.length === 0}
                  <Download size={20} />
                </Button>
                  <Plus size={2
                </Button>
                  <Plus size={20}
       

                <div className="flex gap-2 items-cent
                  <Input
                 
     
   

                    type="number"
                    value={maxPrice}
                    className="w-28"
            
                    <Button
                      size="sm"
     
   

                    </Button>
         
                  <SelectTrigger className="w-full m
                  
                    <SelectItem value="all">Todas las garantías</SelectItem>
                    <SelectItem value="2">2 mese
                    <SelectItem value="6">6 meses</Selec
                  </S
                <Select value={sortBy} onValueCh
     
   

                          {sortBy ==
         
                      </div>
                  
                    <SelectItem value="none">Sin ordenar</SelectItem>
                    <SelectItem value="price
                    <SelectItem value="name-desc">Nomb
                </Sel
            </div>
     
   

                <Package size={64} 
                <p className="text-
                    ? 'Intenta con otros términos de búsqueda'
                </p>
       

                )}
            ) : (
                initial={{ 
                transi
         
       

                    transition={{ delay: index * 0.05,
                    <ProductCard 
                      onEdit={handleEditProduct}
                    />
                ))}
            )}

            <div class
         
       

                 
      
   

                    <Plus size={20} />
                  </Button>
              </div>
              <div className="fl
                  <MagnifyingG
              
                  <Input
       
                   
      
   

                    <SelectItem value="
                    <SelectItem value="por_ent
                    <SelectItem value="cancelada">Cancel
                </Select>
            
                  </SelectTrigger>
     
   


         
                  animate={{ opacity: 1, y: 0 }}
                >
       
                  <div className=
                  <Button
                    variant="outli
                    clas
                    P
                  <Button
                    variant="outline"
     
   

                  
            
                    Completada
                  <B
                    variant="outline"
                    className="bg-muted hove
                    Cancelada
                  <Button
         
                  >
                  </Button>
              )}

              <motion.div 
                animate
              >
                <h3 className="text-lg font-semibold mb-2">No hay órdenes registradas</h
                  Cre
            
     
   

          
                    size="sm"
                    className="gap-2 text-sm"
                    {selectedOrders.size === getFilte
                    ) : (
                 
                  </Button>
                <motion.div 
                  a
                  className="grid grid-cols-1 lg:grid-cols-2 gap
                  {getFilteredOrders().map((order, index) => (
                  
                  
                      className="relative"
                      <di
                          selectedOrders.has(order.id) ? 'scale-110' : 'hover:scale-105'
                        onClick={() => handleToggleOrder(order.id)}
                        {selectedOrders.has(order.id) ? (
                      
                   
                      <div className={`transition-all ${selectedOrders.has(order.id) ? 'ring-2 ring-primary ro
                          order={order}
                        />
                    </
                
            )}

            <div className=
                Perfiles de Negocio ({profiles.length})
              <Button onClick={() => setIsNewProfileOpen(true)} classNa
                Nuevo Perfil
            </d
            {profiles.length === 0 ? (
                initial
                class
                <Storefront siz
                <p classNam
                </p>
                  <Plus size={20} />
                </Button>
            ) :
                initial={{ opacity
                transit
              >
                  const stats = getProfileStats(
                    <motion.div
                      initial={{
                      transitio
                      <ProfileCard
                        productCount={stats.
                        onEdit={handleEditProfile}
                    </motion.div>
                })}
            )}
        </Tabs>

        open={isNe
        profiles
        onSubm


        profiles={profiles}
      />
      <EditProductDialog
        onOpenChange={setIsEditProductOpen}
        onSubmit={handleUpdateProdu

        open={isNewProfile
        onSubmit={handleCreateProfile}

        open={isEditP
        profile={editingPr
      />
      <SettingsDialog
        onOpenChange={

        open={isShort

  )

















































































































































































































































































































































































































































































