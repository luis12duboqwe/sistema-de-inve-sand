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
import { ArrowsLeftRight, AlertCircle, MapPin, Package } from '@phosphor-icons/react'
import { apiClient } from '@/lib/apiClient'

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
  const [fromLocationId, setFromLocationId] = useState<number | null>(null)
  const [toLocationId, setToLocationId] = useState<number | null>(null)
  const [cantidad, setCantidad] = useState('')
  const [notas, setNotas] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [loading, setLoading] = useState(false)

  // Cargar ubicaciones cuando se abre el dialog
  useEffect(() => {
    if (open) {
      loadLocations()
      // Reset form
      setFromLocationId(null)
      setToLocationId(null)
      setCantidad('')
      setNotas('')
    }
  }, [open])

  const loadLocations = async () => {
    setLoading(true)
    try {
      const data = await apiClient.listLocations()
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
    return stockItem?.cantidad_disponible || 0
  }

  // Ubicaciones de destino disponibles (excluir la de origen)
  const availableDestinations = locations.filter(l => l.id !== fromLocationId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!product) {
      toast.error('No hay producto seleccionado')
      return
    }

    if (!fromLocationId) {
      toast.error('Selecciona una ubicación de origen')
      return
    }

    if (!toLocationId) {
      toast.error('Selecciona una ubicación de destino')
      return
    }

    const cantidadNum = parseInt(cantidad)
    if (isNaN(cantidadNum) || cantidadNum <= 0) {
      toast.error('La cantidad debe ser mayor a 0')
      return
    }

    const availableStock = getAvailableStock()
    if (cantidadNum > availableStock) {
      toast.error(`Stock insuficiente en ubicación origen. Disponible: ${availableStock}`)
      return
    }

    setIsSubmitting(true)

    try {
      const transferData: CreateStockTransferRequest = {
        product_id: product.id,
        from_location_id: fromLocationId,
        to_location_id: toLocationId,
        cantidad: cantidadNum,
        notas: notas.trim() || undefined,
        created_by: 'Sistema'
      }

      await apiClient.createStockTransfer(transferData)

      const fromLoc = locations.find(l => l.id === fromLocationId)
      const toLoc = locations.find(l => l.id === toLocationId)
      
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

        <form onSubmit={handleSubmit}>
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
                  <Select 
                    value={fromLocationId?.toString() || ''} 
                    onValueChange={(v) => {
                      setFromLocationId(parseInt(v))
                      setToLocationId(null) // Reset destino cuando cambia origen
                      setCantidad('') // Reset cantidad
                    }}
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
                          const stock = stockItem?.cantidad_disponible || 0
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
                      <Select 
                        value={toLocationId?.toString() || ''} 
                        onValueChange={(v) => setToLocationId(parseInt(v))}
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
                  <Input
                    id="cantidad"
                    type="number"
                    min="1"
                    max={availableStock}
                    value={cantidad}
                    onChange={e => setCantidad(e.target.value)}
                    placeholder="0"
                    required
                    disabled={!fromLocationId || availableStock === 0}
                  />
                  {fromLocationId && (
                    <p className="text-xs text-muted-foreground">
                      Máximo disponible: <strong>{availableStock} unidades</strong>
                    </p>
                  )}
                </div>

                {/* Notas */}
                <div className="grid gap-2">
                  <Label htmlFor="notas">Notas (Opcional)</Label>
                  <Textarea
                    id="notas"
                    value={notas}
                    onChange={e => setNotas(e.target.value)}
                    placeholder="Razón de la transferencia, observaciones, etc."
                    rows={2}
                    disabled={!fromLocationId}
                  />
                </div>

                {/* Resumen de transferencia */}
                {fromLocationId && toLocationId && cantidad && parseInt(cantidad) > 0 && (
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
                !cantidad ||
                parseInt(cantidad) <= 0
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
