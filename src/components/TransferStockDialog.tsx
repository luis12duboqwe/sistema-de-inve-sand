import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
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
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowsLeftRight, MapPin, Package, WarningCircle as AlertCircle } from '@phosphor-icons/react'
import { calculateLuhnCheckDigit } from '@/lib/utils'

import type { CreateStockTransferRequest, Location, ProductWithStock } from '@/lib/types'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { createTransferStockSchema, type TransferStockFormValues } from '@/lib/validation/transferStockSchema'

interface TransferStockDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock | null
  onTransferComplete: () => void
  initialFromLocationId?: number
  initialToLocationId?: number
}

export function TransferStockDialog({
  open,
  onOpenChange,
  product,
  onTransferComplete,
  initialFromLocationId,
  initialToLocationId
}: TransferStockDialogProps) {
  const [locations, setLocations] = useState<Location[]>([])
  const [availableImeis, setAvailableImeis] = useState<string[]>([])
  const [selectedImeis, setSelectedImeis] = useState<string[]>([])
  const [originScanInput, setOriginScanInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const scannerInputRef = useRef<HTMLInputElement | null>(null)

  const isSerializedProduct = Boolean(product?.is_serialized || product?.categoria === 'celular')
  const schema = useMemo(() => createTransferStockSchema(product), [product])

  const {
    control,
    handleSubmit: handleFormSubmit,
    watch,
    reset,
    setValue,
    clearErrors,
    formState: { errors }
  } = useForm<TransferStockFormValues>({
    resolver: zodResolver(schema)
  })

  const fromLocationId = watch('fromLocationId')
  const toLocationId = watch('toLocationId')
  const cantidad = watch('cantidad') ?? 0

  useEffect(() => {
    if (!open) return

    const loadLocations = async () => {
      setLoading(true)
      try {
        const data = await inventoryServiceInstance.getLocations()
        setLocations(data.filter(location => location.activo))
      } catch (error) {
        console.error('Error al cargar ubicaciones:', error)
        toast.error('Error al cargar ubicaciones')
      } finally {
        setLoading(false)
      }
    }

    loadLocations()
    reset()
    setAvailableImeis([])
    setSelectedImeis([])
    setOriginScanInput('')
  }, [open, reset])

  // Pre-rellenar origen/destino cuando llegan como prop
  useEffect(() => {
    if (!open) return
    if (initialFromLocationId) setValue('fromLocationId', initialFromLocationId)
    if (initialToLocationId) setValue('toLocationId', initialToLocationId)
  }, [open, initialFromLocationId, initialToLocationId, setValue])

  useEffect(() => {
    if (!product || !fromLocationId || !isSerializedProduct) {
      setAvailableImeis([])
      setSelectedImeis([])
      setOriginScanInput('')
      return
    }

    inventoryServiceInstance
      .getAvailableIMEIs(product.id, fromLocationId)
      .then(setAvailableImeis)
      .catch(error => {
        console.error('Error cargando IMEIs disponibles:', error)
        setAvailableImeis([])
      })

    setSelectedImeis([])
    setOriginScanInput('')
  }, [fromLocationId, isSerializedProduct, product])

  useEffect(() => {
    if (!open || !isSerializedProduct || !fromLocationId || cantidad <= 0) {
      return
    }

    requestAnimationFrame(() => scannerInputRef.current?.focus())
  }, [open, isSerializedProduct, fromLocationId, cantidad])

  const availableStock = useMemo(() => {
    if (!product || !fromLocationId) return 0
    const stockItem = product.stock_items?.find(item => item.location_id === fromLocationId)
    const disponible = stockItem?.cantidad_disponible || 0
    const reservado = stockItem?.cantidad_reservada || 0
    return Math.max(disponible - reservado, 0)
  }, [fromLocationId, product])

  const fromLocation = locations.find(location => location.id === fromLocationId)
  const toLocation = locations.find(location => location.id === toLocationId)
  const availableDestinations = locations.filter(location => location.id !== fromLocationId)

  const handleFromLocationChange = (value: string, onChange: (val: number | undefined) => void) => {
    const parsed = value ? Number(value) : undefined
    onChange(parsed)

    setValue('toLocationId', undefined as unknown as TransferStockFormValues['toLocationId'], {
      shouldValidate: false,
      shouldDirty: false
    })
    setValue('cantidad', 0 as TransferStockFormValues['cantidad'], {
      shouldValidate: false,
      shouldDirty: false
    })

    setSelectedImeis([])
    setAvailableImeis([])
    setOriginScanInput('')
    clearErrors(['toLocationId', 'cantidad'])
  }

  const normalizeImeiForScanner = (value: string): string => {
    const cleaned = value.replace(/\D/g, '')
    if (cleaned.length === 14) {
      try {
        return cleaned + calculateLuhnCheckDigit(cleaned)
      } catch {
        return cleaned
      }
    }
    return cleaned
  }

  const handleScanOriginImei = () => {
    const scanned = normalizeImeiForScanner(originScanInput.trim())
    if (!scanned) {
      toast.error('Escanea o escribe un IMEI válido')
      return
    }

    if (scanned.length !== 15) {
      toast.error('El IMEI escaneado debe tener 15 dígitos')
      return
    }

    if (!cantidad || cantidad <= 0) {
      toast.error('Primero indica la cantidad a transferir')
      return
    }

    if (!fromLocationId) {
      toast.error('Selecciona la ubicación origen antes de escanear')
      return
    }

    if (!availableImeis.includes(scanned)) {
      toast.error('Este IMEI no está disponible en la ubicación origen seleccionada')
      setOriginScanInput('')
      requestAnimationFrame(() => scannerInputRef.current?.focus())
      return
    }

    if (selectedImeis.includes(scanned)) {
      toast.error('Este IMEI ya fue escaneado en origen')
      setOriginScanInput('')
      requestAnimationFrame(() => scannerInputRef.current?.focus())
      return
    }

    if (selectedImeis.length >= cantidad) {
      toast.error(`Ya se escanearon las ${cantidad} unidades requeridas`)
      setOriginScanInput('')
      requestAnimationFrame(() => scannerInputRef.current?.focus())
      return
    }

    setSelectedImeis(previous => [...previous, scanned])
    setOriginScanInput('')
    requestAnimationFrame(() => scannerInputRef.current?.focus())
  }

  const onSubmitForm = async (values: TransferStockFormValues) => {
    if (!product) {
      toast.error('No hay producto seleccionado')
      return
    }

    if (isSerializedProduct && selectedImeis.length !== values.cantidad) {
      toast.error(`Debes escanear ${values.cantidad} IMEIs en la ubicación origen para transferir`)
      return
    }

    const payload: CreateStockTransferRequest = {
      product_id: product.id,
      from_location_id: values.fromLocationId,
      to_location_id: values.toLocationId,
      cantidad: values.cantidad,
      notas: values.notas,
      imeis: selectedImeis.length > 0 ? selectedImeis : undefined,
      created_by: 'Sistema'
    }

    setIsSubmitting(true)
    try {
      await inventoryServiceInstance.createStockTransfer(payload)

      const fromName = locations.find(location => location.id === values.fromLocationId)?.nombre
      const toName = locations.find(location => location.id === values.toLocationId)?.nombre

      toast.success(`✅ Transferencia creada: ${values.cantidad} unidades de "${fromName}" → "${toName}"`, {
        duration: 5000
      })

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
                <div className="grid gap-2">
                  <Label htmlFor="from_location">Ubicación origen *</Label>
                  <Controller
                    control={control}
                    name="fromLocationId"
                    render={({ field }) => (
                      <Select
                        value={field.value ? String(field.value) : ''}
                        onValueChange={value => handleFromLocationChange(value, field.onChange)}
                      >
                        <SelectTrigger id="from_location">
                          <SelectValue placeholder="Selecciona ubicación origen" />
                        </SelectTrigger>
                        <SelectContent>
                          {locations.length === 0 ? (
                            <div className="p-2 text-sm text-muted-foreground">No hay ubicaciones disponibles</div>
                          ) : (
                            locations.map(location => {
                              const stockItem = product.stock_items?.find(item => item.location_id === location.id)
                              const disponible = stockItem?.cantidad_disponible || 0
                              const reservado = stockItem?.cantidad_reservada || 0
                              const stockLibre = Math.max(disponible - reservado, 0)

                              return (
                                <SelectItem key={location.id} value={String(location.id)} disabled={stockLibre === 0}>
                                  <div className="flex items-center justify-between gap-3 w-full">
                                    <div className="flex items-center gap-2">
                                      <MapPin className="w-4 h-4" weight="fill" />
                                      <span>{location.nombre}</span>
                                    </div>
                                    <Badge variant={stockLibre > 0 ? 'default' : 'secondary'} className="ml-2">
                                      {stockLibre} unid.
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
                  {errors.fromLocationId && <p className="text-xs text-red-600">{errors.fromLocationId.message}</p>}
                  {fromLocation && (
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {fromLocation.tipo} • Stock disponible: <strong>{availableStock} unidades</strong>
                    </p>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="to_location">Ubicación recepción *</Label>
                  {!fromLocationId ? (
                    <div className="flex items-center gap-2 p-3 rounded-lg border bg-muted/50 text-muted-foreground">
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-sm">Primero selecciona la ubicación de origen</span>
                    </div>
                  ) : availableDestinations.length === 0 ? (
                    <div className="flex items-center gap-2 p-3 rounded-lg border border-yellow-200 bg-yellow-50 text-yellow-800">
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-sm">No hay otras ubicaciones disponibles para transferencia</span>
                    </div>
                  ) : (
                    <>
                      <Controller
                        control={control}
                        name="toLocationId"
                        render={({ field }) => (
                          <Select
                            value={field.value ? String(field.value) : ''}
                            onValueChange={value => field.onChange(value ? Number(value) : undefined)}
                            disabled={!fromLocationId}
                          >
                            <SelectTrigger id="to_location">
                              <SelectValue placeholder="Selecciona ubicación recepción" />
                            </SelectTrigger>
                            <SelectContent>
                              {availableDestinations.map(location => (
                                <SelectItem key={location.id} value={String(location.id)}>
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
                      {errors.toLocationId && <p className="text-xs text-red-600">{errors.toLocationId.message}</p>}
                      {toLocation && (
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {toLocation.direccion || `${toLocation.tipo} sin dirección`}
                        </p>
                      )}
                    </>
                  )}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="cantidad">Cantidad a transferir *</Label>
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
                        onChange={event => {
                          const value = event.target.value
                          field.onChange(value === '' ? undefined : Number(value))
                          clearErrors('cantidad')
                        }}
                        placeholder="0"
                        required
                        disabled={!fromLocationId || availableStock === 0}
                      />
                    )}
                  />
                  {errors.cantidad && <p className="text-xs text-red-600">{errors.cantidad.message}</p>}
                  {fromLocationId && (
                    <p className="text-xs text-muted-foreground">
                      Máximo disponible: <strong>{availableStock} unidades</strong>
                    </p>
                  )}
                </div>

                {isSerializedProduct && fromLocationId && (
                  <div className="grid gap-2">
                    <Label>Escanear IMEIs en origen ({selectedImeis.length}/{cantidad || 0})</Label>
                    <div className="bg-muted/30 p-3 rounded-lg border border-dashed space-y-3">
                      <div className="flex gap-2">
                        <Input
                          ref={scannerInputRef}
                          autoFocus
                          value={originScanInput}
                          onChange={event => setOriginScanInput(event.target.value)}
                          onKeyDown={event => {
                            if (event.key === 'Enter') {
                              event.preventDefault()
                              handleScanOriginImei()
                            }
                          }}
                          placeholder="Escanea o escribe IMEI en ubicación origen"
                          disabled={!fromLocationId || !cantidad || availableImeis.length === 0}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          onClick={handleScanOriginImei}
                          disabled={!originScanInput.trim() || !fromLocationId || !cantidad || availableImeis.length === 0}
                        >
                          Registrar
                        </Button>
                      </div>

                      {availableImeis.length === 0 ? (
                        <div className="text-sm text-muted-foreground italic">No hay IMEIs disponibles en esta ubicación.</div>
                      ) : (
                        <>
                          <div className="text-xs text-muted-foreground">IMEIs disponibles en origen: {availableImeis.length}</div>
                          <div className="flex flex-wrap gap-2">
                            {selectedImeis.map(imei => (
                              <div
                                key={imei}
                                className="px-2 py-1 text-xs rounded border bg-primary text-primary-foreground border-primary font-medium cursor-pointer"
                                onClick={() => setSelectedImeis(previous => previous.filter(item => item !== imei))}
                                title="Quitar IMEI escaneado"
                              >
                                {imei}
                              </div>
                            ))}
                          </div>
                          {selectedImeis.length === 0 && (
                            <div className="text-sm text-muted-foreground italic">Aún no se ha escaneado ningún IMEI en origen.</div>
                          )}
                        </>
                      )}

                      {cantidad > selectedImeis.length && cantidad > 0 && (
                        <div className="text-xs text-amber-600 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          Faltan escanear {cantidad - selectedImeis.length} IMEIs en origen
                        </div>
                      )}

                      {selectedImeis.length > 0 && (
                        <div className="text-xs text-muted-foreground">
                          Haz clic sobre un IMEI escaneado para quitarlo si hubo error de lectura.
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="grid gap-2">
                  <Label htmlFor="notas">Notas (opcional)</Label>
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

                {fromLocationId && toLocationId && cantidad > 0 && (
                  <div className="flex items-center gap-2 p-4 rounded-lg border-2 border-primary/20 bg-primary/5">
                    <div className="flex-1">
                      <div className="text-sm font-medium text-primary mb-1">📦 Resumen de transferencia:</div>
                      <div className="text-sm">
                        <strong>{cantidad} unidades</strong> de <strong>"{fromLocation?.nombre}"</strong>
                        <ArrowsLeftRight className="inline mx-1 w-4 h-4" weight="bold" />
                        <strong>"{toLocation?.nombre}"</strong>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex items-start gap-2 p-3 rounded-lg border border-blue-200 bg-blue-50 text-blue-800">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div className="text-xs">
                    <strong>Importante:</strong> La transferencia quedará pendiente de recepción.{' '}
                    {isSerializedProduct
                      ? 'Debes escanear cada unidad en origen ahora y volver a escanearla en la ubicación de recepción para completarla.'
                      : 'La ubicación de recepción deberá confirmar la llegada para completar el movimiento.'}
                  </div>
                </div>
              </>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
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
                (isSerializedProduct && cantidad > 0 && selectedImeis.length !== cantidad)
              }
            >
              {isSubmitting ? 'Registrando...' : 'Registrar Transferencia'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
