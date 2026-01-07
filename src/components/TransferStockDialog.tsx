import { useState, useEffect, useMemo } from 'react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import type { ProductWithStock, Location, CreateStockTransferRequest } from '@/lib/types'
import { ArrowsLeftRight, WarningCircle as AlertCircle, MapPin, Package } from '@phosphor-icons/react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { createTransferStockSchema, type TransferStockFormValues } from '@/lib/validation/transferStockSchema'

interface TransferStockDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock | null
  onTransferComplete: () => void
}

export function TransferStockDialog({
  open,
  onOpenChange,
  product,
  onTransferComplete
}: TransferStockDialogProps) {
  const [locations, setLocations] = useState<Location[]>([])
  const [selectedImeis, setSelectedImeis] = useState<string[]>([])
  const [availableImeis, setAvailableImeis] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [loading, setLoading] = useState(false)

  const schema = useMemo(() => createTransferStockSchema(product), [product])

  const {
    control,
    handleSubmit: handleFormSubmit,
    reset,
    watch,
    setValue,
    clearErrors,
    formState: { errors }
  } = useForm<TransferStockFormValues>({
    resolver: zodResolver(schema)
  })

  const fromLocationId = watch('fromLocationId')
  const toLocationId = watch('toLocationId')
  const cantidad = watch('cantidad') ?? 0

  const handleFromLocationChange = (value: string, onChange: (val: number | undefined) => void) => {
    const parsed = value ? Number(value) : undefined
    onChange(parsed)
    setValue(
      'toLocationId',
      undefined as unknown as TransferStockFormValues['toLocationId'],
      { shouldValidate: false, shouldDirty: false }
    )
    setValue(
      'cantidad',
      0 as TransferStockFormValues['cantidad'],
      { shouldValidate: false, shouldDirty: false }
    )
    setSelectedImeis([])
    setAvailableImeis([])
    clearErrors(['toLocationId', 'cantidad'])
  }

  // Cargar ubicaciones cuando se abre el dialog
  useEffect(() => {
    if (open) {
      loadLocations()
      reset()
      setSelectedImeis([])
      setAvailableImeis([])
    }
  }, [open, reset])

  // Cargar IMEIs cuando cambia la ubicación de origen
  useEffect(() => {
    if (fromLocationId && product?.categoria === 'celular') {
      inventoryServiceInstance.getAvailableIMEIs(product.id, fromLocationId)
        .then(setAvailableImeis)
        .catch(console.error)
    } else {
      setAvailableImeis([])
    }
    setSelectedImeis([])
  }, [fromLocationId, product])

  const loadLocations = async () => {
    setLoading(true)
    try {
      const data = await inventoryServiceInstance.getLocations()
      setLocations(data.filter(l => l.activo))
    } catch (error) {
      console.error('Error al cargar ubicaciones:', error)
      toast.error('Error al cargar ubicaciones')
    } finally {
      setLoading(false)
    }
  }

  // Obtener stock disponible en ubicación origen
  const getAvailableStock = () => {
    if (!product || !fromLocationId) return 0
    const stockItem = product.stock_items?.find(s => s.location_id === fromLocationId)
    const disponible = stockItem?.cantidad_disponible || 0
    const reservado = stockItem?.cantidad_reservada || 0
    return Math.max(disponible - reservado, 0)
  }

  // Ubicaciones de destino disponibles (excluir la de origen)
  const availableDestinations = locations.filter(l => l.id !== fromLocationId)

  const onSubmitForm = async (values: TransferStockFormValues) => {
    if (!product) {
      toast.error('No hay producto seleccionado')
      return
    }

    const cantidadNum = values.cantidad
    const fromId = values.fromLocationId
    const toId = values.toLocationId

    if (product.categoria === 'celular' && selectedImeis.length !== cantidadNum) {
      toast.error(`Debes seleccionar ${cantidadNum} IMEIs para transferir`)
      return
    }

    setIsSubmitting(true)

    try {
      const transferData: CreateStockTransferRequest = {
        product_id: product.id,
        from_location_id: fromId,
        to_location_id: toId,
        cantidad: cantidadNum,
        imeis: selectedImeis.length > 0 ? selectedImeis : undefined,
        notas: values.notas,
        created_by: 'Sistema'
      }

      await inventoryServiceInstance.createStockTransfer(transferData)

      const fromLoc = locations.find(l => l.id === fromId)
      const toLoc = locations.find(l => l.id === toId)

      toast.success(
        `✅ Transferencia creada: ${cantidadNum} unidades de "${fromLoc?.nombre}" → "${toLoc?.nombre}"`,
        { duration: 5000 }
      )

      onTransferComplete()
      onOpenChange(false)
    } catch (error) {
      console.error('Error al transferir stock:', error)
      toast.error(error instanceof Error ? error.message : 'Error al transferir stock')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!product) return null

  const availableStock = getAvailableStock()
  const fromLocation = locations.find(l => l.id === fromLocationId)
  const toLocation = locations.find(l => l.id === toLocationId)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-[550px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowsLeftRight className="w-5 h-5" weight="bold" />
            Transferir Stock entre Ubicaciones
          </DialogTitle>
          <DialogDescription>
            Mueve inventario de este producto entre tus tiendas y bodegas
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleFormSubmit(onSubmitForm)}>
          <div className="space-y-4 py-4">
            {/* Información del producto */}
            <div className="rounded-lg border-2 border-primary/20 p-4 bg-primary/5">
              <div className="flex items-center gap-3">
                <Package className="w-8 h-8 text-primary" weight="duotone" />
                <div className="flex-1">
                  <div className="font-semibold">{product.nombre}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    SKU: {product.sku} • Stock total: {product.stock_disponible} unidades
                  </div>
                </div>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-4 text-muted-foreground">Cargando ubicaciones...</div>
            ) : (
              <>
                {/* Ubicación de origen */}
                <div className="grid gap-2">
                  <Label htmlFor="from_location">Desde (Ubicación Origen) *</Label>
                  <Controller
                    control={control}
                    name="fromLocationId"
                    render={({ field }) => (
                      <Select
                        value={field.value ? field.value.toString() : ''}
                        onValueChange={value => handleFromLocationChange(value, field.onChange)}
                      >
                        <SelectTrigger id="from_location">
                          <SelectValue placeholder="Selecciona ubicación de origen" />
                        </SelectTrigger>
                        <SelectContent>
                          {locations.length === 0 ? (
                            <div className="p-2 text-sm text-muted-foreground">No hay ubicaciones disponibles</div>
                          ) : (
                            locations.map(location => {
                              const stockItem = product.stock_items?.find(s => s.location_id === location.id)
                              const disponible = stockItem?.cantidad_disponible || 0
                              const reservado = stockItem?.cantidad_reservada || 0
                              const stock = Math.max(disponible - reservado, 0)
                              return (
                                <SelectItem key={location.id} value={location.id.toString()} disabled={stock === 0}>
                                  <div className="flex items-center justify-between gap-3 w-full">
                                    <div className="flex items-center gap-2">
                                      <MapPin className="w-4 h-4" weight="fill" />
                                      <span>{location.nombre}</span>
                                    </div>
                                    <Badge variant={stock > 0 ? 'default' : 'secondary'} className="ml-2">
                                      {stock} unid.
                                    </Badge>
                                  </div>
                                </SelectItem>
                              )
                            })
                          )}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.fromLocationId && (
                    <p className="text-xs text-red-600">{errors.fromLocationId.message}</p>
                  )}
                  {fromLocationId && fromLocation && (
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {fromLocation.tipo} • Stock disponible: <strong>{availableStock} unidades</strong>
                    </p>
                  )}
                </div>

                {/* Ubicación de destino */}
                <div className="grid gap-2">
                  <Label htmlFor="to_location">Hacia (Ubicación Destino) *</Label>
                  {!fromLocationId ? (
                    <div className="flex items-center gap-2 p-3 rounded-lg border bg-muted/50 text-muted-foreground">
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-sm">Primero selecciona la ubicación de origen</span>
                    </div>
                  ) : availableDestinations.length === 0 ? (
                    <div className="flex items-center gap-2 p-3 rounded-lg border border-yellow-200 bg-yellow-50 text-yellow-800">
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-sm">
                        No hay otras ubicaciones disponibles para transferencia
                      </span>
                    </div>
                  ) : (
                    <>
                      <Controller
                        control={control}
                        name="toLocationId"
                        render={({ field }) => (
                          <Select
                            value={field.value ? field.value.toString() : ''}
                            onValueChange={value => field.onChange(value ? Number(value) : undefined)}
                            disabled={!fromLocationId}
                          >
                            <SelectTrigger id="to_location">
                              <SelectValue placeholder="Selecciona ubicación de destino" />
                            </SelectTrigger>
                            <SelectContent>
                              {availableDestinations.map(location => (
                                <SelectItem key={location.id} value={location.id.toString()}>
                                  <div className="flex items-center gap-2">
                                    <MapPin className="w-4 h-4" weight="fill" />
                                    <span>{location.nombre}</span>
                                    <Badge variant="outline" className="ml-2 capitalize">
                                      {location.tipo}
                                    </Badge>
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                      />
                      {errors.toLocationId && (
                        <p className="text-xs text-red-600">{errors.toLocationId.message}</p>
                      )}
                      {toLocationId && toLocation && (
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {toLocation.direccion || `${toLocation.tipo} sin dirección`}
                        </p>
                      )}
                    </>
                  )}
                </div>

                {/* Cantidad */}
                <div className="grid gap-2">
                  <Label htmlFor="cantidad">Cantidad a Transferir *</Label>
                  <Controller
                    control={control}
                    name="cantidad"
                    render={({ field }) => (
                      <Input
                        id="cantidad"
                        type="number"
                        min="1"
                        max={availableStock}
                        value={field.value ?? ''}
                        onChange={e => {
                          const value = e.target.value
                          field.onChange(value === '' ? undefined : Number(value))
                          clearErrors('cantidad')
                        }}
                        placeholder="0"
                        required
                        disabled={!fromLocationId || availableStock === 0}
                      />
                    )}
                  />
                  {errors.cantidad && (
                    <p className="text-xs text-red-600">{errors.cantidad.message}</p>
                  )}
                  {fromLocationId && (
                    <p className="text-xs text-muted-foreground">
                      Máximo disponible: <strong>{availableStock} unidades</strong>
                    </p>
                  )}
                </div>

                {/* IMEI Selector */}
                {product.categoria === 'celular' && fromLocationId && (
                  <div className="grid gap-2">
                    <Label>Seleccionar IMEIs ({selectedImeis.length}/{cantidad || 0})</Label>
                    <div className="bg-muted/30 p-3 rounded-lg border border-dashed">
                      {availableImeis.length === 0 ? (
                        <div className="text-sm text-muted-foreground italic">
                          No hay IMEIs disponibles en esta ubicación.
                        </div>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {availableImeis.map(imei => {
                            const isSelected = selectedImeis.includes(imei)
                            return (
                              <div 
                                key={imei}
                                onClick={() => {
                                  const qty = cantidad || 0
                                  if (isSelected) {
                                    setSelectedImeis(prev => prev.filter(i => i !== imei))
                                  } else {
                                    if (selectedImeis.length >= qty) {
                                      if (qty === 0) {
                                        toast.error('Primero ingresa la cantidad a transferir')
                                      } else {
                                        toast.error(`Solo puedes seleccionar ${qty} IMEIs`)
                                      }
                                      return
                                    }
                                    setSelectedImeis(prev => [...prev, imei])
                                  }
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
                      {cantidad > selectedImeis.length && cantidad > 0 && (
                        <div className="mt-2 text-xs text-amber-600 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          Faltan seleccionar {cantidad - selectedImeis.length} IMEIs
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Notas */}
                <div className="grid gap-2">
                  <Label htmlFor="notas">Notas (Opcional)</Label>
                  <Controller
                    control={control}
                    name="notas"
                    render={({ field }) => (
                      <Textarea
                        id="notas"
                        maxLength={500}
                        value={field.value ?? ''}
                        onChange={field.onChange}
                        placeholder="Razón de la transferencia, observaciones, etc."
                        rows={2}
                        disabled={!fromLocationId}
                      />
                    )}
                  />
                  {errors.notas && <p className="text-xs text-red-600">{errors.notas.message}</p>}
                </div>

                {/* Resumen de transferencia */}
                {fromLocationId && toLocationId && cantidad > 0 && (
                  <div className="flex items-center gap-2 p-4 rounded-lg border-2 border-primary/20 bg-primary/5">
                    <div className="flex-1">
                      <div className="text-sm font-medium text-primary mb-1">
                        📦 Resumen de Transferencia:
                      </div>
                      <div className="text-sm">
                        <strong>{cantidad} unidades</strong> de <strong>"{fromLocation?.nombre}"</strong>
                        <ArrowsLeftRight className="inline mx-1 w-4 h-4" weight="bold" />
                        <strong>"{toLocation?.nombre}"</strong>
                      </div>
                    </div>
                  </div>
                )}

                {/* Advertencia */}
                <div className="flex items-start gap-2 p-3 rounded-lg border border-blue-200 bg-blue-50 text-blue-800">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div className="text-xs">
                    <strong>Importante:</strong> La transferencia se ejecutará inmediatamente. 
                    El stock se descontará de la ubicación origen y se sumará a la ubicación destino.
                  </div>
                </div>
              </>
            )}
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
            <Button
              type="submit"
              disabled={
                isSubmitting || 
                !fromLocationId || 
                !toLocationId || 
                availableStock === 0 ||
                cantidad <= 0 ||
                (product.categoria === 'celular' && cantidad > 0 && selectedImeis.length !== cantidad)
              }
            >
              {isSubmitting ? 'Transfiriendo...' : 'Transferir Stock'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
