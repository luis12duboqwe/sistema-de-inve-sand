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
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogTitle>Editar Orden #{order.id}</DialogTitle>

        <div className="space-y-4 py-4">

            <div className="space-y-2">
              <Input
            <div className="space-y-2">
                value={customerName}
              <Inputalue)}
                placeholder="Juan Pérez"
                value={customerName}
            </div>

              />y-2">
              <Label htmlFor="edit-customer-phone">Teléfono</Label>

                id="edit-customer-phone"
                value={customerPhone}
              <Inputalue)}
                placeholder="+504 9999-9999"
                type="tel"
                value={customerPhone}
          </div>

              />d-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="edit-canal">Canal</Label>
{(v) => setCanal(v as typeof canal)}>
                <SelectTrigger id="edit-canal">
            <div className="space-y-2">
              <Label htmlFor="edit-canal">Canal</Label>
                <SelectContent>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="facebook">Facebook</SelectItem>
                  <SelectItem value="instagram">Instagram</SelectItem>
                <SelectContent>
              </Select>
                  <SelectItem value="facebook">Facebook</SelectItem>

            <div className="space-y-2">
              <Label htmlFor="edit-metodo-pago">Método de Pago</Label>
              <Select

                onValueChange={(v) => setMetodoPago(v as typeof metodoPago)}
                <SelectTrigger id="edit-metodo-pago">
              <Select
                value={metodoPago}
                <SelectContent>
              >
                  <SelectItem value="transferencia">Transferencia</SelectItem>
                  <SelectItem value="tarjeta">Tarjeta</SelectItem>
                  <SelectItem value="financiamiento">Financiamiento</SelectItem>
                <SelectContent>
                  <SelectItem value="efectivo">Efectivo</SelectItem>
            </div>
                  <SelectItem value="tarjeta">Tarjeta</SelectItem>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Productos</Label>
              <Button type="button" variant="outline" size="sm" onClick={addItem}>

                Agregar Producto
            </div>
              <Label>Productos</Label>
            <div className="space-y-2">
              {items.map((item, index) => {
                const availableForThisItem = getAvailableProducts(item.product_id)
                return (
                  <div key={index} className="flex items-end gap-2">

                      <Label className="text-sm">Producto</Label>
              {items.map((item, index) => {
                        onValueChange={(v) => updateItemProduct(index, parseInt(v))}
                return (
                        <SelectTrigger>
                    <div className="flex-1 space-y-2">
                        </SelectTrigger>
                      <Select
                        value={item.product_id.toString()}
                            const originalItem = order.items.find(oi => oi.product_id === product.id)
                      >ck_disponible + (originalItem?.cantidad || 0)
                        <SelectTrigger>
                              <SelectItem key={product.id} value={product.id.toString()}>
                                {product.nombre} - HNL {product.precio.toLocaleString()} (Stock:{' '}
                        <SelectContent>
                          {availableForThisItem.map(product => {
                            const originalItem = order.items.find(oi => oi.product_id === product.id)
                          })}
                            return (
                              <SelectItem key={product.id} value={product.id.toString()}>
                    </div>

                    <div className="w-24 space-y-2">
                      <Label className="text-sm">Cantidad</Label>
                          })}
                        type="number"
                        min="1"
                        value={item.cantidad}

                        placeholder="Cant."
                    </div>
                      <Input
                    {items.length > 1 && (
                        min="1"
                        value={item.cantidad}
                        variant="outline"
                        size="icon"
                      />index)}
                      >
>
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
              })}
            </div>

                        <Trash size={16} />
                      </Button>
              <span className="text-lg font-semibold">Total:</span>
              <span className="text-2xl font-bold text-primary">
                )
              })}
            </div>
          </div>


        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
              <span className="text-2xl font-bold text-primary">
                HNL {calculateTotal().toLocaleString()}
              </span>
            </div>
          </div>
        </div>

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

          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Guardando...' : 'Guardar Cambios'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
