import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import type { OrderWithItems, ProductWithStock, Order } from '@/lib/types'
import { Trash, Plus } from '@phosphor-icons/react'

interface EditOrderDialogProps {
  open: boolean
  order: OrderWithItems
  products: ProductWithStock[]
  onOpenChange: (open: boolean) => void
  onSubmit: (orderId: number, updates: {
    customer_name: string
    customer_phone: string
    canal: Order['canal']
    metodo_pago: Order['metodo_pago']
    items: Array<{
      id?: number
      product_id: number
      cantidad: number
    }>
  }) => Promise<void>
}

export function EditOrderDialog({ open, order, products, onOpenChange, onSubmit }: EditOrderDialogProps) {
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [canal, setCanal] = useState<Order['canal']>('whatsapp')
  const [metodoPago, setMetodoPago] = useState<Order['metodo_pago']>('efectivo')
  const [items, setItems] = useState<Array<{
    id?: number
    product_id: number
    cantidad: number
  }>>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (order) {
      setCustomerName(order.customer_name)
      setCustomerPhone(order.customer_phone)
      setCanal(order.canal)
      setMetodoPago(order.metodo_pago)
      setItems(order.items.map(item => ({
        id: item.id,
        product_id: item.product_id,
        cantidad: item.cantidad
      })))
    }
  }, [order])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!customerName.trim() || !customerPhone.trim()) {
      return
    }

    if (items.length === 0) {
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit(order.id, {
        customer_name: customerName.trim(),
        customer_phone: customerPhone.trim(),
        canal,
        metodo_pago: metodoPago,
        items
      })
      onOpenChange(false)
    } catch (error) {
      console.error('Error updating order:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const addItem = () => {
    const availableProduct = products.find(p => 
      !items.some(item => item.product_id === p.id) && p.stock_disponible > 0
    )
    
    if (availableProduct) {
      setItems([...items, { product_id: availableProduct.id, cantidad: 1 }])
    }
  }

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const updateItemProduct = (index: number, productId: number) => {
    const newItems = [...items]
    newItems[index] = { ...newItems[index], product_id: productId, cantidad: 1 }
    setItems(newItems)
  }

  const updateItemQuantity = (index: number, cantidad: number) => {
    const newItems = [...items]
    newItems[index] = { ...newItems[index], cantidad }
    setItems(newItems)
  }

  const calculateTotal = () => {
    return items.reduce((sum, item) => {
      const product = products.find(p => p.id === item.product_id)
      return sum + (product?.precio || 0) * item.cantidad
    }, 0)
  }

  const getAvailableProducts = (currentProductId?: number) => {
    return products.filter(p => {
      if (p.id === currentProductId) return true
      const isAlreadySelected = items.some(item => item.product_id === p.id)
      return !isAlreadySelected && p.stock_disponible > 0
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar Orden #{order.id}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="edit-customer-name">Nombre del Cliente *</Label>
              <Input
                id="edit-customer-name"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Nombre completo"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-customer-phone">Teléfono *</Label>
              <Input
                id="edit-customer-phone"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="########"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-canal">Canal</Label>
              <Select value={canal} onValueChange={(value) => setCanal(value as Order['canal'])}>
                <SelectTrigger id="edit-canal">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="facebook">Facebook</SelectItem>
                  <SelectItem value="instagram">Instagram</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-metodo-pago">Método de Pago</Label>
              <Select value={metodoPago} onValueChange={(value) => setMetodoPago(value as Order['metodo_pago'])}>
                <SelectTrigger id="edit-metodo-pago">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="efectivo">Efectivo</SelectItem>
                  <SelectItem value="transferencia">Transferencia</SelectItem>
                  <SelectItem value="tarjeta">Tarjeta</SelectItem>
                  <SelectItem value="financiamiento">Financiamiento</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Productos *</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addItem}
                disabled={items.length >= products.length || getAvailableProducts().length === 0}
              >
                <Plus size={16} className="mr-2" />
                Agregar Producto
              </Button>
            </div>

            {items.length === 0 ? (
              <div className="text-center py-8 border-2 border-dashed rounded-lg">
                <p className="text-sm text-muted-foreground">
                  Agrega al menos un producto a la orden
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item, index) => {
                  const product = products.find(p => p.id === item.product_id)
                  const availableProducts = getAvailableProducts(item.product_id)
                  const maxQuantity = product?.stock_disponible || 0
                  const originalItem = order.items.find(oi => oi.product_id === item.product_id)
                  const originalQuantity = originalItem?.cantidad || 0
                  const maxAvailable = maxQuantity + originalQuantity

                  return (
                    <div key={index} className="flex gap-3 items-start p-4 border rounded-lg">
                      <div className="flex-1 space-y-3">
                        <div className="space-y-2">
                          <Label className="text-xs">Producto</Label>
                          <Select
                            value={String(item.product_id)}
                            onValueChange={(value) => updateItemProduct(index, Number(value))}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {availableProducts.map(p => (
                                <SelectItem key={p.id} value={String(p.id)}>
                                  {p.nombre} - {p.marca} ({p.stock_disponible} disponibles)
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-2">
                            <Label className="text-xs">Cantidad</Label>
                            <Input
                              type="number"
                              min="1"
                              max={maxAvailable}
                              value={item.cantidad}
                              onChange={(e) => updateItemQuantity(index, parseInt(e.target.value) || 1)}
                            />
                            <p className="text-xs text-muted-foreground">
                              Máx: {maxAvailable}
                            </p>
                          </div>

                          <div className="space-y-2">
                            <Label className="text-xs">Subtotal</Label>
                            <div className="h-10 flex items-center">
                              <Badge variant="secondary" className="text-sm">
                                HNL {((product?.precio || 0) * item.cantidad).toLocaleString()}
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </div>

                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeItem(index)}
                        className="mt-6"
                      >
                        <Trash size={18} />
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-4 border-t">
            <div>
              <p className="text-sm text-muted-foreground">Total de la Orden</p>
              <p className="text-2xl font-bold text-primary">
                HNL {calculateTotal().toLocaleString()}
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting || items.length === 0}>
              {isSubmitting ? 'Guardando...' : 'Guardar Cambios'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
