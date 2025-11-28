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
import { toast } from 'sonner'
import type { OrderWithItems, ProductWithStock } from '@/lib/types'
import { validatePhoneNumber } from '@/lib/phoneValidator'

interface EditOrderDialogProps {
  open: boolean
  order: OrderWithItems
  products: ProductWithStock[]
  onOpenChange: (open: boolean) => void
  onSubmit: (orderId: number, updates: {
    customer_name: string
    customer_phone: string
    canal: OrderWithItems['canal']
    metodo_pago: OrderWithItems['metodo_pago']
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
  order,
  products,
  onOpenChange,
  onSubmit
}: EditOrderDialogProps) {
  const [customerName, setCustomerName] = useState(order.customer_name)
  const [customerPhone, setCustomerPhone] = useState(order.customer_phone)
  const [canal, setCanal] = useState<OrderWithItems['canal']>(order.canal)
  const [metodoPago, setMetodoPago] = useState<OrderWithItems['metodo_pago']>(order.metodo_pago)
  const [items, setItems] = useState<OrderItemForm[]>(
    order.items.map(item => ({
      product_id: item.product_id,
      cantidad: item.cantidad
    }))
  )
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
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
  }, [open, order])

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

  const handleSubmit = async () => {
    if (!customerName.trim()) {
      toast.error('Por favor ingresa el nombre del cliente')
      return
    }

    const phoneValidation = validatePhoneNumber(customerPhone)
    if (!phoneValidation.valid) {
      toast.error(phoneValidation.error || 'El teléfono del cliente es inválido')
      return
    }

    const validItems = items.filter(item => item.product_id > 0 && item.cantidad > 0)
    if (validItems.length === 0) {
      toast.error('Por favor agrega al menos un producto a la orden')
      return
    }

    for (const item of validItems) {
      const product = products.find(p => p.id === item.product_id)
      if (!product) continue
      
      const originalItem = order.items.find(oi => oi.product_id === item.product_id)
      const originalQuantity = originalItem?.cantidad || 0
      const maxAvailable = product.stock_disponible + originalQuantity

      if (item.cantidad > maxAvailable) {
        toast.error(`Stock insuficiente para ${product.nombre}. Disponible: ${maxAvailable}`)
        return
      }
    }

    setIsSubmitting(true)
    try {
      await onSubmit(order.id, {
        customer_name: customerName,
        customer_phone: phoneValidation.phone,
        canal,
        metodo_pago: metodoPago,
        items: validItems
      })
      onOpenChange(false)
    } catch (error) {
      console.error('Error updating order:', error)
      setIsSubmitting(false)
      setIsSubmitting(false)
    }
  }
  return (
  return (en} onOpenChange={onOpenChange}>
    <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogHeader>
        <DialogHeader>Editar Orden #{order.id}</DialogTitle>
          <DialogTitle>Editar Orden #{order.id}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
        <div className="space-y-4 py-4">-2 gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">omer-name">Nombre del Cliente</Label>
              <Label htmlFor="edit-customer-name">Nombre del Cliente</Label>
              <Inputedit-customer-name"
                id="edit-customer-name"
                value={customerName}CustomerName(e.target.value)}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Juan Pérez"
              />v>
            </div>
            <div className="space-y-2">
            <div className="space-y-2">omer-phone">Teléfono</Label>
              <Label htmlFor="edit-customer-phone">Teléfono</Label>
              <Inputedit-customer-phone"
                id="edit-customer-phone"
                type="tel"tomerPhone}
                value={customerPhone}ustomerPhone(e.target.value)}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="+504 9999-9999"
              />v>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">l">Canal</Label>
              <Label htmlFor="edit-canal">Canal</Label>=> setCanal(v as typeof canal)}>
              <Select value={canal} onValueChange={(v) => setCanal(v as typeof canal)}>
                <SelectTrigger id="edit-canal">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>alue="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="facebook">Facebook</SelectItem>m>
                  <SelectItem value="instagram">Instagram</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
            <div className="space-y-2">do-pago">Método de Pago</Label>
              <Label htmlFor="edit-metodo-pago">Método de Pago</Label>
              <Select={metodoPago}
                value={metodoPago} => setMetodoPago(v as typeof metodoPago)}
                onValueChange={(v) => setMetodoPago(v as typeof metodoPago)}
              > <SelectTrigger id="edit-metodo-pago">
                <SelectTrigger id="edit-metodo-pago">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>alue="efectivo">Efectivo</SelectItem>
                  <SelectItem value="efectivo">Efectivo</SelectItem>electItem>
                  <SelectItem value="transferencia">Transferencia</SelectItem>
                  <SelectItem value="tarjeta">Tarjeta</SelectItem>o</SelectItem>
                  <SelectItem value="financiamiento">Financiamiento</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
          <div className="space-y-2">s-center justify-between">
            <div className="flex items-center justify-between">
              <Label>Productos</Label>riant="outline" size="sm" onClick={addItem}>
              <Button type="button" variant="outline" size="sm" onClick={addItem}>
                <Plus size={16} className="mr-1" />
                Agregar Producto
              </Button>
            </div>
            <div className="space-y-2">
            <div className="space-y-2">=> {
              {items.map((item, index) => {= getAvailableProducts(item.product_id)
                const availableForThisItem = getAvailableProducts(item.product_id)
                return (ey={index} className="flex items-end gap-2">
                  <div key={index} className="flex items-end gap-2">
                    <div className="flex-1 space-y-2">cto</Label>
                      <Label className="text-sm">Producto</Label>
                      <Select={item.product_id.toString()}
                        value={item.product_id.toString()}oduct(index, parseInt(v))}
                        onValueChange={(v) => updateItemProduct(index, parseInt(v))}
                      > <SelectTrigger>
                        <SelectTrigger>placeholder="Seleccionar producto" />
                          <SelectValue placeholder="Seleccionar producto" />
                        </SelectTrigger>
                        <SelectContent>ThisItem.map(product => {
                          {availableForThisItem.map(product => {d(oi => oi.product_id === product.id)
                            const originalItem = order.items.find(oi => oi.product_id === product.id) || 0)
                            const availableStock = product.stock_disponible + (originalItem?.cantidad || 0)
                            return (tItem key={product.id} value={product.id.toString()}>
                              <SelectItem key={product.id} value={product.id.toString()}>(Stock:{' '}
                                {product.nombre} - HNL {product.precio.toLocaleString()} (Stock:{' '}
                                {availableStock})
                              </SelectItem>
                            )
                          })}ectContent>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="w-24 space-y-2">
                    <div className="w-24 space-y-2">tidad</Label>
                      <Label className="text-sm">Cantidad</Label>
                      <Input="number"
                        type="number"
                        min="1"item.cantidad}
                        value={item.cantidad}teItemQuantity(index, parseInt(e.target.value) || 1)}
                        onChange={(e) => updateItemQuantity(index, parseInt(e.target.value) || 1)}
                        placeholder="Cant."
                      />v>
                    </div>
                    {items.length > 1 && (
                    {items.length > 1 && (
                      <Button"button"
                        type="button"ine"
              </span>
                        size="icon"
                        onClick={() => removeItem(index)}
        </div>
                      >
        <DialogFooter>
                      </Button>ine" onClick={() => onOpenChange(false)}>
                    )}
                  </div>
                ) onClick={handleSubmit} disabled={isSubmitting}>
              })}bmitting ? 'Guardando...' : 'Guardar Cambios'}
            </div>>
          </div>Footer>
      </DialogContent>
          <div className="pt-4 border-t">
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">Total:</span>
              <span className="text-2xl font-bold text-primary">                HNL {calculateTotal().toLocaleString()}              </span>            </div>          </div>        </div>      </DialogContent>    </Dialog>  )}