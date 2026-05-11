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
import { Plus, Trash, Robot, MapPin, WarningCircle, CreditCard } from '@phosphor-icons/react'
import type { Profile, ProductWithStock, CreateOrderRequest, SalesProfile, Location, Bank, TradeIn } from '@/lib/types'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { toast } from 'sonner'
import { validatePhoneNumber } from '@/lib/phoneValidator'
import { calculateLuhnCheckDigit } from '@/lib/utils'
import { ORDER_FIELD_LIMITS, validateOrderForm, type OrderItemDraft } from '@/lib/validation/orderFormSchema'

interface NewOrderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profiles: Profile[]
  salesProfiles: SalesProfile[]
  locations: Location[]
  products: ProductWithStock[]
  onSubmit: (order: CreateOrderRequest) => Promise<void>
}

type OrderItemForm = OrderItemDraft

const parseFlexibleNumber = (value: unknown): number | undefined => {
  if (value === undefined || value === null || value === '') {
    return undefined
  }

  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : undefined
  }

  let normalized = String(value).trim().replace(/\s+/g, '')
  if (!normalized) {
    return undefined
  }

  if (normalized.includes(',') && normalized.includes('.')) {
    if (normalized.lastIndexOf(',') > normalized.lastIndexOf('.')) {
      normalized = normalized.replace(/\./g, '').replace(',', '.')
    } else {
      normalized = normalized.replace(/,/g, '')
    }
  } else if (normalized.includes(',')) {
    normalized = normalized.replace(',', '.')
  }

  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : undefined
}

