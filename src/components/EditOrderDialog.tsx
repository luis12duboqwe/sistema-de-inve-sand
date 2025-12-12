import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
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
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'

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
      imeis?: string[]
    }[]
    notes?: string
    delivery_date?: string
  }) => Promise<void>
}

interface OrderItemForm {
  product_id: number
  cantidad: number
  imeis?: string[]
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
  const [notas, setNotas] = useState(order.notas || '')
  const [deliveryDate, setDeliveryDate] = useState(
    order.delivery_date ? new Date(order.delivery_date).toISOString().slice(0, 16) : ''
  )
  const [items, setItems] = useState<OrderItemForm[]>(
    order.items.map(item => ({
      product_id: item.product_id,
      cantidad: item.cantidad,
      imeis: item.imeis || []
    }))
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [availableIMEIs, setAvailableIMEIs] = useState<Record<number, string[]>>({})

  useEffect(() => {
    if (open) {
      setCustomerName(order.customer_name)
      setCustomerPhone(order.customer_phone)
      setCanal(order.canal)
      setMetodoPago(order.metodo_pago)
      setNotas(order.notas || '')
      setDeliveryDate(
        order.delivery_date ? new Date(order.delivery_date).toISOString().slice(0, 16) : ''
      )
      setItems(
        order.items.map(item => ({
          product_id: item.product_id,
          cantidad: item.cantidad,
          imeis: item.imeis || []
        }))
      )
    }
  }, [open, order])

  // Fetch IMEIs for initial items and when items change
  useEffect(() => {
    const fetchIMEIs = async () => {
      if (!order.source_location_id || !open) return
      
      const newAvailableIMEIs: Record<number, string[]> = {}
      
      for (const item of items) {
        if (item.product_id > 0 && !newAvailableIMEIs[item.product_id]) {
          const product = products.find(p => p.id === item.product_id)
          if (product?.categoria === 'celular') {
             try {
               // Fetch available IMEIs
               const imeis = await inventoryServiceInstance.getAvailableIMEIs(item.product_id, order.source_location_id)
               
               // Also include the IMEIs currently assigned to this item (so they appear as selectable)
               // We need to find the original item in the order to get its IMEIs
               const originalItem = order.items.find(oi => oi.product_id === item.product_id)
               const currentIMEIs = originalItem?.imeis || []
               
               // Combine and deduplicate
               const combined = Array.from(new Set([...imeis, ...currentIMEIs]))
               newAvailableIMEIs[item.product_id] = combined
             } catch (e) {
               console.error('Error fetching IMEIs', e)
             }
          }
        }
      }
      setAvailableIMEIs(prev => ({ ...prev, ...newAvailableIMEIs }))
    }
    
    fetchIMEIs()
  }, [open, items, order.source_location_id, products])

  const addItem = () => {
    setItems([...items, { product_id: 0, cantidad: 1 }])
  }

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const updateItemProduct = (index: number, productId: number) => {
    const newItems = [...items]
    newItems[index].product_id = productId
    newItems[index].imeis = [] // Reset IMEIs when product changes
    setItems(newItems)
  }

  const updateItemQuantity = (index: number, cantidad: number) => {
    const newItems = [...items]
    newItems[index].cantidad = cantidad
    
    // Trim IMEIs if quantity reduced
    if (newItems[index].imeis && newItems[index].imeis!.length > cantidad) {
       newItems[index].imeis = newItems[index].imeis!.slice(0, cantidad)
    }
    
    setItems(newItems)
  }

  const updateItemIMEIs = (index: number, imeis: string[]) => {
    const newItems = [...items]
    newItems[index].imeis = imeis
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

      // Validate IMEIs for serialized products
      if (product.categoria === 'celular') {
        if (!item.imeis || item.imeis.length !== item.cantidad) {
          toast.error(`Debes seleccionar ${item.cantidad} IMEIs para ${product.nombre}`)
          return
        }
      }
    }

    setIsSubmitting(true)
    try {
      await onSubmit(order.id, {
        customer_name: customerName,
        customer_phone: phoneValidation.phone,
        canal,
        metodo_pago: metodoPago,
        items: validItems,
        notes: notas.trim() || undefined,
        delivery_date: deliveryDate || undefined
      })
      onOpenChange(false)
    } catch (error) {
      console.error('Error updating order:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar Orden #{order.id}</DialogTitle>
          <DialogDescription>
            Modifica los detalles de la orden, productos y cantidades.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="+504 9999-9999"
                type="tel"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                <Plus size={16} className="mr-2" />
                Agregar Producto
              </Button>
            </div>
            {items.map((item, index) => {
              const availableForThisItem = getAvailableProducts(item.product_id)
              const originalItem = order.items.find(oi => oi.product_id === item.product_id)
              const product = products.find(p => p.id === item.product_id)
              
              return (
                <div key={index} className="border p-3 rounded-md space-y-3 bg-card">
                  <div className="flex items-end gap-2">
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
                          {availableForThisItem.map(product => {
                            const availableStock = product.stock_disponible + (originalItem?.cantidad || 0)
                            return (
                              <SelectItem key={product.id} value={product.id.toString()}>
                                {product.nombre} - HNL {product.precio.toLocaleString()} (Stock:{' '}
                                {availableStock})
                              </SelectItem>
                            )
                          })}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="w-24 space-y-2">
                      <Label className="text-sm">Cantidad</Label>
                      <Input
                        type="number"
                        min="1"
                        value={item.cantidad}
                        onChange={(e) => updateItemQuantity(index, parseInt(e.target.value) || 1)}
                      />
                    </div>

                    {items.length > 1 && (
                      <Button
                        type="button"
                        variant="destructive"
                        size="icon"
                        onClick={() => removeItem(index)}
                      >
                        <Trash size={16} />
                      </Button>
                    )}
                  </div>

                  {/* IMEI Selector */}
                  {product?.categoria === 'celular' && (
                    <div className="w-full bg-muted/30 p-2 rounded border border-dashed">
                      <div className="flex justify-between items-center mb-2">
                        <Label className="text-xs font-medium">
                          Seleccionar IMEIs ({item.imeis?.length || 0}/{item.cantidad})
                        </Label>
                        <span className="text-xs text-muted-foreground">
                          {(availableIMEIs[item.product_id] || []).length} disponibles
                        </span>
                      </div>
                      
                      {(availableIMEIs[item.product_id] || []).length === 0 ? (
                        <div className="text-xs text-muted-foreground italic">
                          No hay IMEIs disponibles en esta ubicación.
                        </div>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {(availableIMEIs[item.product_id] || []).map(imei => {
                            const isSelected = item.imeis?.includes(imei)
                            return (
                              <div 
                                key={imei}
                                onClick={() => {
                                  const currentImeis = item.imeis || []
                                  let newImeis
                                  if (isSelected) {
                                    newImeis = currentImeis.filter(i => i !== imei)
                                  } else {
                                    if (currentImeis.length >= item.cantidad) {
                                      toast.error(`Solo puedes seleccionar ${item.cantidad} IMEIs`)
                                      return
                                    }
                                    newImeis = [...currentImeis, imei]
                                  }
                                  updateItemIMEIs(index, newImeis)
                                }}
                                className={`
                                  px-2 py-1 rounded text-xs cursor-pointer border transition-colors
                                  ${isSelected 
                                    ? 'bg-primary text-primary-foreground border-primary' 
                                    : 'bg-background hover:bg-muted border-input'}
                                `}
                              >
                                {imei}
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-notas">Notas (opcional)</Label>
            <Textarea
              id="edit-notas"
              value={notas}
              onChange={e => setNotas(e.target.value)}
              placeholder="Instrucciones especiales, comentarios, etc..."
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-delivery-date">Fecha de Entrega (opcional)</Label>
            <Input
              id="edit-delivery-date"
              type="datetime-local"
              value={deliveryDate}
              onChange={e => setDeliveryDate(e.target.value)}
            />
          </div>

          <div className="flex items-center justify-between pt-4 border-t">
            <span className="text-lg font-semibold">Total:</span>
            <span className="text-2xl font-bold text-primary">
              HNL {calculateTotal().toLocaleString()}
            </span>
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
