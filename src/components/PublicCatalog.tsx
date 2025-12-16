import { useState, useEffect } from 'react'
import { ShoppingCart, Search, Plus, Minus, Trash2, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { toast } from 'sonner'
import { useKV } from '@/hooks/use-kv'

// Types matching the backend PublicProductResponse
interface PublicProduct {
  id: number
  nombre: string
  marca: string
  modelo: string
  categoria: string
  condicion: string
  precio: number
  moneda: string
  capacidad?: string
  color?: string
  in_stock: boolean
}

interface CartItem extends PublicProduct {
  quantity: number
}

export default function PublicCatalog() {
  const [products, setProducts] = useState<PublicProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string>('all')
  const [cart, setCart] = useState<CartItem[]>([])
  const [isCartOpen, setIsCartOpen] = useState(false)
  const [apiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')

  // Fetch products
  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams()
        if (search) params.append('search', search)
        if (category && category !== 'all') params.append('category', category)
        params.append('per_page', '100') // Load plenty for the catalog

        // Use the configured API URL
        // Remove trailing slash if present to avoid double slashes
        const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl
        const url = `${baseUrl}/public/catalog?${params.toString()}`
        
        const response = await fetch(url)
        if (!response.ok) throw new Error('Error al cargar productos')
        
        const data = await response.json()
        setProducts(data.items)
      } catch (error) {
        console.error(error)
        toast.error('No se pudo cargar el catálogo')
      } finally {
        setLoading(false)
      }
    }

    const debounce = setTimeout(fetchProducts, 500)
    return () => clearTimeout(debounce)
  }, [search, category, apiUrl])

  // Cart Logic
  const addToCart = (product: PublicProduct) => {
    setCart(prev => {
      const existing = prev.find(item => item.id === product.id)
      if (existing) {
        return prev.map(item => 
          item.id === product.id 
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      }
      return [...prev, { ...product, quantity: 1 }]
    })
    toast.success('Agregado al carrito')
  }

  const removeFromCart = (productId: number) => {
    setCart(prev => prev.filter(item => item.id !== productId))
  }

  const updateQuantity = (productId: number, delta: number) => {
    setCart(prev => prev.map(item => {
      if (item.id === productId) {
        const newQty = item.quantity + delta
        return newQty > 0 ? { ...item, quantity: newQty } : item
      }
      return item
    }))
  }

  const cartTotal = cart.reduce((sum, item) => sum + (item.precio * item.quantity), 0)
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0)

  // WhatsApp Checkout
  const handleCheckout = () => {
    if (cart.length === 0) return

    let message = "Hola, me interesa ordenar los siguientes productos:\n\n"
    cart.forEach(item => {
      message += `• ${item.quantity}x ${item.marca} ${item.modelo} (${item.capacidad || ''}) - ${item.moneda} ${item.precio}\n`
    })
    message += `\nTotal Estimado: ${cart[0]?.moneda || 'HNL'} ${cartTotal.toLocaleString()}`
    message += "\n\n¿Me confirman disponibilidad?"

    const encodedMessage = encodeURIComponent(message)
    // Replace with actual business number
    const phoneNumber = "50499999999" 
    window.open(`https://wa.me/${phoneNumber}?text=${encodedMessage}`, '_blank')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
        <div className="container flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2 font-bold text-xl text-primary">
            <span>📱 Catálogo Digital</span>
          </div>
          
          <Sheet open={isCartOpen} onOpenChange={setIsCartOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon" className="relative">
                <ShoppingCart className="h-5 w-5" />
                {cartCount > 0 && (
                  <Badge className="absolute -top-2 -right-2 h-5 w-5 flex items-center justify-center rounded-full p-0">
                    {cartCount}
                  </Badge>
                )}
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Tu Carrito</SheetTitle>
              </SheetHeader>
              <div className="flex flex-col h-full pb-20">
                <ScrollArea className="flex-1 py-4">
                  {cart.length === 0 ? (
                    <div className="text-center text-muted-foreground py-10">
                      Tu carrito está vacío
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {cart.map(item => (
                        <div key={item.id} className="flex flex-col gap-2 border-b pb-4">
                          <div className="font-medium text-sm">
                            {item.marca} {item.modelo} {item.capacidad}
                          </div>
                          <div className="flex items-center justify-between">
                            <div className="text-sm text-muted-foreground">
                              {item.moneda} {item.precio.toLocaleString()}
                            </div>
                            <div className="flex items-center gap-2">
                              <Button variant="outline" size="icon" className="h-6 w-6" onClick={() => updateQuantity(item.id, -1)}>
                                <Minus className="h-3 w-3" />
                              </Button>
                              <span className="text-sm w-4 text-center">{item.quantity}</span>
                              <Button variant="outline" size="icon" className="h-6 w-6" onClick={() => updateQuantity(item.id, 1)}>
                                <Plus className="h-3 w-3" />
                              </Button>
                              <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive ml-2" onClick={() => removeFromCart(item.id)}>
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
                
                {cart.length > 0 && (
                  <div className="space-y-4 pt-4 border-t mt-auto">
                    <div className="flex justify-between font-bold text-lg">
                      <span>Total</span>
                      <span>{cart[0]?.moneda} {cartTotal.toLocaleString()}</span>
                    </div>
                    <Button className="w-full gap-2 bg-green-600 hover:bg-green-700" onClick={handleCheckout}>
                      <Send className="h-4 w-4" />
                      Pedir por WhatsApp
                    </Button>
                  </div>
                )}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-6 space-y-6">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar productos..."
              className="pl-8"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={category} onValueChange={setCategory}>
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

        {/* Product Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
              <Card key={n} className="animate-pulse">
                <div className="h-48 bg-gray-200 rounded-t-lg" />
                <CardContent className="p-4 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4" />
                  <div className="h-4 bg-gray-200 rounded w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {products.map((product) => (
              <Card key={product.id} className="flex flex-col overflow-hidden hover:shadow-lg transition-shadow">
                <div className="aspect-square bg-gray-100 flex items-center justify-center text-gray-400">
                  {/* Placeholder for image - in real app would be <img src={product.image} /> */}
                  <span className="text-4xl">📱</span>
                </div>
                <CardContent className="flex-1 p-4">
                  <div className="flex justify-between items-start mb-2">
                    <Badge variant="outline" className="capitalize">{product.condicion}</Badge>
                    {product.in_stock ? (
                      <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-100">Disponible</Badge>
                    ) : (
                      <Badge variant="destructive">Agotado</Badge>
                    )}
                  </div>
                  <h3 className="font-bold text-lg leading-tight mb-1">
                    {product.marca} {product.modelo}
                  </h3>
                  <p className="text-sm text-muted-foreground mb-2">
                    {product.capacidad} {product.color && `• ${product.color}`}
                  </p>
                  <div className="font-bold text-xl text-primary">
                    {product.moneda} {product.precio.toLocaleString()}
                  </div>
                </CardContent>
                <CardFooter className="p-4 pt-0">
                  <Button 
                    className="w-full" 
                    disabled={!product.in_stock}
                    onClick={() => addToCart(product)}
                  >
                    {product.in_stock ? 'Agregar al Carrito' : 'Sin Stock'}
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