const normalizeScannerValue = (value: string): string => {
  const trimmed = value.trim()
  const digits = trimmed.replace(/\D/g, '')

  if (digits.length === 14) {
    try {
      return digits + calculateLuhnCheckDigit(digits)
    } catch {
      return digits
    }
  }

  if (digits.length === 15) {
    return digits
  }

  return trimmed.replace(/\s+/g, '').toUpperCase()
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
  const ALL_ORDER_CHANNELS: CreateOrderRequest['canal'][] = ['whatsapp', 'facebook', 'instagram', 'tienda']
  const CHANNEL_LABELS: Record<CreateOrderRequest['canal'], string> = {
    whatsapp: 'WhatsApp',
    facebook: 'Facebook',
    instagram: 'Instagram',
    tienda: 'Tienda Física'
  }

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
  const [transferBankName, setTransferBankName] = useState('')
  const [transferReference, setTransferReference] = useState('')
  const [items, setItems] = useState<OrderItemForm[]>([{ product_id: 0, cantidad: 1 }])
  const [tradeIns, setTradeIns] = useState<{
    marca: string
    modelo: string
    color?: string
    capacidad?: string
    imei: string
    condicion: 'usado' | 'dañado' | 'para_repuestos'
    valor_estimado: number
    precio_venta?: number
    notas: string
  }[]>([])
  const [notas, setNotas] = useState('')
  const [deliveryDate, setDeliveryDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // V2.1: Financing State
  const [banks, setBanks] = useState<Bank[]>([])
  const [selectedBankId, setSelectedBankId] = useState<number | null>(null)
  const [selectedMonths, setSelectedMonths] = useState<number | null>(null)
  const [cashDownPayment, setCashDownPayment] = useState('') // Prima / Pago Inicial
  const [scanInput, setScanInput] = useState('')

  const [availableIMEIs, setAvailableIMEIs] = useState<Record<number, string[]>>({})
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const scannerInputRef = useRef<HTMLInputElement | null>(null)

  const clearFieldError = (field: string) => {
    setFormErrors(prev => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  // Load banks on mount
  const loadBanks = async () => {
    try {
      const data = await inventoryServiceInstance.getBanks(true)
      setBanks(data)
    } catch (e) {
      console.error('Error loading banks', e)
    }
  }

  useEffect(() => {
    loadBanks()
  }, [open]) // Reload when dialog opens to get latest config

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
    setTransferBankName('')
    setTransferReference('')
    setItems([{ product_id: 0, cantidad: 1 }])
    setTradeIns([])
    setNotas('')
    setDeliveryDate('')
    setIsSubmitting(false)
    // NO resetear salesProfileSlug y sourceLocationId para mantener selección entre ventas
    setAvailableIMEIs({})
    setSelectedBankId(null)
    setSelectedMonths(null)
    setCashDownPayment('')
    setFormErrors({})
  }

  // PROBLEMA 1: Resetear formulario al cerrar/cancelar
  useEffect(() => {
    if (!open) {
      resetForm()
      setScanInput('')
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    requestAnimationFrame(() => scannerInputRef.current?.focus())
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

  const selectedSalesProfile = salesProfiles.find(profile => profile.slug === salesProfileSlug)
  const allowedChannels = selectedSalesProfile?.canales?.length
    ? selectedSalesProfile.canales
    : ALL_ORDER_CHANNELS

  useEffect(() => {
    if (!salesProfileSlug) return

    const profile = salesProfiles.find(item => item.slug === salesProfileSlug)
    if (!profile?.canales?.length) return

    const nextChannel = profile.canales.includes('tienda')
      ? 'tienda'
      : profile.canales.length === 1
        ? profile.canales[0]
        : profile.canales.includes(canal)
          ? canal
          : profile.canales[0]

    if (nextChannel !== canal) {
      setCanal(nextChannel)
      clearFieldError('canal')
    }
  }, [salesProfileSlug, salesProfiles, canal])

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
      
      
      return hasStock
    }
    
    // Si no tiene stock_items, NO mostrar (requiere migración a V2.0)
    return false
  })

  const handleAddItem = () => {
    setItems([...items, { product_id: 0, cantidad: 1 }])
  }

  const getAvailableStockForProduct = (product: ProductWithStock): number => {
    if (product.stock_items && product.stock_items.length > 0) {
      const stockInLocation = product.stock_items.find(s => s.location_id === sourceLocationId)
      return Math.max((stockInLocation?.cantidad_disponible || 0) - (stockInLocation?.cantidad_reservada || 0), 0)
    }

    return Math.max(product.stock_disponible || 0, 0)
  }

  const ensureAvailableImeisForProduct = async (productId: number): Promise<string[]> => {
    if (!sourceLocationId) return []

    const cached = availableIMEIs[productId]
    if (cached) {
      return cached
    }

    try {
      const imeis = await inventoryServiceInstance.getAvailableIMEIs(productId, sourceLocationId)
      setAvailableIMEIs(prev => ({ ...prev, [productId]: imeis }))
      return imeis
    } catch (error) {
      console.error('Error obteniendo IMEIs para escaneo de orden', error)
      return []
    }
  }

  const addScannedProductToOrder = async (product: ProductWithStock, scannedImei?: string) => {
    const availableStock = getAvailableStockForProduct(product)
    if (availableStock <= 0) {
      toast.error(`No hay stock disponible para "${product.nombre}" en esta ubicación`)
      return
    }

    const isSerialized = product.is_serialized ?? (product.categoria === 'celular')
    const availableImeisForProduct = isSerialized
      ? await ensureAvailableImeisForProduct(product.id)
      : []

    if (scannedImei && isSerialized && !availableImeisForProduct.includes(scannedImei)) {
      toast.error('El IMEI escaneado no está disponible en la ubicación seleccionada')
      return
    }

    const currentPrice = parseFlexibleNumber(product.precio) ?? 0
    const nextItems = items.length === 1 && items[0].product_id === 0 ? [] : [...items]
    const existingIndex = nextItems.findIndex(item => item.product_id === product.id)

    if (existingIndex >= 0) {
      const currentItem = nextItems[existingIndex]
      const currentImeis = currentItem.imeis ? [...currentItem.imeis] : []

      if (scannedImei) {
        if (currentImeis.includes(scannedImei)) {
          toast.error('Ese IMEI ya fue agregado a la orden')
          return
        }

        if (currentImeis.length >= availableStock) {
          toast.error(`Ya agregaste todas las unidades disponibles de "${product.nombre}"`)
          return
        }

        const updatedImeis = [...currentImeis, scannedImei]
        nextItems[existingIndex] = {
          ...currentItem,
          cantidad: updatedImeis.length,
          imeis: updatedImeis,
          precio_unitario: parseFlexibleNumber(currentItem.precio_unitario) ?? currentPrice,
        }
      } else {
        const nextQuantity = currentItem.cantidad + 1
        if (nextQuantity > availableStock) {
          toast.error(`Solo hay ${availableStock} unidades disponibles de "${product.nombre}"`)
          return
        }

        nextItems[existingIndex] = {
          ...currentItem,
          cantidad: nextQuantity,
          precio_unitario: parseFlexibleNumber(currentItem.precio_unitario) ?? currentPrice,
        }
      }
    } else {
      nextItems.push({
        product_id: product.id,
        cantidad: 1,
        precio_unitario: currentPrice,
        imeis: scannedImei ? [scannedImei] : [],
      })
    }

    setItems(nextItems)
    setScanInput('')
    requestAnimationFrame(() => scannerInputRef.current?.focus())
    toast.success(scannedImei
      ? `IMEI agregado para "${product.nombre}"`
      : `Producto agregado: ${product.nombre}`)
  }

  const handleScanProduct = async () => {
    const scannedValue = normalizeScannerValue(scanInput)

    if (!scannedValue) {
      toast.error('Escanea o escribe un SKU o IMEI válido')
      return
    }

    if (!sourceLocationId) {
      toast.error('Selecciona primero una ubicación origen')
      return
    }

    const skuMatch = availableProducts.find(product => product.sku.trim().toUpperCase() === scannedValue)
    if (skuMatch) {
      await addScannedProductToOrder(skuMatch)
      return
    }

    if (/^\d{15}$/.test(scannedValue)) {
      for (const product of availableProducts) {
        const isSerialized = product.is_serialized ?? (product.categoria === 'celular')
        if (!isSerialized) continue

        const imeis = await ensureAvailableImeisForProduct(product.id)
        if (imeis.includes(scannedValue)) {
          await addScannedProductToOrder(product, scannedValue)
          return
        }
      }
    }

    toast.error('No se encontró un producto disponible con ese SKU o IMEI')
    setScanInput('')
    requestAnimationFrame(() => scannerInputRef.current?.focus())
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
        
        // V2.1: Establecer precio por defecto al seleccionar producto
        if (product) {
          newItems[index].precio_unitario = parseFlexibleNumber(product.precio) ?? 0
        }

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

      // Guard: la cantidad debe ser >= 1
      const normalizedVal = !Number.isFinite(val) || val < 1 ? 1 : val
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
        if (normalizedVal > available) {
          toast.error(`⚠️ Solo hay ${available} unidades de "${product?.nombre}" ${product?.stock_items?.length ? 'en esta ubicación' : 'disponibles'}`)
          newItems[index].cantidad = available
        } else {
          newItems[index].cantidad = normalizedVal
        }

        // Trim IMEIs if quantity reduced
        if (newItems[index].imeis && newItems[index].imeis!.length > newItems[index].cantidad) {
           newItems[index].imeis = newItems[index].imeis!.slice(0, newItems[index].cantidad)
        }
      } else {
        newItems[index].cantidad = normalizedVal
      }
    } 
    else if (field === 'imeis') {
       newItems[index].imeis = value as string[]
    }
    else if (field === 'precio_unitario') {
       if (value === '' || value === null) {
         newItems[index].precio_unitario = undefined
       } else {
         const numericValue = parseFlexibleNumber(value)
         if (numericValue === undefined) {
           toast.error('El precio unitario debe ser numérico')
           return
         }
         if (numericValue < 0) {
           toast.error('El precio unitario no puede ser negativo')
           return
         }
         newItems[index].precio_unitario = numericValue
       }
    }
    
    setItems(newItems)
  }

    const calculateTotal = () => {
      const itemsTotal = items.reduce((total, item) => {
        const product = products.find(p => p.id === item.product_id)
        if (!product) return total
        // V2.1: Usar precio personalizado si existe
        const price = parseFlexibleNumber(item.precio_unitario) ?? parseFlexibleNumber(product.precio) ?? 0
        return total + price * item.cantidad
      }, 0)

      const tradeInsTotal = tradeIns.reduce((total, item) => total + (Number(item.valor_estimado) || 0), 0)
      const baseTotal = Math.max(0, itemsTotal - tradeInsTotal)

      // Base para financiamiento = (Productos - TradeIns - Prima)
      // La prima se resta ANTES de calcular el recargo, porque eso se paga en efectivo
      const downPayment = parseFloat(cashDownPayment) || 0
      const amountToFinance = Math.max(0, baseTotal - downPayment)

      let surcharge = 0

      // V2.1: Calcular recargo por financiamiento
      if (selectedBankId) {
        const bank = banks.find(b => b.id === selectedBankId)
      
        if (metodoPago === 'financiamiento' && selectedMonths) {
          const option = bank?.financing_options.find(o => o.months === selectedMonths)
          if (option) {
            surcharge = amountToFinance * Number(option.rate)
          }
        } else if (metodoPago === 'tarjeta') {
          // Tarjeta normal: aplicar tasa base del banco
          surcharge = amountToFinance * Number(bank?.normal_card_rate || 0)
        }
      }

      // Total Orden (alineado con backend): downPayment + monto a financiar + recargo
      return downPayment + amountToFinance + surcharge
    }

  const handleSubmit = async () => {
    const validation = validateOrderForm(
      {
        salesProfileSlug,
        sourceLocationId,
        customerName,
        customerPhone,
        canal,
        metodoPago,
        transferBankName,
        transferReference,
        items,
        tradeIns,
        notas,
        deliveryDate,
        cashDownPayment,
        selectedBankId,
        selectedMonths
      },
      { products, banks }
    )

    if (!validation.ok) {
      const aggregated: Record<string, string> = {}
      validation.issues.forEach(issue => {
        if (!aggregated[issue.field]) {
          aggregated[issue.field] = issue.message
        }
      })
      setFormErrors(aggregated)
      toast.error(validation.issues[0]?.message || 'Revisa los datos de la orden')
      return
    }

    setFormErrors({})

    const trimmedName = customerName.trim()
    const phoneValidation = validatePhoneNumber(customerPhone)
    const parsedDownPayment = cashDownPayment ? Number(cashDownPayment) : 0

    const sanitizedTradeIns: TradeIn[] | undefined = tradeIns.length
      ? tradeIns.map(tradeIn => ({
          marca: tradeIn.marca.trim(),
          modelo: tradeIn.modelo.trim(),
          color: tradeIn.color?.trim() || undefined,
          capacidad: tradeIn.capacidad?.trim() || undefined,
          imei: tradeIn.imei?.trim() || undefined,
          condicion: tradeIn.condicion,
          valor_estimado: Number(tradeIn.valor_estimado) || 0,
          precio_venta: tradeIn.precio_venta,
          notas: tradeIn.notas?.trim() || undefined
        }))
      : undefined

    const validItems = items
      .filter(item => item.product_id > 0 && item.cantidad > 0)
      .map(item => ({
        product_id: item.product_id,
        cantidad: item.cantidad,
        imeis: item.imeis?.filter(Boolean),
        precio_unitario:
          parseFlexibleNumber(item.precio_unitario)
      }))

    const itemsTotal = validItems.reduce((total, item) => {
      const product = products.find(p => p.id === item.product_id)
      if (!product) return total
      const price = parseFlexibleNumber(item.precio_unitario) ?? parseFlexibleNumber(product.precio) ?? 0
      return total + price * item.cantidad
    }, 0)
    const tradeInsTotal = tradeIns.reduce((total, item) => total + (Number(item.valor_estimado) || 0), 0)
    const baseTotal = Math.max(0, itemsTotal - tradeInsTotal)

    if ((metodoPago === 'financiamiento' || metodoPago === 'tarjeta') && parsedDownPayment > baseTotal) {
      setFormErrors(prev => ({
        ...prev,
        cashDownPayment: 'La prima no puede exceder el total neto de la orden'
      }))
      toast.error(`La prima (HNL ${parsedDownPayment}) no puede ser mayor al total de la orden (HNL ${baseTotal})`)
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit({
        profile_slug: profiles[0]?.slug || undefined,
        sales_profile_slug: salesProfileSlug,
        source_location_id: sourceLocationId!,
        canal,
        customer_name: trimmedName,
        customer_phone: phoneValidation.phone,
        metodo_pago: metodoPago,
        transfer_bank_name: metodoPago === 'transferencia' ? transferBankName.trim() || undefined : undefined,
        transfer_reference: metodoPago === 'transferencia' ? transferReference.trim() || undefined : undefined,
        items: validItems,
        trade_ins: sanitizedTradeIns,
        notes: notas.trim() || undefined,
        delivery_date: deliveryDate || undefined,
        financing_data: selectedBankId
          ? {
              bank_id: selectedBankId,
              months: selectedMonths || 0,
              down_payment: parsedDownPayment || undefined
            }
          : undefined
      })

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
              Perfil de Venta *
            </Label>
            <Select
              value={salesProfileSlug}
              onValueChange={value => {
                setSalesProfileSlug(value)
                clearFieldError('salesProfileSlug')
              }}
            >
              <SelectTrigger id="sales-profile">
                <SelectValue placeholder="Seleccionar perfil de venta" />
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
            {selectedSalesProfile?.canales?.length ? (
              <p className="text-xs text-muted-foreground">
                Canales habilitados para este perfil: <strong>{selectedSalesProfile.canales.map(channel => CHANNEL_LABELS[channel as CreateOrderRequest['canal']] || channel).join(', ')}</strong>
              </p>
            ) : null}
            {formErrors.salesProfileSlug && (
              <p className="text-xs text-red-600">{formErrors.salesProfileSlug}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="location" className="flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Ubicación Origen del Stock *
            </Label>
            <Select 
              value={sourceLocationId?.toString() || ''} 
              onValueChange={v => {
                setSourceLocationId(parseInt(v))
                clearFieldError('sourceLocationId')
              }}
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
              {canal === 'tienda'
                ? 'Esta ubicación quedará reportada como la tienda física donde se registró la venta'
                : 'De qué tienda/bodega se tomará el stock'}
            </p>
            {formErrors.sourceLocationId && (
              <p className="text-xs text-red-600">{formErrors.sourceLocationId}</p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="customer-name">Nombre del Cliente</Label>
              <Input
                id="customer-name"
                maxLength={ORDER_FIELD_LIMITS.MAX_CUSTOMER_NAME_LENGTH}
                value={customerName}
                onChange={e => {
                  setCustomerName(e.target.value)
                  clearFieldError('customerName')
                }}
                placeholder="Juan Pérez"
              />
              {formErrors.customerName && (
                <p className="text-xs text-red-600">{formErrors.customerName}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="customer-phone">Teléfono</Label>
              <Input
                id="customer-phone"
                type="tel"
                maxLength={ORDER_FIELD_LIMITS.MAX_PHONE_LENGTH}
                value={customerPhone}
                onChange={e => {
                  setCustomerPhone(String(e.target.value))
                  clearFieldError('customerPhone')
                }}
                placeholder="+504 9999-9999"
              />
              {formErrors.customerPhone && (
                <p className="text-xs text-red-600">{formErrors.customerPhone}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Productos</Label>
              </div>

              <div className="rounded-lg border border-dashed border-emerald-300 bg-emerald-50/60 p-3 space-y-2">
                <Label htmlFor="order-product-scan">Agregar por escaneo</Label>
                <div className="flex flex-col sm:flex-row gap-2">
                  <Input
                    id="order-product-scan"
                    ref={scannerInputRef}
                    autoFocus
                    value={scanInput}
                    onChange={e => setScanInput(e.target.value)}
                    onKeyDown={async e => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        await handleScanProduct()
                      }
                    }}
                    placeholder="Escanea SKU o IMEI"
                  />
                  <Button type="button" variant="outline" onClick={handleScanProduct}>
                    Agregar escaneado
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Puedes escanear el SKU para sumar el producto o el IMEI para agregar automáticamente una unidad serializada.
                </p>
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
                    <div className="flex flex-col md:flex-row md:items-end gap-2">
                      <div className="flex-1 space-y-2 w-full">
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
                                const stockDisplay = getAvailableStockForProduct(product)
                                
                                return (
                                  <SelectItem key={product.id} value={product.id.toString()}>
                                    {product.nombre} - HNL {(parseFlexibleNumber(product.precio) ?? 0).toLocaleString()} 
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

                      <div className="flex items-end gap-2 w-full md:w-auto">
                        <div className="flex-1 md:w-32 space-y-2">
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            value={item.precio_unitario ?? ''}
                            onChange={e =>
                              handleItemChange(index, 'precio_unitario', e.target.value)
                            }
                            placeholder={(() => {
                              const product = products.find(p => p.id === item.product_id)
                              return product ? String(parseFlexibleNumber(product.precio) ?? '') : 'Precio'
                            })()}
                            title="Precio unitario (dejar vacío para usar precio de lista)"
                          />
                        </div>

                        <div className="w-24 space-y-2">
                          <Input
                            type="number"
                            min="1"
                            max={(() => {
                              const product = products.find(p => p.id === item.product_id)
                              if (!product) return 999

                              return getAvailableStockForProduct(product)
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
                <Button type="button" variant="outline" size="sm" onClick={handleAddItem} disabled={!sourceLocationId} className="w-full mt-2">
                  <Plus size={16} className="mr-1" />
                  Agregar Producto
                </Button>
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
                  onClick={() =>
                    setTradeIns([
                      ...tradeIns,
                      {
                        marca: '',
                        modelo: '',
                        color: '',
                        capacidad: '',
                        imei: '',
                        condicion: 'usado',
                        valor_estimado: 0,
                        notas: ''
                      }
                    ])
                  }
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
                      <div className="grid grid-cols-2 gap-1">
                        <Input
                          placeholder="Color"
                          value={tradeIn.color || ''}
                          onChange={e => {
                            const newTradeIns = [...tradeIns]
                            newTradeIns[index].color = e.target.value
                            setTradeIns(newTradeIns)
                          }}
                        />
                        <Input
                          placeholder="Capacidad (GB)"
                          value={tradeIn.capacidad || ''}
                          onChange={e => {
                            const newTradeIns = [...tradeIns]
                            newTradeIns[index].capacidad = e.target.value
                            setTradeIns(newTradeIns)
                          }}
                        />
                      </div>
                    </div>
                    <div className="col-span-4 space-y-1">
                      <Input
                        placeholder="IMEI (Opcional)"
                        value={tradeIn.imei}
                        onChange={e => {
                          const val = e.target.value.replace(/\D/g, '')
                          let finalVal = val
                          if (val.length === 14) {
                              try {
                                const check = calculateLuhnCheckDigit(val)
                                finalVal = val + check
                                toast.success(`Dígito verificador generado: ${check}`)
                              } catch (err) {
                                console.error('Error calculando dígito IMEI', err)
                              }
                          }
                          const newTradeIns = [...tradeIns]
                          newTradeIns[index].imei = finalVal
                          setTradeIns(newTradeIns)
                        }}
                        maxLength={15}
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
                          const rawValue = e.target.value
                          const newTradeIns = [...tradeIns]
                          if (!rawValue.trim()) {
                            newTradeIns[index].precio_venta = undefined
                          } else {
                            const parsed = parseFloat(rawValue)
                            if (Number.isNaN(parsed) || parsed <= 0) {
                              toast.error('El precio de venta sugerido debe ser mayor a 0 o dejarse vacío')
                              return
                            }
                            newTradeIns[index].precio_venta = parsed
                          }
                          setTradeIns(newTradeIns)
                        }}
                        className="bg-green-50 border-green-200"
                        title="Precio de venta sugerido para el nuevo producto"
                      />
                      <Input
                        placeholder="Notas"
                        maxLength={ORDER_FIELD_LIMITS.MAX_TRADE_IN_NOTES_LENGTH}
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="canal">Canal</Label>
                <Select value={canal} onValueChange={(v) => setCanal(v as typeof canal)}>
                  <SelectTrigger id="canal">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {allowedChannels.map(channel => (
                      <SelectItem key={channel} value={channel}>
                        {CHANNEL_LABELS[channel as CreateOrderRequest['canal']]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {canal === 'tienda' && sourceLocationId && (
                  <p className="text-xs text-muted-foreground">
                    La venta se reportará en <strong>{locations.find(l => l.id === sourceLocationId)?.nombre || 'la tienda seleccionada'}</strong>.
                  </p>
                )}
                {selectedSalesProfile?.canales?.includes('tienda') && canal === 'tienda' && (
                  <p className="text-xs text-emerald-700">
                    Este perfil está configurado para venta física; el canal se ajustó automáticamente.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="metodo-pago">Método de Pago</Label>
                <Select
                  value={metodoPago}
                  onValueChange={(v) => {
                    const next = v as typeof metodoPago
                    setMetodoPago(next)
                    if (next !== 'transferencia') {
                      setTransferBankName('')
                      setTransferReference('')
                      clearFieldError('transferBankName')
                      clearFieldError('transferReference')
                    }
                  }}
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

            {metodoPago === 'transferencia' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 rounded-md border border-dashed border-blue-300 bg-blue-50/40 p-3">
                <div className="space-y-2">
                  <Label htmlFor="transfer-bank">Banco de la transferencia</Label>
                  <Input
                    id="transfer-bank"
                    list="transfer-bank-options"
                    value={transferBankName}
                    onChange={(e) => {
                      setTransferBankName(e.target.value)
                      clearFieldError('transferBankName')
                    }}
                    placeholder="Ej: BAC, Ficohsa, Atlántida"
                    maxLength={120}
                  />
                  <datalist id="transfer-bank-options">
                    {banks.map(bank => (
                      <option key={bank.id} value={bank.name} />
                    ))}
                  </datalist>
                  {formErrors.transferBankName && (
                    <p className="text-xs text-red-600">{formErrors.transferBankName}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="transfer-reference">Número de referencia</Label>
                  <Input
                    id="transfer-reference"
                    value={transferReference}
                    onChange={(e) => {
                      setTransferReference(e.target.value)
                      clearFieldError('transferReference')
                    }}
                    placeholder="Ej: 84291372"
                    maxLength={120}
                  />
                  <p className="text-xs text-muted-foreground">
                    Se valida contra referencias previas para evitar pagos duplicados/fraude.
                  </p>
                  {formErrors.transferReference && (
                    <p className="text-xs text-red-600">{formErrors.transferReference}</p>
                  )}
                </div>
              </div>
            )}

            {/* V2.1: Financing Options */}
            {(metodoPago === 'tarjeta' || metodoPago === 'financiamiento') && (
              <div className="bg-muted/30 p-3 rounded-md border border-dashed space-y-3">
                 <div className="flex items-center justify-between">
                   <div className="flex items-center gap-2 text-sm font-medium text-primary">
                      <CreditCard className="w-4 h-4" />
                      {metodoPago === 'financiamiento' ? 'Opciones de Extrafinanciamiento' : 'Cobro con Tarjeta'}
                   </div>
                 </div>
                 
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                       <Label className="text-xs">Banco</Label>
                       <Select 
                          value={selectedBankId?.toString() || ''} 
                          onValueChange={(v) => {
                             setSelectedBankId(Number(v))
                             setSelectedMonths(null) // Reset months
                          }}
                       >
                          <SelectTrigger className="h-8 text-xs">
                             <SelectValue placeholder="Seleccionar Banco" />
                          </SelectTrigger>
                          <SelectContent>
                             {banks.map(bank => (
                                <SelectItem key={bank.id} value={bank.id.toString()}>
                                   {bank.name} {metodoPago === 'tarjeta' && Number(bank.normal_card_rate) > 0 ? `(${Number(bank.normal_card_rate * 100).toFixed(2)}%)` : ''}
                                </SelectItem>
                             ))}
                          </SelectContent>
                       </Select>
                    </div>
                    
                    {metodoPago === 'financiamiento' && (
                      <div className="space-y-1">
                         <Label className="text-xs">Plazo</Label>
                         <Select 
                            value={selectedMonths?.toString() || ''} 
                            onValueChange={(v) => setSelectedMonths(Number(v))}
                            disabled={!selectedBankId}
                         >
                            <SelectTrigger className="h-8 text-xs">
                               <SelectValue placeholder="Meses" />
                            </SelectTrigger>
                            <SelectContent>
                               {selectedBankId && banks.find(b => b.id === selectedBankId)?.financing_options.map(opt => (
                                  <SelectItem key={opt.id} value={opt.months.toString()}>
                                     {opt.months} Meses ({Number(opt.rate) * 100}%)
                                  </SelectItem>
                               ))}
                            </SelectContent>
                         </Select>
                      </div>
                    )}

                    <div className="space-y-1 col-span-2 border-t pt-2 mt-1">
                       <Label className="text-xs">Prima / Pago Inicial (Efectivo/Transf.)</Label>
                       <Input 
                          type="number" 
                          className="h-8 text-xs" 
                          placeholder="0.00"
                          value={cashDownPayment}
                          onChange={(e) => setCashDownPayment(e.target.value)}
                       />
                    </div>
                 </div>

                 {selectedBankId && (
                    <div className="text-xs bg-background p-2 rounded border space-y-1">
                       {metodoPago === 'tarjeta' && (
                          <div className="text-blue-600 font-medium mb-1">
                             Cobro con tarjeta aplica tasa normal
                          </div>
                       )}
                       {(() => {
                          const bank = banks.find(b => b.id === selectedBankId)
                          if (!bank) return null

                          // Calcular base total (items - tradeins)
                          const itemsTotal = items.reduce((total, item) => {
                             const product = products.find(p => p.id === item.product_id)
                             if (!product) return total
                             const price = item.precio_unitario !== undefined ? item.precio_unitario : product.precio
                             return total + price * item.cantidad
                          }, 0)
                          const tradeInsTotal = tradeIns.reduce((total, item) => total + (Number(item.valor_estimado) || 0), 0)
                          
                          // V2.1: Split Payment Logic
                          const downPayment = parseFloat(cashDownPayment) || 0
                          
                          // Base para cálculo de intereses = Total Productos - TradeIns - Prima
                          const financedAmount = Math.max(0, itemsTotal - tradeInsTotal - downPayment)

                          let surcharge = 0
                          let rate = 0
                          let monthly = 0

                          if (metodoPago === 'financiamiento' && selectedMonths) {
                             const option = bank.financing_options.find(o => o.months === selectedMonths)
                             if (option) {
                                rate = Number(option.rate)
                                surcharge = financedAmount * rate
                                monthly = (financedAmount + surcharge) / selectedMonths
                             }
                          } else if (metodoPago === 'tarjeta') {
                             rate = Number(bank.normal_card_rate || 0)
                             surcharge = financedAmount * rate
                          }
                          
                          return (
                             <>
                                <div className="flex justify-between text-muted-foreground">
                                   <span>Subtotal Productos:</span>
                                   <span>HNL {itemsTotal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                </div>
                                
                                {tradeInsTotal > 0 && (
                                   <div className="flex justify-between text-green-600 font-medium">
                                      <span>(-) Trade-In (Retoma):</span>
                                      <span>HNL {tradeInsTotal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                   </div>
                                )}
                                
                                {downPayment > 0 && (
                                   <div className="flex justify-between text-green-600 font-medium">
                                      <span>(-) Prima / Efectivo:</span>
                                      <span>HNL {downPayment.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                   </div>
                                )}

                                <div className="flex justify-between font-medium border-t border-dashed pt-1">
                                   <span>Monto a Financiar:</span>
                                   <span>HNL {financedAmount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                </div>

                                <div className="flex justify-between text-red-500">
                                   <span>(+) Recargo ({Number(rate*100).toFixed(2)}%):</span>
                                   <span>HNL {surcharge.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                </div>

                                <div className="flex justify-between font-bold border-t pt-1 mt-1">
                                   <span>A Cobrar en POS:</span>
                                   <span>HNL {(financedAmount + surcharge).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                                </div>

                                {monthly > 0 && (
                                  <div className="mt-3 bg-blue-50 p-3 rounded text-center border border-blue-100">
                                     <div className="text-xs text-blue-600 uppercase font-bold tracking-wider">Cuota Mensual ({selectedMonths} meses)</div>
                                     <div className="text-xl font-bold text-blue-700">HNL {monthly.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                  </div>
                                )}
                             </>
                          )
                       })()}
                    </div>
                 )}
              </div>
            )}

          <div className="space-y-2">
            <Label htmlFor="notas">Notas (opcional)</Label>
              <Textarea
                maxLength={ORDER_FIELD_LIMITS.MAX_ORDER_NOTES_LENGTH}
              id="notas"
              value={notas}
              onChange={e => setNotas(e.target.value)}
              placeholder="Instrucciones especiales, comentarios, etc..."
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="delivery-date">Fecha programada de entrega (opcional)</Label>
            <Input
              id="delivery-date"
              type="datetime-local"
              value={deliveryDate}
              onChange={e => setDeliveryDate(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              La fecha y hora de creacion de la orden se registran automaticamente al guardarla.
            </p>
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
