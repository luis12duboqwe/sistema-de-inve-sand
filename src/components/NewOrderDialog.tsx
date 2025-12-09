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
import { Plus, Trash, Robot, MapPin } from '@phosphor-icons/react'
import type { Profile, ProductWithStock, CreateOrderRequest, SalesProfile, Location } from '@/lib/types'
import { toast } from 'sonner'
import { validatePhoneNumber } from '@/lib/phoneValidator'

interface NewOrderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profiles: Profile[]
  salesProfiles: SalesProfile[]
  locations: Location[]
  products: ProductWithStock[]
  onSubmit: (order: CreateOrderRequest) => Promise<void>
}

interface OrderItemForm {
  product_id: number
  cantidad: number
}

export function NewOrderDialog({
  open,
  onOpenChange,
  profiles,
  salesProfiles,
  locations,
  products,
  onSubmit
}: NewOrderDialogProps) {
  // V2.0: Sistema único con múltiples canales de venta y ubicaciones
  const [salesProfileSlug, setSalesProfileSlug] = useState('')
  const [sourceLocationId, setSourceLocationId] = useState<number | null>(null)
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [canal, setCanal] = useState<CreateOrderRequest['canal']>('whatsapp')
  const [metodoPago, setMetodoPago] = useState<CreateOrderRequest['metodo_pago']>('efectivo')
  const [items, setItems] = useState<OrderItemForm[]>([{ product_id: 0, cantidad: 1 }])
  const [notas, setNotas] = useState('')
  const [deliveryDate, setDeliveryDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Establecer valores por defecto al abrir
  useEffect(() => {
    if (!open) return
    const defaultSalesProfile = salesProfiles.find(sp => sp.active) || salesProfiles[0]
    const defaultLocation = locations.find(l => l.activo) || locations[0]
    setSalesProfileSlug(defaultSalesProfile?.slug ?? '')
    setSourceLocationId(defaultLocation?.id ?? null)
  }, [open, salesProfiles, locations])

  // Todos los productos están disponibles globalmente (sin filtro por perfil)
  const availableProducts = products

  const handleAddItem = () => {
    setItems([...items, { product_id: 0, cantidad: 1 }])
  }

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const handleItemChange = (index: number, field: keyof OrderItemForm, value: number) => {
    const newItems = [...items]
    newItems[index][field] = value
    setItems(newItems)
  }

  const calculateTotal = () => {
    return items.reduce((total, item) => {
      const product = products.find(p => p.id === item.product_id)
      if (!product) return total
      return total + product.precio * item.cantidad
    }, 0)
  }

  const handleSubmit = async () => {
    // Validación V2.0
    if (!salesProfileSlug) {
      toast.error('Por favor selecciona un canal de venta')
      return
    }
    
    if (!sourceLocationId) {
      toast.error('Por favor selecciona una ubicación origen')
      return
    }
    
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

    // Validación de stock en ubicación específica usando datos ya cargados
    for (const item of validItems) {
      const product = products.find(p => p.id === item.product_id)
      if (!product) {
        toast.error('Producto seleccionado no encontrado')
        return
      }

      if (!product.stock_items) {
        console.warn('Stock por ubicación no presente en producto, se omite validación por ubicación')
        continue
      }

      const stockInLocation = product.stock_items.find(s => s.location_id === sourceLocationId)
      if (!stockInLocation || stockInLocation.cantidad_disponible < item.cantidad) {
        const location = locations.find(l => l.id === sourceLocationId)
        toast.error(`Stock insuficiente para ${product.nombre} en ${location?.nombre}. Disponible: ${stockInLocation?.cantidad_disponible || 0}`)
        return
      }
    }

    setIsSubmitting(true)
    try {
      await onSubmit({
        profile_slug: profiles[0]?.slug || undefined, // Legacy compatibility para backend
        sales_profile_slug: salesProfileSlug,
        source_location_id: sourceLocationId!,
        canal,
        customer_name: customerName,
        customer_phone: phoneValidation.phone,
        metodo_pago: metodoPago,
        items: validItems,
        notes: notas.trim() || undefined,
        delivery_date: deliveryDate || undefined
      })

      // Reset form
      setSalesProfileSlug('')
      setSourceLocationId(null)
      setCustomerName('')
      setCustomerPhone('')
      setCanal('whatsapp')
      setMetodoPago('efectivo')
      setItems([{ product_id: 0, cantidad: 1 }])
      setNotas('')
      setDeliveryDate('')
      onOpenChange(false)
    } catch (error) {
      console.error('Error creating order:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nueva Orden</DialogTitle>
          <DialogDescription>
            Crea una nueva orden seleccionando perfil, productos y datos del cliente.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Perfil de Venta y Ubicación */}
          <div className="space-y-2">
            <Label htmlFor="sales-profile" className="flex items-center gap-2">
              <Robot className="w-4 h-4" />
              Canal de Venta *
            </Label>
            <Select value={salesProfileSlug} onValueChange={setSalesProfileSlug}>
              <SelectTrigger id="sales-profile">
                <SelectValue placeholder="Seleccionar canal de venta" />
              </SelectTrigger>
              <SelectContent>
                {salesProfiles.map(profile => (
                  <SelectItem key={profile.id} value={profile.slug}>
                    {profile.name} ({profile.tipo})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Quién realiza la venta (bot, vendedor, sistema)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="location" className="flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Ubicación Origen del Stock *
            </Label>
            <Select 
              value={sourceLocationId?.toString() || ''} 
              onValueChange={(v) => setSourceLocationId(parseInt(v))}
            >
              <SelectTrigger id="location">
                <SelectValue placeholder="Seleccionar ubicación" />
              </SelectTrigger>
              <SelectContent>
                {locations.map(location => (
                  <SelectItem key={location.id} value={location.id.toString()}>
                    {location.nombre} ({location.tipo})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              De qué tienda/bodega se tomará el stock
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="customer-name">Nombre del Cliente</Label>
              <Input
                id="customer-name"
                value={customerName}
                onChange={e => setCustomerName(e.target.value)}
                placeholder="Juan Pérez"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="customer-phone">Teléfono</Label>
              <Input
                id="customer-phone"
                type="tel"
                value={customerPhone}
                onChange={e => setCustomerPhone(String(e.target.value))}
                placeholder="+504 9999-9999"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="canal">Canal</Label>
              <Select value={canal} onValueChange={(v) => setCanal(v as typeof canal)}>
                <SelectTrigger id="canal">
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
              <Label htmlFor="metodo-pago">Método de Pago</Label>
              <Select
                value={metodoPago}
                onValueChange={(v) => setMetodoPago(v as typeof metodoPago)}
              >
                <SelectTrigger id="metodo-pago">
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
              <Button type="button" variant="outline" size="sm" onClick={handleAddItem}>
                <Plus size={16} className="mr-1" />
                Agregar Producto
              </Button>
            </div>

            <div className="space-y-2">
              {items.map((item, index) => (
                <div key={index} className="flex items-end gap-2">
                  <div className="flex-1 space-y-2">
                    <Select
                      value={item.product_id.toString()}
                      onValueChange={v => handleItemChange(index, 'product_id', parseInt(v))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Seleccionar producto" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableProducts.map(product => (
                          <SelectItem key={product.id} value={product.id.toString()}>
                            {product.nombre} - HNL {product.precio.toLocaleString()} (Stock:{' '}
                            {product.stock_disponible})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-24 space-y-2">
                    <Input
                      type="number"
                      min="1"
                      value={item.cantidad}
                      onChange={e =>
                        handleItemChange(index, 'cantidad', parseInt(e.target.value) || 1)
                      }
                      placeholder="Cant."
                    />
                  </div>

                  {items.length > 1 && (
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => handleRemoveItem(index)}
                    >
                      <Trash size={16} />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="notas">Notas (opcional)</Label>
            <Textarea
              id="notas"
              value={notas}
              onChange={e => setNotas(e.target.value)}
              placeholder="Instrucciones especiales, comentarios, etc..."
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="delivery-date">Fecha de Entrega (opcional)</Label>
            <Input
              id="delivery-date"
              type="datetime-local"
              value={deliveryDate}
              onChange={e => setDeliveryDate(e.target.value)}
            />
          </div>

          <div className="pt-4 border-t">
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">Total:</span>
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
            {isSubmitting ? 'Creando...' : 'Crear Orden'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
