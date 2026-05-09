import { useState, useEffect, useRef } from 'react'
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
import { Plus, Trash, Barcode } from '@phosphor-icons/react'
import { toast } from 'sonner'
import type { Bank, OrderWithItems, ProductWithStock, SalesProfile } from '@/lib/types'
import { validatePhoneNumber } from '@/lib/phoneValidator'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { apiClient } from '@/lib/apiClient'

interface EditOrderDialogProps {
  open: boolean
  order: OrderWithItems
  products: ProductWithStock[]
  salesProfiles?: SalesProfile[]
  onOpenChange: (open: boolean) => void
  onSubmit: (orderId: number, updates: {
    customer_name: string
    customer_phone: string
    canal: OrderWithItems['canal']
    metodo_pago: OrderWithItems['metodo_pago']
    transfer_bank_name?: string
    transfer_reference?: string
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
  salesProfiles = [],
  onOpenChange,
  onSubmit
}: EditOrderDialogProps) {
  const ALL_ORDER_CHANNELS: OrderWithItems['canal'][] = ['whatsapp', 'facebook', 'instagram', 'tienda']
  const CHANNEL_LABELS: Record<NonNullable<OrderWithItems['canal']>, string> = {
    whatsapp: 'WhatsApp',
    facebook: 'Facebook',
    instagram: 'Instagram',
    tienda: 'Tienda Física'
  }

  const [customerName, setCustomerName] = useState(order.customer_name)
  const [customerPhone, setCustomerPhone] = useState(order.customer_phone)
  const [canal, setCanal] = useState<OrderWithItems['canal']>(order.canal)
  const [metodoPago, setMetodoPago] = useState<OrderWithItems['metodo_pago']>(order.metodo_pago)
  const [transferBankName, setTransferBankName] = useState(order.transfer_bank_name || '')
  const [transferReference, setTransferReference] = useState(order.transfer_reference || '')
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
  const [banks, setBanks] = useState<Bank[]>([])

  const [scanInput, setScanInput] = useState('')
  const scanInputRef = useRef<HTMLInputElement>(null)
  const selectedSalesProfile = salesProfiles.find(profile => profile.id === order.sales_profile_id)
  const allowedChannels = selectedSalesProfile?.canales?.length
    ? selectedSalesProfile.canales
    : ALL_ORDER_CHANNELS

  const handleScan = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const imei = scanInput.trim()
      if (!imei) return

      try {
        // 1. Buscar producto por IMEI
        const product = await inventoryServiceInstance.getProductByIMEI(imei)
        
        // 2. Buscar si el producto ya está en la orden
        const existingItemIndex = items.findIndex(i => i.product_id === product.id)
        
        if (existingItemIndex >= 0) {
          // El producto está en la orden. Asignar IMEI si falta.
          const item = items[existingItemIndex]
          const currentImeis = item.imeis || []
          
          if (currentImeis.includes(imei)) {
            toast.info('Este IMEI ya está asignado a la orden')
          } else if (currentImeis.length < item.cantidad) {
            updateItemIMEIs(existingItemIndex, [...currentImeis, imei])
            toast.success(`IMEI asignado a ${product.nombre}`)
          } else {
            toast.warning(`La cantidad para ${product.nombre} ya está completa. Aumenta la cantidad si deseas agregar más.`)
          }
        } else {
          // El producto NO está en la orden. ¿Es un reemplazo?
          // Buscar si hay algún item pendiente de IMEI que sea "compatible" (mismo precio/modelo?)
          // Por ahora, simplemente preguntamos si quiere agregarlo o reemplazar el primer item sin IMEIs
          
          const pendingItemIndex = items.findIndex(i => 
            (!i.imeis || i.imeis.length < i.cantidad) && 
            products.find(p => p.id === i.product_id)?.categoria === 'celular'
          )

          if (pendingItemIndex >= 0) {
            const pendingItem = items[pendingItemIndex]
            const pendingProduct = products.find(p => p.id === pendingItem.product_id)
            
            // Lógica de reemplazo automático si es "similar" o confirmación
            // Aquí asumimos que si escanea algo diferente, quiere cambiarlo
            if (confirm(`El IMEI escaneado es de un ${product.nombre}, pero la orden espera ${pendingProduct?.nombre}. ¿Deseas cambiar el producto en la orden?`)) {
               // Reemplazar producto
               const newItems = [...items]
               newItems[pendingItemIndex] = {
                 ...newItems[pendingItemIndex],
                 product_id: product.id,
                 imeis: [imei] // Asignar el nuevo IMEI
               }
               setItems(newItems)
               toast.success(`Producto cambiado a ${product.nombre} y asignado`)
            }
          } else {
             // No hay items pendientes, preguntar si agregar
             if (confirm(`El producto ${product.nombre} no está en la orden. ¿Deseas agregarlo?`)) {
               setItems([...items, { product_id: product.id, cantidad: 1, imeis: [imei] }])
               toast.success('Producto agregado')
             }
          }
        }
      } catch {
        toast.error('IMEI no encontrado o error al buscar producto')
      }
      
      setScanInput('')
    }
  }

  useEffect(() => {
    if (open) {
      setCustomerName(order.customer_name)
      setCustomerPhone(order.customer_phone)
      setCanal(order.canal)
      setMetodoPago(order.metodo_pago)
      setTransferBankName(order.transfer_bank_name || '')
      setTransferReference(order.transfer_reference || '')
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

  useEffect(() => {
    if (!open) return

    apiClient.getBanks(true)
      .then(setBanks)
      .catch(error => {
        console.warn('No se pudieron cargar bancos para transferencias:', error)
        setBanks([])
      })
  }, [open])

  useEffect(() => {
    if (!open) return
    if (!selectedSalesProfile?.canales?.length) return
    if (selectedSalesProfile.canales.includes(canal)) return

    const nextChannel = selectedSalesProfile.canales.includes('tienda')
      ? 'tienda'
      : selectedSalesProfile.canales[0]

    setCanal(nextChannel)
  }, [open, selectedSalesProfile, canal])

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
  }, [open, items, order.source_location_id, products, order.items])

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
      const stockInOrderLocation = p.stock_items?.find(stock => stock.location_id === order.source_location_id)
      const stockLibre = Math.max(
        (stockInOrderLocation?.cantidad_disponible || 0) - (stockInOrderLocation?.cantidad_reservada || 0),
        0
      )
      const availableStock = stockLibre + (originalItem?.cantidad || 0)
      return availableStock > 0
    })
  }

  const getAvailableStockInOrderLocation = (product: ProductWithStock, originalQuantity = 0) => {
    const stockInOrderLocation = product.stock_items?.find(stock => stock.location_id === order.source_location_id)
    const stockLibre = Math.max(
      (stockInOrderLocation?.cantidad_disponible || 0) - (stockInOrderLocation?.cantidad_reservada || 0),
      0
    )
    return stockLibre + originalQuantity
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

    if (metodoPago === 'transferencia') {
      if (!transferBankName.trim()) {
        toast.error('Ingresa el banco de la transferencia')
        return
      }
      if (!transferReference.trim()) {
        toast.error('Ingresa el número de referencia de la transferencia')
        return
      }
    }

    for (const item of validItems) {
      const product = products.find(p => p.id === item.product_id)
      if (!product) continue
      
      const originalItem = order.items.find(oi => oi.product_id === item.product_id)
      const originalQuantity = originalItem?.cantidad || 0
      const maxAvailable = getAvailableStockInOrderLocation(product, originalQuantity)

      if (item.cantidad > maxAvailable) {
        toast.error(`Stock insuficiente para ${product.nombre} en la ubicación de la orden. Disponible: ${maxAvailable}`)
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
        transfer_bank_name: metodoPago === 'transferencia' ? transferBankName.trim() : undefined,
        transfer_reference: metodoPago === 'transferencia' ? transferReference.trim() : undefined,
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
                  {allowedChannels.map(channel => (
                    <SelectItem key={channel} value={channel}>
                      {CHANNEL_LABELS[channel as NonNullable<OrderWithItems['canal']>]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedSalesProfile?.canales?.length ? (
                <p className="text-xs text-muted-foreground">
                  Perfil actual: <strong>{selectedSalesProfile.name}</strong>. Canales permitidos: <strong>{selectedSalesProfile.canales.map(channel => CHANNEL_LABELS[channel as NonNullable<OrderWithItems['canal']>] || channel).join(', ')}</strong>
                </p>
              ) : null}
              {canal === 'tienda' && order.source_location_id && (
                <p className="text-xs text-muted-foreground">
                  Esta venta física seguirá reportándose en la ubicación origen ya registrada para la orden.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-metodo-pago">Método de Pago</Label>
              <Select
                value={metodoPago}
                onValueChange={(v) => {
                  const next = v as typeof metodoPago
                  setMetodoPago(next)
                  if (next !== 'transferencia') {
                    setTransferBankName('')
                    setTransferReference('')
                  }
                }}
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

          {metodoPago === 'transferencia' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 rounded-md border border-dashed border-blue-300 bg-blue-50/40 p-3">
              <div className="space-y-2">
                <Label htmlFor="edit-transfer-bank">Banco de la transferencia</Label>
                <Input
                  id="edit-transfer-bank"
                  list="edit-transfer-bank-options"
                  value={transferBankName}
                  onChange={(e) => setTransferBankName(e.target.value)}
                  placeholder="Ej: BAC, Ficohsa, Atlántida"
                  maxLength={120}
                />
                <datalist id="edit-transfer-bank-options">
                  {banks.map(bank => (
                    <option key={bank.id} value={bank.name} />
                  ))}
                </datalist>
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-transfer-reference">Número de referencia</Label>
                <Input
                  id="edit-transfer-reference"
                  value={transferReference}
                  onChange={(e) => setTransferReference(e.target.value)}
                  placeholder="Ej: 84291372"
                  maxLength={120}
                />
                <p className="text-xs text-muted-foreground">
                  Se valida contra referencias previas para evitar pagos duplicados.
                </p>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
              <div className="flex items-center gap-2 mb-2">
                <Barcode className="w-5 h-5 text-blue-600" />
                <Label className="text-blue-800 font-medium">Escaneo de Fulfillment</Label>
              </div>
              <div className="flex gap-2">
                <Input
                  ref={scanInputRef}
                  value={scanInput}
                  onChange={(e) => setScanInput(e.target.value)}
                  onKeyDown={handleScan}
                  placeholder="Escanea el código de barras del IMEI aquí..."
                  className="bg-white"
                  autoFocus
                />
              </div>
              <p className="text-xs text-blue-600 mt-1">
                Escanea un IMEI para asignarlo automáticamente o reemplazar productos.
              </p>
            </div>

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

          {/* V2.1: Detalles Financieros y Trade-Ins (Solo Lectura) */}
          {((order.trade_ins && order.trade_ins.length > 0) || order.financing_details) && (
            <div className="border rounded-md p-4 bg-muted/20 space-y-4">
              <h3 className="font-medium text-sm flex items-center gap-2">
                <span className="w-1 h-4 bg-primary rounded-full"></span>
                Detalles de la Transacción
              </h3>
              
              {/* Trade-Ins */}
              {order.trade_ins && order.trade_ins.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Retomas (Trade-In)</Label>
                  <div className="space-y-1">
                    {order.trade_ins.map((trade, idx) => (
                      <div key={idx} className="flex justify-between text-sm bg-background p-2 rounded border shadow-sm">
                        <div className="flex flex-col">
                          <span className="font-medium">{trade.marca} {trade.modelo}</span>
                          <span className="text-xs text-muted-foreground capitalize">{trade.condicion} • {trade.color || 'N/A'} • {trade.capacidad || 'N/A'}</span>
                        </div>
                        <span className="font-medium text-red-600 flex items-center">- HNL {trade.valor_estimado.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Financiamiento */}
              {order.financing_details && (() => {
                try {
                  const details = JSON.parse(order.financing_details)
                  return (
                    <div className="space-y-2">
                      <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Financiamiento ({details.bank_name})</Label>
                      <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-sm bg-background p-3 rounded border shadow-sm">
                        <div className="text-muted-foreground">Plazo:</div>
                        <div className="text-right font-medium">{details.months > 0 ? `${details.months} meses` : 'Contado'}</div>
                        
                        <div className="text-muted-foreground">Prima:</div>
                        <div className="text-right font-medium">HNL {details.down_payment?.toLocaleString() || '0.00'}</div>
                        
                        <div className="text-muted-foreground">Monto a Financiar:</div>
                        <div className="text-right font-medium">HNL {details.financed_amount?.toLocaleString() || '0.00'}</div>
                        
                        <div className="text-muted-foreground">Recargo ({((details.rate || 0) * 100).toFixed(1)}%):</div>
                        <div className="text-right font-medium text-orange-600">+ HNL {details.surcharge?.toLocaleString() || '0.00'}</div>
                        
                        <div className="col-span-2 border-t pt-2 mt-1 flex justify-between items-center">
                          <span className="font-bold text-primary">Cuota Mensual:</span>
                          <span className="font-bold text-lg">HNL {details.monthly_payment?.toLocaleString() || '0.00'}</span>
                        </div>
                      </div>
                    </div>
                  )
                } catch (error) {
                  console.error('Error parsing financing_details', error)
                  return null
                }
              })()}
              
              {/* Resumen Total */}
              <div className="flex justify-between items-center pt-3 border-t border-dashed">
                <span className="font-bold text-base">Total Final Orden:</span>
                <span className="font-bold text-xl text-primary">HNL {order.total.toLocaleString()}</span>
              </div>
            </div>
          )}

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
