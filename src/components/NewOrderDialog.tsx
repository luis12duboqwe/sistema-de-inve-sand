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
import type { Profile, ProductWithStock, CreateOrderRequest } from '@/lib/types'

interface NewOrderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profiles: Profile[]
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
  products,
  onSubmit
}: NewOrderDialogProps) {
  const [profileSlug, setProfileSlug] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [canal, setCanal] = useState<CreateOrderRequest['canal']>('whatsapp')
  const [metodoPago, setMetodoPago] = useState<CreateOrderRequest['metodo_pago']>('efectivo')
  const [items, setItems] = useState<OrderItemForm[]>([{ product_id: 0, cantidad: 1 }])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const availableProducts = products.filter(p => 
    !profileSlug || profiles.find(pr => pr.slug === profileSlug)?.id === p.profile_id
  )

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
    if (!profileSlug || !customerName || !customerPhone) {
      return
    }

    const validItems = items.filter(item => item.product_id > 0 && item.cantidad > 0)
    if (validItems.length === 0) {
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit({
        profile_slug: profileSlug,
        canal,
        customer_name: customerName,
        customer_phone: customerPhone,
        metodo_pago: metodoPago,
        items: validItems
      })

      setProfileSlug('')
      setCustomerName('')
      setCustomerPhone('')
      setCanal('whatsapp')
      setMetodoPago('efectivo')
      setItems([{ product_id: 0, cantidad: 1 }])
      onOpenChange(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nueva Orden</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="profile">Perfil</Label>
            <Select value={profileSlug} onValueChange={setProfileSlug}>
              <SelectTrigger id="profile">
                <SelectValue placeholder="Seleccionar perfil" />
              </SelectTrigger>
              <SelectContent>
                {profiles.map(profile => (
                  <SelectItem key={profile.id} value={profile.slug}>
                    {profile.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
                value={customerPhone}
                onChange={e => setCustomerPhone(e.target.value)}
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
