import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Plus, Trash } from '@phosphor-icons/react'
import type { OrderWithItems, ProductWithStock, Order } from '@/lib/types'
import { toast } from 'sonner'

interface EditOrderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  order: OrderWithItems
  products: ProductWithStock[]
  onSubmit: (orderId: number, updates: {
    customer_name: string
    customer_phone: string
    canal: Order['canal']
    metodo_pago: Order['metodo_pago']
    items: {
      product_id: number
      cantidad: number
    }[]
  }) => Promise<void>
}

interface OrderItemForm {
  product_id: number
  cantidad: number
}

export function EditOrderDialog({
  open,
  onOpenChange,
  order,
  products,
  onSubmit
}: EditOrderDialogProps) {
  const [customerName, setCustomerName] = useState(order.customer_name)
  const [customerPhone, setCustomerPhone] = useState(order.customer_phone)
  const [canal, setCanal] = useState<Order['canal']>(order.canal)
  const [metodoPago, setMetodoPago] = useState<Order['metodo_pago']>(order.metodo_pago)
  const [items, setItems] = useState<OrderItemForm[]>(
    order.items.map(item => ({
      product_id: item.product_id,
      cantidad: item.cantidad
    }))
  )
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (order) {
      setCustomerName(order.customer_name)
      setCustomerPhone(order.customer_phone)
      setCanal(order.canal)
      setMetodoPago(order.metodo_pago)
      setItems(
        order.items.map(item => ({
          product_id: item.product_id,
          cantidad: item.cantidad
        }))
      )
    }
  }, [order])

  const addItem = () => {
    setItems([...items, { product_id: 0, cantidad: 1 }])
  }

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const updateItemProduct = (index: number, productId: number) => {
    const newItems = [...items]
    newItems[index].product_id = productId
    setItems(newItems)
  }

  const updateItemQuantity = (index: number, cantidad: number) => {
    const newItems = [...items]
    newItems[index].cantidad = cantidad
    setItems(newItems)
  }

  const getAvailableProducts = (currentProductId: number) => {
    return products.filter(p => {
      if (p.id === currentProductId) return true
      const originalItem = order.items.find(oi => oi.product_id === p.id)
      const availableStock = p.stock_disponible + (originalItem?.cantidad || 0)
      return availableStock > 0
    })
  }

  const calculateTotal = () => {
    return items.reduce((total, item) => {
      const product = products.find(p => p.id === item.product_id)
      if (!product) return total
      return total + product.precio * item.cantidad
    }, 0)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!customerName.trim()) {
      toast.error('Por favor ingresa el nombre del cliente')
      return
    }

    if (!customerPhone.trim()) {
      toast.error('Por favor ingresa el teléfono del cliente')
      return
    }

    const validItems = items.filter(item => item.product_id > 0 && item.cantidad > 0)
    if (validItems.length === 0) {
      toast.error('Por favor agrega al menos un producto')
      return
    }

    for (const item of validItems) {
      const product = products.find(p => p.id === item.product_id)
      const originalItem = order.items.find(oi => oi.product_id === item.product_id)
      const originalQuantity = originalItem?.cantidad || 0
      const maxAvailable = (product?.stock_disponible || 0) + originalQuantity

      if (item.cantidad > maxAvailable) {
        toast.error(`Stock insuficiente para ${product?.nombre}. Disponible: ${maxAvailable}`)
        return
      }
    }

    setIsSubmitting(true)
    try {
      await onSubmit(order.id, {
        customer_name: customerName,
        customer_phone: customerPhone,
        canal,
        metodo_pago: metodoPago,
        items: validItems
      })
      onOpenChange(false)
    } catch (error) {
      console.error('Error updating order:', error)
      toast.error('Error al actualizar la orden')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar Orden #{order.id}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="edit-customer-name">Nombre del Cliente</Label>
              <Input
                id="edit-customer-name"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Juan Pérez"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-customer-phone">Teléfono</Label>
              <Input
                id="edit-customer-phone"
                type="tel"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="+504 9999-9999"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="edit-canal">Canal</Label>
              <Select value={canal} onValueChange={(v) => setCanal(v as typeof canal)}>
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
              <Select
                value={metodoPago}
                onValueChange={(v) => setMetodoPago(v as typeof metodoPago)}
              >
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

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Productos</Label>
              <Button type="button" variant="outline" size="sm" onClick={addItem}>
                <Plus size={16} className="mr-1" />
                Agregar Producto
              </Button>
            </div>

            {items.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No hay productos en esta orden</p>
                <Button type="button" variant="outline" size="sm" onClick={addItem} className="mt-2">
                  <Plus size={16} className="mr-1" />
                  Agregar Producto
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item, index) => {
                  const product = products.find(p => p.id === item.product_id)
                  const originalItem = order.items.find(oi => oi.product_id === item.product_id)
                  const originalQuantity = originalItem?.cantidad || 0
                  const maxAvailable = (product?.stock_disponible || 0) + originalQuantity

                  return (
                    <div key={index} className="flex items-end gap-2 p-3 border rounded-lg">
                      <div className="flex-1 space-y-2">
                        <Label className="text-sm">Producto</Label>
                        <Select
                          value={item.product_id.toString()}
                          onValueChange={(v) => updateItemProduct(index, parseInt(v))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Seleccionar producto" />
                          </SelectTrigger>
                          <SelectContent>
                            {getAvailableProducts(item.product_id).map(p => (
                              <SelectItem key={p.id} value={p.id.toString()}>
                                {p.nombre} - HNL {p.precio.toLocaleString()}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="w-32 space-y-2">
                        <Label className="text-sm">Cantidad</Label>
                        <Input
                          type="number"
                          min="1"
                          max={maxAvailable}
                          value={item.cantidad}
                          onChange={(e) => updateItemQuantity(index, parseInt(e.target.value) || 1)}
                        />
                      </div>

                      {product && (
                        <div className="w-32 space-y-2">
                          <Label className="text-sm">Subtotal</Label>
                          <div className="h-10 flex items-center px-3 bg-muted rounded-md">
                            <span className="text-sm font-medium">
                              HNL {(product.precio * item.cantidad).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      )}

                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={() => removeItem(index)}
                        className="mb-2"
                      >
                        <Trash size={18} />
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="pt-4 border-t">
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">Total:</span>
              <span className="text-2xl font-bold text-primary">
                HNL {calculateTotal().toLocaleString()}
              </span>
            </div>
          </div>
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Guardando...' : 'Guardar Cambios'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
