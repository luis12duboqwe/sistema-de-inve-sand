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
import { Plus, Trash, Robot, MapPin, WarningCircle } from '@phosphor-icons/react'
import type { Profile, ProductWithStock, CreateOrderRequest, SalesProfile, Location } from '@/lib/types'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
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
  imeis?: string[]
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
  const [salesProfileSlug, setSalesProfileSlug] = useState(() => localStorage.getItem('last_sales_profile_slug') || '')
  const [sourceLocationId, setSourceLocationId] = useState<number | null>(() => {
    const saved = localStorage.getItem('last_source_location_id')
    return saved ? parseInt(saved) : null
  })
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [canal, setCanal] = useState<CreateOrderRequest['canal']>('whatsapp')
  const [metodoPago, setMetodoPago] = useState<CreateOrderRequest['metodo_pago']>('efectivo')
  const [items, setItems] = useState<OrderItemForm[]>([{ product_id: 0, cantidad: 1 }])
  const [tradeIns, setTradeIns] = useState<{
    marca: string
    modelo: string
    imei: string
    condicion: 'usado' | 'dañado' | 'para_repuestos'
    valor_estimado: number
    precio_venta?: number
    notas: string
  }[]>([])
  const [notas, setNotas] = useState('')
  const [deliveryDate, setDeliveryDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [availableIMEIs, setAvailableIMEIs] = useState<Record<number, string[]>>({})

  // Persistir selección en localStorage
  useEffect(() => {
    if (salesProfileSlug) localStorage.setItem('last_sales_profile_slug', salesProfileSlug)
  }, [salesProfileSlug])

  useEffect(() => {
    if (sourceLocationId) localStorage.setItem('last_source_location_id', sourceLocationId.toString())
  }, [sourceLocationId])

  // 🔒 BUG FIX: Limpiar IMEIs seleccionados al cambiar de ubicación para evitar inconsistencias
  useEffect(() => {
    setAvailableIMEIs({})
    setItems(prev => prev.map(item => ({ ...item, imeis: [] })))
  }, [sourceLocationId])

  // Función para resetear el formulario
  const resetForm = () => {
    setCustomerName('')
    setCustomerPhone('')
    setCanal('whatsapp')
    setMetodoPago('efectivo')
    setItems([{ product_id: 0, cantidad: 1 }])
    setTradeIns([])
    setNotas('')
    setDeliveryDate('')
    setIsSubmitting(false)
    // NO resetear salesProfileSlug y sourceLocationId para mantener selección entre ventas
    setAvailableIMEIs({})
  }

  // PROBLEMA 1: Resetear formulario al cerrar/cancelar
  useEffect(() => {
    if (!open) {
      resetForm()
    }
  }, [open])

  // Establecer valores por defecto al abrir si no hay selección previa
  useEffect(() => {
    if (!open) return
    
    if (!salesProfileSlug && salesProfiles.length > 0) {
      const defaultSalesProfile = salesProfiles.find(sp => sp.active) || salesProfiles[0]
      setSalesProfileSlug(defaultSalesProfile?.slug ?? '')
    }
    
    if (!sourceLocationId && locations.length > 0) {
      const defaultLocation = locations.find(l => l.activo) || locations[0]
      setSourceLocationId(defaultLocation?.id ?? null)
    }
  }, [open, salesProfiles, locations, salesProfileSlug, sourceLocationId])

  // Filtrar productos: solo mostrar los que tienen stock en la ubicación seleccionada
  const availableProducts = products.filter(product => {
    // Si no hay ubicación seleccionada, no mostrar nada
    if (!sourceLocationId) return false
    
    // V2.0: Verificar stock_items (tabla Stock)
    if (product.stock_items && product.stock_items.length > 0) {
      const stockInLocation = product.stock_items.find(s => s.location_id === sourceLocationId)
      // 🔒 Bug #8: Considerar stock_reservada en el cálculo
      const stockLibre = (stockInLocation?.cantidad_disponible || 0) - (stockInLocation?.cantidad_reservada || 0)
      const hasStock = stockInLocation && stockLibre > 0
      
      console.log('📦 Producto:', product.nombre, '| Ubicación:', sourceLocationId, '| Disponible:', stockInLocation?.cantidad_disponible || 0, '| Reservado:', stockInLocation?.cantidad_reservada || 0, '| Libre:', stockLibre, '| Mostrar:', hasStock)
      
      return hasStock
    }
    
    // Si no tiene stock_items, NO mostrar (requiere migración a V2.0)
    console.log('⚠️ Producto sin stock_items (no compatible con V2.0):', product.nombre)
    return false
  })

  const handleAddItem = () => {
    setItems([...items, { product_id: 0, cantidad: 1 }])
  }

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const handleItemChange = async (index: number, field: keyof OrderItemForm, value: any) => {
    const newItems = [...items]
    
    // Si cambia el producto, validar que no esté duplicado
    if (field === 'product_id') {
      const productId = value as number
      if (productId > 0) {
        const isDuplicate = newItems.some((item, i) => i !== index && item.product_id === productId)
        if (isDuplicate) {
          const product = products.find(p => p.id === productId)
          toast.error(`❌ "${product?.nombre}" ya está en la orden. Usa el campo cantidad para pedir más unidades.`)
          return // No permitir el cambio
        }

        // Fetch IMEIs if needed
        const product = products.find(p => p.id === productId)
        const isSerialized = product?.is_serialized ?? (product?.categoria === 'celular')
        if (isSerialized && sourceLocationId) {
           try {
             const imeis = await inventoryServiceInstance.getAvailableIMEIs(productId, sourceLocationId)
             setAvailableIMEIs(prev => ({ ...prev, [productId]: imeis }))
             newItems[index].imeis = []
           } catch (e) {
             console.error('Error fetching IMEIs', e)
           }
        }
      }
      newItems[index].product_id = productId
    }
    
    // Si cambia cantidad, validar contra stock disponible
    else if (field === 'cantidad') {
      const val = value as number
      const productId = newItems[index].product_id
      if (productId > 0) {
        const product = products.find(p => p.id === productId)
        
        // Determinar stock disponible (V2.0 con ubicaciones o legacy global)
        let available = 0
        if (product?.stock_items && product.stock_items.length > 0) {
          // V2.0: Usar stock de la ubicación específica
          const stockInLocation = product.stock_items.find(s => s.location_id === sourceLocationId)
          available = (stockInLocation?.cantidad_disponible || 0) - (stockInLocation?.cantidad_reservada || 0)
        } else {
          // Legacy: Usar stock_disponible global
          available = product?.stock_disponible || 0
        }
        
        // Limitar al stock disponible
        if (val > available) {
          toast.error(`⚠️ Solo hay ${available} unidades de "${product?.nombre}" ${product?.stock_items?.length ? 'en esta ubicación' : 'disponibles'}`)
          newItems[index].cantidad = available
        } else {
          newItems[index].cantidad = val
        }

        // Trim IMEIs if quantity reduced
        if (newItems[index].imeis && newItems[index].imeis!.length > newItems[index].cantidad) {
           newItems[index].imeis = newItems[index].imeis!.slice(0, newItems[index].cantidad)
        }
      } else {
        newItems[index].cantidad = val
      }
    } 
    else if (field === 'imeis') {
       newItems[index].imeis = value as string[]
    }
    
    setItems(newItems)
  }

  const calculateTotal = () => {
    const itemsTotal = items.reduce((total, item) => {
      const product = products.find(p => p.id === item.product_id)
      if (!product) return total
      return total + product.precio * item.cantidad
    }, 0)

    const tradeInsTotal = tradeIns.reduce((total, item) => total + (Number(item.valor_estimado) || 0), 0)

    return Math.max(0, itemsTotal - tradeInsTotal)
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

    // Validar IMEIs para productos serializados
    for (const item of validItems) {
      const product = products.find(p => p.id === item.product_id)
      // V2.0: Usar is_serialized si existe, fallback a categoría celular
      const isSerialized = product?.is_serialized ?? (product?.categoria === 'celular')
      
      if (isSerialized) {
        if (!item.imeis || item.imeis.length !== item.cantidad) {
          toast.error(`Debes seleccionar ${item.cantidad} IMEIs para "${product?.nombre}"`)
          return
        }
      }
    }

    // PROBLEMA 3: Validar duplicados PRIMERO - sumar cantidades del mismo producto
    const productQuantities = new Map<number, number>()
    for (const item of validItems) {
      const current = productQuantities.get(item.product_id) || 0
      productQuantities.set(item.product_id, current + item.cantidad)
    }

    // Validar totales contra stock disponible en la ubicación
    for (const [productId, totalCantidad] of productQuantities.entries()) {
      const product = products.find(p => p.id === productId)
      if (!product) {
        toast.error('Producto seleccionado no encontrado')
        return
      }

      // Determinar stock disponible (V2.0 con ubicaciones o legacy global)
      let available = 0
      if (product.stock_items && product.stock_items.length > 0) {
        // V2.0: Usar stock de la ubicación específica
        const stockInLocation = product.stock_items.find(s => s.location_id === sourceLocationId)
        available = (stockInLocation?.cantidad_disponible || 0) - (stockInLocation?.cantidad_reservada || 0)
      } else {
        // Legacy: Usar stock_disponible global
        available = product.stock_disponible || 0
      }
      
      if (totalCantidad > available) {
        const location = locations.find(l => l.id === sourceLocationId)
        const locationMsg = product.stock_items?.length 
          ? `en ${location?.nombre}` 
          : 'disponibles'
        toast.error(`📦 Total solicitado de "${product.nombre}": ${totalCantidad} unidades, pero solo hay ${available} ${locationMsg}`)
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
        trade_ins: tradeIns.length > 0 ? tradeIns : undefined,
        notes: notas.trim() || undefined,
        delivery_date: deliveryDate || undefined
      })

      // Reset ya no es necesario - el useEffect lo hace al cerrar
      onOpenChange(false)
    } catch (error) {
      console.error('Error creating order:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-2xl max-h-[90vh] overflow-y-auto">
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
              <Button type="button" variant="outline" size="sm" onClick={handleAddItem} disabled={!sourceLocationId}>
                <Plus size={16} className="mr-1" />
                Agregar Producto
              </Button>
            </div>

            {/* Alerta de filtrado por ubicación */}
            {sourceLocationId && (
              <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3 text-sm">
                <p className="text-blue-800">
                  📍 Mostrando solo productos con stock en{' '}
                  <strong>{locations.find(l => l.id === sourceLocationId)?.nombre}</strong>
                </p>
                {availableProducts.length === 0 && (
                  <p className="text-blue-700 mt-1 text-xs">
                    ⚠️ Esta ubicación no tiene productos con stock. Selecciona otra ubicación o transfiere stock primero.
                  </p>
                )}
              </div>
            )}
            {!sourceLocationId && (
              <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 text-sm text-amber-800">
                ⚠️ Selecciona primero una ubicación origen para ver los productos disponibles
              </div>
            )}

            <div className="space-y-2">
              {items.map((item, index) => (
                <div key={index} className="border p-3 rounded-md space-y-3 bg-card">
                  <div className="flex items-end gap-2">
                    <div className="flex-1 space-y-2">
                      <Select
                        value={item.product_id.toString()}
                        onValueChange={v => handleItemChange(index, 'product_id', parseInt(v))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Seleccionar producto" />
                        </SelectTrigger>
                        <SelectContent>
                          {availableProducts.length === 0 ? (
                            <div className="p-4 text-center text-sm text-muted-foreground">
                              {sourceLocationId 
                                ? 'No hay productos con stock en esta ubicación'
                                : 'Selecciona primero una ubicación'}
                            </div>
                          ) : (
                            availableProducts.map(product => {
                              // Obtener stock en la ubicación seleccionada
                              const stockInLocation = product.stock_items?.find(
                                s => s.location_id === sourceLocationId
                              )
                              const stockDisplay = stockInLocation 
                                ? (stockInLocation.cantidad_disponible - (stockInLocation.cantidad_reservada || 0))
                                : product.stock_disponible
                              
                              return (
                                <SelectItem key={product.id} value={product.id.toString()}>
                                  {product.nombre} - HNL {product.precio.toLocaleString()} 
                                  <span className="ml-2 text-muted-foreground">
                                    (Stock: {stockDisplay})
                                  </span>
                                </SelectItem>
                              )
                            })
                          )}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="w-24 space-y-2">
                      <Input
                        type="number"
                        min="1"
                        max={(() => {
                          const product = products.find(p => p.id === item.product_id)
                          if (!product) return 999
                          
                          // V2.0: Usar stock de ubicación específica si existe
                          if (product.stock_items && product.stock_items.length > 0) {
                            const stockInLocation = product.stock_items.find(s => s.location_id === sourceLocationId)
                            return (stockInLocation?.cantidad_disponible || 0) - (stockInLocation?.cantidad_reservada || 0)
                          }
                          
                          // Legacy: Usar stock global
                          return product.stock_disponible || 0
                        })()}
                        value={item.cantidad}
                        onChange={e =>
                          handleItemChange(index, 'cantidad', parseInt(e.target.value) || 1)
                        }
                        placeholder="Cant."
                      />
                    </div>

                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => handleRemoveItem(index)}
                      disabled={items.length === 1}
                      title={items.length === 1 ? 'Debe haber al menos un producto' : 'Eliminar producto'}
                    >
                      <Trash size={16} />
                    </Button>
                  </div>

                  {/* IMEI Selector */}
                  {(() => {
                    const product = products.find(p => p.id === item.product_id)
                    const isSerialized = product?.is_serialized ?? (product?.categoria === 'celular')
                    
                    if (isSerialized) {
                      const imeis = availableIMEIs[item.product_id] || []
                      return (
                        <div className="w-full bg-muted/30 p-2 rounded border border-dashed">
                          <div className="flex justify-between items-center mb-2">
                            <Label className="text-xs font-medium">
                              Seleccionar IMEIs ({item.imeis?.length || 0}/{item.cantidad})
                            </Label>
                            <span className="text-xs text-muted-foreground">
                              {imeis.length} disponibles
                            </span>
                          </div>
                          
                          {imeis.length === 0 ? (
                            <div className="text-xs text-muted-foreground italic">
                              No hay IMEIs disponibles en esta ubicación.
                            </div>
                          ) : (
                            <div className="flex flex-wrap gap-2">
                              {imeis.map(imei => {
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
                                      handleItemChange(index, 'imeis', newImeis)
                                    }}
                                    className={`cursor-pointer px-2 py-1 text-xs rounded border transition-colors ${
                                      isSelected
                                        ? 'bg-primary text-primary-foreground border-primary font-medium' 
                                        : 'bg-background hover:bg-muted border-input'
                                    }`}
                                  >
                                    {imei}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                          {item.cantidad > (item.imeis?.length || 0) && (
                            <div className="mt-2 text-xs text-amber-600 flex items-center gap-1">
                              <WarningCircle className="w-3 h-3" />
                              Faltan seleccionar {item.cantidad - (item.imeis?.length || 0)} IMEIs
                            </div>
                          )}
                        </div>
                      )
                    }
                  })()}
                </div>
              ))}
            </div>
          </div>

          {/* Trade-Ins Section */}
          <div className="space-y-4 border-t pt-4">
            <div className="flex items-center justify-between">
              <Label className="text-base font-semibold">Retomas (Trade-Ins)</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setTradeIns([...tradeIns, { marca: '', modelo: '', imei: '', condicion: 'usado', valor_estimado: 0, precio_venta: 0, notas: '' }])}
              >
                <Plus className="mr-2 h-4 w-4" />
                Agregar Retoma
              </Button>
            </div>

            <div className="space-y-3">
              {tradeIns.map((tradeIn, index) => (
                <div key={index} className="grid grid-cols-12 gap-2 items-start border p-2 rounded-md">
                  <div className="col-span-4 space-y-1">
                    <Input
                      placeholder="Marca"
                      value={tradeIn.marca}
                      onChange={e => {
                        const newTradeIns = [...tradeIns]
                        newTradeIns[index].marca = e.target.value
                        setTradeIns(newTradeIns)
                      }}
                    />
                    <Input
                      placeholder="Modelo"
                      value={tradeIn.modelo}
                      onChange={e => {
                        const newTradeIns = [...tradeIns]
                        newTradeIns[index].modelo = e.target.value
                        setTradeIns(newTradeIns)
                      }}
                    />
                  </div>
                  <div className="col-span-4 space-y-1">
                    <Input
                      placeholder="IMEI (Opcional)"
                      value={tradeIn.imei}
                      onChange={e => {
                        const newTradeIns = [...tradeIns]
                        newTradeIns[index].imei = e.target.value
                        setTradeIns(newTradeIns)
                      }}
                    />
                    <Select
                      value={tradeIn.condicion}
                      onValueChange={value => {
                        const newTradeIns = [...tradeIns]
                        newTradeIns[index].condicion = value as any
                        setTradeIns(newTradeIns)
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Condición" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="usado">Usado</SelectItem>
                        <SelectItem value="dañado">Dañado</SelectItem>
                        <SelectItem value="para_repuestos">Para Repuestos</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-3 space-y-1">
                    <Input
                      type="number"
                      placeholder="Valor Estimado"
                      value={tradeIn.valor_estimado || ''}
                      onChange={e => {
                        const val = parseFloat(e.target.value) || 0
                        const newTradeIns = [...tradeIns]
                        newTradeIns[index].valor_estimado = val
                        // Auto-calcular precio sugerido (30%) si no se ha editado manualmente
                        if (!newTradeIns[index].precio_venta || newTradeIns[index].precio_venta === 0) {
                           newTradeIns[index].precio_venta = Math.round(val * 1.3)
                        }
                        setTradeIns(newTradeIns)
                      }}
                    />
                    <Input
                      type="number"
                      placeholder="Precio Venta (Sugerido)"
                      value={tradeIn.precio_venta || ''}
                      onChange={e => {
                        const newTradeIns = [...tradeIns]
                        newTradeIns[index].precio_venta = parseFloat(e.target.value) || 0
                        setTradeIns(newTradeIns)
                      }}
                      className="bg-green-50 border-green-200"
                      title="Precio de venta sugerido para el nuevo producto"
                    />
                    <Input
                      placeholder="Notas"
                      value={tradeIn.notas}
                      onChange={e => {
                        const newTradeIns = [...tradeIns]
                        newTradeIns[index].notas = e.target.value
                        setTradeIns(newTradeIns)
                      }}
                    />
                  </div>
                  <div className="col-span-1 flex justify-center pt-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        const newTradeIns = [...tradeIns]
                        newTradeIns.splice(index, 1)
                        setTradeIns(newTradeIns)
                      }}
                    >
                      <Trash className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
              {tradeIns.length === 0 && (
                <div className="text-sm text-muted-foreground text-center py-2">
                  No hay equipos en retoma
                </div>
              )}
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
          {/* 🔒 Bug #9: Validar que ubicación esté seleccionada */}
          <Button 
            onClick={handleSubmit} 
            disabled={isSubmitting || !sourceLocationId || !salesProfileSlug || items.length === 0}
            title={!sourceLocationId ? 'Selecciona una ubicación' : !salesProfileSlug ? 'Selecciona un perfil de ventas' : ''}
          >
            {isSubmitting ? 'Creando...' : 'Crear Orden'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
