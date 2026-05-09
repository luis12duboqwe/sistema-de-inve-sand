import { useState, useEffect, useCallback } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { ScrollArea } from './ui/scroll-area'
import { Loader2, Check, X, Clock, Package, MapPin, ArrowRight, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import { inventoryServiceInstance } from '../lib/inventoryServiceFactory'
import { apiClient } from '../lib/apiClient'
import { StockTransfer, Location } from '../lib/types'
import { ValidationCodeDialog } from './ValidationCodeDialog'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'

interface TransferListDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  locations: Location[]
  currentLocationId?: number  // Para filtrar transferencias relevantes
  onTransferUpdated?: () => void
}

export function TransferListDialog({
  open,
  onOpenChange,
  locations,
  currentLocationId,
  onTransferUpdated
}: TransferListDialogProps) {
  const [loading, setLoading] = useState(false)
  const [transfers, setTransfers] = useState<StockTransfer[]>([])
  const [selectedTransfer, setSelectedTransfer] = useState<StockTransfer | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [confirmedBy, setConfirmedBy] = useState('')
  const [receivedQuantity, setReceivedQuantity] = useState('')
  const [incidentNotes, setIncidentNotes] = useState('')
  const [receiveScanInput, setReceiveScanInput] = useState('')
  const [scannedReceiveImeis, setScannedReceiveImeis] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState<'in_transit' | 'received' | 'incidents'>('in_transit')
  const [validationCodeRequest, setValidationCodeRequest] = useState<{
    resolve: (code: string | null) => void
  } | null>(null)

  useEffect(() => {
    if (!selectedTransfer) {
      setConfirmedBy('')
      setReceivedQuantity('')
      setIncidentNotes('')
      setReceiveScanInput('')
      setScannedReceiveImeis([])
      return
    }

    setConfirmedBy('')
    setReceivedQuantity(String(selectedTransfer.cantidad))
    setIncidentNotes('')
    setReceiveScanInput('')
    setScannedReceiveImeis([])
  }, [selectedTransfer])

  const loadTransfers = useCallback(async () => {
    setLoading(true)
    try {
      const service = inventoryServiceInstance
      const allTransfers = await service.listStockTransfers()
      
      // Filter by location if provided
      const filtered = currentLocationId 
        ? allTransfers.filter(t => t.from_location_id === currentLocationId || t.to_location_id === currentLocationId)
        : allTransfers
        
      setTransfers(filtered)
    } catch (error) {
      console.error('Error loading transfers:', error)
      toast.error('Error al cargar transferencias')
    } finally {
      setLoading(false)
    }
  }, [currentLocationId])

  useEffect(() => {
    if (open) {
      loadTransfers()
    }
  }, [open, loadTransfers])

  const getTransferValidationCode = async (): Promise<string | undefined | null> => {
    try {
      const config = await apiClient.getDailyCloseConfig()
      if (!config.configured) return undefined
    } catch (error) {
      console.error('Error checking transfer validation config:', error)
      toast.error('No se pudo verificar el código de validación')
      return null
    }

    return new Promise(resolve => {
      setValidationCodeRequest({ resolve })
    })
  }

  const handleConfirm = async (transfer: StockTransfer) => {
    if (!confirmedBy.trim()) {
      toast.error('Por favor ingresa tu nombre para confirmar')
      return
    }

    const parsedReceivedQuantity = receivedQuantity.trim() === ''
      ? transfer.cantidad
      : Number(receivedQuantity)

    if (!Number.isInteger(parsedReceivedQuantity) || parsedReceivedQuantity < 0 || parsedReceivedQuantity > transfer.cantidad) {
      toast.error(`La cantidad recibida debe estar entre 0 y ${transfer.cantidad}`)
      return
    }

    if (parsedReceivedQuantity < transfer.cantidad && !incidentNotes.trim()) {
      toast.error('Agrega notas de incidencia para una recepción parcial')
      return
    }

    const expectedImeis = transfer.imeis || []
    const scannedImeis = expectedImeis.length > 0 ? scannedReceiveImeis : undefined

    if (expectedImeis.length > 0 && scannedReceiveImeis.length !== parsedReceivedQuantity) {
      toast.error(`Debes escanear ${parsedReceivedQuantity} IMEIs recibidos en la ubicación de recepción`)
      return
    }

    const validationCode = await getTransferValidationCode()
    if (validationCode === null) return

    setActionLoading(true)
    try {
      const service = inventoryServiceInstance
      await service.confirmStockTransfer(
        transfer.id,
        confirmedBy,
        scannedImeis,
        validationCode,
        parsedReceivedQuantity,
        incidentNotes.trim() || undefined
      )
      toast.success('Transferencia confirmada exitosamente')
      setSelectedTransfer(null)
      setConfirmedBy('')
      setReceivedQuantity('')
      setIncidentNotes('')
      loadTransfers()
      onTransferUpdated?.()
    } catch (error) {
      console.error('Error confirming transfer:', error)
      toast.error('Error al confirmar transferencia')
    } finally {
      setActionLoading(false)
    }
  }

  const handleReject = async (transfer: StockTransfer) => {
    if (!confirmedBy.trim()) {
      toast.error('Por favor ingresa tu nombre para rechazar')
      return
    }

    setActionLoading(true)
    try {
      const service = inventoryServiceInstance
      await service.rejectStockTransfer(transfer.id, confirmedBy, 'Rechazada por usuario')
      toast.success('Transferencia rechazada')
      setSelectedTransfer(null)
      setConfirmedBy('')
      loadTransfers()
      onTransferUpdated?.()
    } catch (error) {
      console.error('Error rejecting transfer:', error)
      toast.error('Error al rechazar transferencia')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancel = async (transfer: StockTransfer) => {
    if (!window.confirm('¿Estás seguro de cancelar esta transferencia?')) return

    setActionLoading(true)
    try {
      const service = inventoryServiceInstance
      await service.cancelStockTransfer(transfer.id)
      toast.success('Transferencia cancelada')
      loadTransfers()
      onTransferUpdated?.()
    } catch (error) {
      console.error('Error canceling transfer:', error)
      toast.error('Error al cancelar transferencia')
    } finally {
      setActionLoading(false)
    }
  }

  const getLocationName = (locationId: number) => {
    return locations.find(l => l.id === locationId)?.nombre || `Ubicación ${locationId}`
  }

  const handleAddReceptionScan = () => {
    if (!selectedTransfer) return

    const scanned = receiveScanInput.trim()
    if (!scanned) return

    const expectedImeis = selectedTransfer.imeis || []

    if (expectedImeis.length === 0) {
      toast.error('Esta transferencia no requiere escaneo por IMEI')
      return
    }

    if (!expectedImeis.includes(scanned)) {
      toast.error('Este IMEI no pertenece a la transferencia esperada')
      return
    }

    if (scannedReceiveImeis.includes(scanned)) {
      toast.error('Este IMEI ya fue escaneado en recepción')
      return
    }

    setScannedReceiveImeis(prev => [...prev, scanned])
    setReceiveScanInput('')
  }

  const getStatusBadge = (estado: string) => {
    const variants: Record<string, { variant: any; icon: any; label: string }> = {
      pendiente: { variant: 'default', icon: Clock, label: 'Pendiente' },
      confirmada: { variant: 'default', icon: Check, label: 'Confirmada' },
      rechazada: { variant: 'destructive', icon: X, label: 'Rechazada' },
      cancelada: { variant: 'secondary', icon: X, label: 'Cancelada' }
    }

    const config = variants[estado] || variants.pendiente
    const Icon = config.icon

    return (
      <Badge variant={config.variant} className="gap-1">
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    )
  }

  const getOperationalStage = (transfer: StockTransfer) => {
    if (transfer.estado === 'confirmada') {
      return {
        label: 'Recibida',
        description: 'La ubicación de recepción confirmó y escaneó el ingreso completo.',
        className: 'border-green-200 bg-green-50 text-green-800'
      }
    }

    if (transfer.estado === 'pendiente') {
      return {
        label: 'Despachada / En tránsito',
        description: 'Salida validada en origen. Pendiente de escaneo y confirmación en recepción.',
        className: 'border-amber-200 bg-amber-50 text-amber-800'
      }
    }

    if (transfer.estado === 'rechazada') {
      return {
        label: 'Rechazada',
        description: 'La recepción no fue aceptada y la transferencia fue revertida.',
        className: 'border-red-200 bg-red-50 text-red-800'
      }
    }

    return {
      label: 'Cancelada',
      description: 'La transferencia fue anulada antes de completar la recepción.',
      className: 'border-slate-200 bg-slate-50 text-slate-700'
    }
  }

  const inTransitTransfers = transfers.filter(t => t.estado === 'pendiente')
  const receivedTransfers = transfers.filter(t => t.estado === 'confirmada')
  const incidentTransfers = transfers.filter(t => t.estado === 'rechazada' || t.estado === 'cancelada')

  const renderTransferCard = (transfer: StockTransfer) => {
    const canConfirm = transfer.estado === 'pendiente'  // Siempre permitir confirmar si está pendiente
    const canCancel = transfer.estado === 'pendiente'  // Siempre permitir cancelar si está pendiente
    const operationalStage = getOperationalStage(transfer)

    return (
      <div
        key={transfer.id}
        className="border rounded-lg p-4 space-y-3 hover:shadow-md transition-shadow"
      >
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1">
            <div className="flex items-center gap-2">
              <Package className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{transfer.product?.nombre || `Producto #${transfer.product_id}`}</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-3 w-3" />
              <span>Origen: {getLocationName(transfer.from_location_id)}</span>
              <ArrowRight className="h-3 w-3" />
              <span className="font-medium">Recepción: {getLocationName(transfer.to_location_id)}</span>
            </div>
          </div>
          {getStatusBadge(transfer.estado)}
        </div>

        <div className={`rounded-md border px-3 py-2 text-sm ${operationalStage.className}`}>
          <div className="font-medium">Estado operativo: {operationalStage.label}</div>
          <div className="text-xs mt-1 opacity-90">{operationalStage.description}</div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-muted-foreground">Cantidad:</span>
            <span className="ml-1 font-medium">{transfer.cantidad} unidades</span>
          </div>
          <div>
            <span className="text-muted-foreground">Creada:</span>
            <span className="ml-1">{format(new Date(transfer.created_at), 'dd/MM/yy HH:mm', { locale: es })}</span>
          </div>
        </div>

        {transfer.imeis && transfer.imeis.length > 0 && (
          <div className="text-sm">
            <span className="text-muted-foreground">IMEIs:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {transfer.imeis.map((imei, idx) => (
                <Badge key={idx} variant="outline" className="text-xs font-mono">
                  {imei}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {transfer.notas && (
          <div className="text-sm">
            <span className="text-muted-foreground">Notas:</span>
            <p className="mt-1 text-foreground">{transfer.notas}</p>
          </div>
        )}

        {transfer.estado === 'pendiente' && (
          <div className="flex items-center gap-2 pt-2 border-t">
            <AlertCircle className="h-4 w-4 text-orange-500" />
            <span className="text-sm text-orange-600 dark:text-orange-400">
              ⏳ Transferencia pendiente - validada en origen y esperando recepción
            </span>
          </div>
        )}

        {transfer.estado === 'rechazada' && transfer.rejection_reason && (
          <div className="text-sm text-red-600 dark:text-red-400">
            <span className="font-medium">Motivo:</span> {transfer.rejection_reason}
          </div>
        )}

        {transfer.estado === 'pendiente' && (canConfirm || canCancel) && (
          <div className="flex gap-2 pt-2 border-t">
            {canConfirm && (
              <Button
                size="sm"
                onClick={() => setSelectedTransfer(transfer)}
                disabled={actionLoading}
                className="flex-1"
              >
                <Check className="h-4 w-4 mr-1" />
                Confirmar recepción
              </Button>
            )}
            {canCancel && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCancel(transfer)}
                disabled={actionLoading}
                className="flex-1"
              >
                <X className="h-4 w-4 mr-1" />
                Cancelar
              </Button>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Transferencias de Stock</DialogTitle>
            <DialogDescription>
              Gestiona las transferencias entre ubicaciones. Las transferencias pendientes requieren confirmación del destino.
            </DialogDescription>
          </DialogHeader>

          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="mt-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="in_transit" className="gap-2">
                <Clock className="h-4 w-4" />
                En tránsito
                {inTransitTransfers.length > 0 && (
                  <Badge variant="secondary" className="ml-1">
                    {inTransitTransfers.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="received">
                Recibidas ({receivedTransfers.length})
              </TabsTrigger>
              <TabsTrigger value="incidents">
                Incidencias ({incidentTransfers.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="in_transit" className="mt-4">
              <ScrollArea className="h-[400px] pr-4">
                {loading ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : inTransitTransfers.length === 0 ? (
                  <div className="text-center py-12 space-y-3">
                    <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
                    <div>
                      <p className="font-medium text-foreground mb-1">No hay transferencias en tránsito</p>
                      <p className="text-sm text-muted-foreground">Las transferencias pendientes de recepción aparecerán aquí</p>
                    </div>
                    <div className="pt-2 text-xs text-muted-foreground">
                      <p>Para crear una transferencia:</p>
                      <p className="mt-1">Transferencias → Nueva transferencia rápida → Iniciar transferencia</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {inTransitTransfers.map(renderTransferCard)}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="received" className="mt-4">
              <ScrollArea className="h-[400px] pr-4">
                {loading ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : receivedTransfers.length === 0 ? (
                  <div className="text-center py-12 space-y-3">
                    <Package className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
                    <div>
                      <p className="font-medium text-foreground mb-1">No hay transferencias recibidas</p>
                      <p className="text-sm text-muted-foreground">Las transferencias confirmadas por recepción aparecerán aquí</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {receivedTransfers.map(renderTransferCard)}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="incidents" className="mt-4">
              <ScrollArea className="h-[400px] pr-4">
                {loading ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : incidentTransfers.length === 0 ? (
                  <div className="text-center py-12 space-y-3">
                    <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
                    <div>
                      <p className="font-medium text-foreground mb-1">No hay incidencias</p>
                      <p className="text-sm text-muted-foreground">Las transferencias rechazadas o canceladas aparecerán aquí</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {incidentTransfers.map(renderTransferCard)}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmation Dialog */}
      <Dialog open={!!selectedTransfer} onOpenChange={(open) => !open && setSelectedTransfer(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Confirmar Recepción</DialogTitle>
            <DialogDescription>
              Confirma la recepción en destino. Si el producto es serializado, debes volver a escanear cada unidad recibida.
            </DialogDescription>
          </DialogHeader>

          {selectedTransfer && (
            <div className="space-y-4 mt-4">
              <div className="p-3 border rounded-lg space-y-2">
                <div className="font-medium">{selectedTransfer.product?.nombre}</div>
                <div className="text-sm text-muted-foreground">
                  Ubicación origen: {getLocationName(selectedTransfer.from_location_id)}
                </div>
                <div className="text-sm text-muted-foreground">
                  Ubicación recepción: {getLocationName(selectedTransfer.to_location_id)}
                </div>
                <div className="text-sm">
                  Cantidad: <span className="font-medium">{selectedTransfer.cantidad} unidades</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmedBy">Tu nombre *</Label>
                <Input
                  id="confirmedBy"
                  value={confirmedBy}
                  onChange={(e) => setConfirmedBy(e.target.value)}
                  placeholder="Ingresa tu nombre"
                  disabled={actionLoading}
                />
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="receivedQuantity">Cantidad recibida *</Label>
                  <Input
                    id="receivedQuantity"
                    type="number"
                    min={0}
                    max={selectedTransfer.cantidad}
                    value={receivedQuantity}
                    onChange={(e) => setReceivedQuantity(e.target.value)}
                    disabled={actionLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Faltante</Label>
                  <div className="h-10 rounded-md border bg-muted/40 px-3 py-2 text-sm">
                    {Math.max(selectedTransfer.cantidad - (Number(receivedQuantity) || 0), 0)} unidades
                  </div>
                </div>
              </div>

              {Number(receivedQuantity) < selectedTransfer.cantidad && (
                <div className="space-y-2">
                  <Label htmlFor="incidentNotes">Notas de incidencia *</Label>
                  <Input
                    id="incidentNotes"
                    value={incidentNotes}
                    onChange={(e) => setIncidentNotes(e.target.value)}
                    placeholder="Ej: llegó una unidad menos, paquete abierto, equipo dañado"
                    disabled={actionLoading}
                  />
                </div>
              )}

              {(selectedTransfer.imeis?.length || 0) > 0 && (
                <div className="space-y-3 rounded-lg border border-dashed p-3 bg-muted/20">
                  <div>
                    <Label htmlFor="receiveScanInput">
                      Escanear IMEIs recibidos ({scannedReceiveImeis.length}/{Number(receivedQuantity) || 0})
                    </Label>
                    <div className="flex gap-2 mt-2">
                      <Input
                        id="receiveScanInput"
                        value={receiveScanInput}
                        onChange={(e) => setReceiveScanInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault()
                            handleAddReceptionScan()
                          }
                        }}
                        placeholder="Escanea o escribe IMEI recibido"
                        disabled={actionLoading}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        onClick={handleAddReceptionScan}
                        disabled={actionLoading || !receiveScanInput.trim()}
                      >
                        Registrar
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <span className="text-xs text-muted-foreground">IMEIs recibidos y verificados:</span>
                    <div className="flex flex-wrap gap-1">
                      {scannedReceiveImeis.map((imei) => (
                        <Badge
                          key={imei}
                          variant="default"
                          className="text-xs font-mono cursor-pointer"
                          onClick={() => setScannedReceiveImeis(prev => prev.filter(item => item !== imei))}
                        >
                          {imei}
                        </Badge>
                      ))}
                    </div>
                    {scannedReceiveImeis.length === 0 && (
                      <p className="text-xs text-muted-foreground">Aún no se ha escaneado ningún IMEI en recepción.</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <span className="text-xs text-muted-foreground">Pendientes por escanear:</span>
                    <div className="flex flex-wrap gap-1">
                      {(selectedTransfer.imeis || [])
                        .filter((imei) => !scannedReceiveImeis.includes(imei))
                        .map((imei) => (
                          <Badge key={imei} variant="outline" className="text-xs font-mono">
                            {imei}
                          </Badge>
                        ))}
                    </div>
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  onClick={() => handleConfirm(selectedTransfer)}
                  disabled={
                    actionLoading ||
                    !confirmedBy.trim() ||
                    !Number.isInteger(Number(receivedQuantity)) ||
                    Number(receivedQuantity) < 0 ||
                    Number(receivedQuantity) > selectedTransfer.cantidad ||
                    (Number(receivedQuantity) < selectedTransfer.cantidad && !incidentNotes.trim()) ||
                    ((selectedTransfer.imeis?.length || 0) > 0 && scannedReceiveImeis.length !== (Number(receivedQuantity) || 0))
                  }
                >
                  {actionLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  <Check className="h-4 w-4 mr-2" />
                  Confirmar recepción
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    if (window.confirm('¿Rechazar esta transferencia? El stock regresará al origen.')) {
                      handleReject(selectedTransfer)
                    }
                  }}
                  disabled={actionLoading || !confirmedBy.trim()}
                >
                  <X className="h-4 w-4 mr-2" />
                  Rechazar
                </Button>
              </div>

              {selectedTransfer.notas && (
                <div className="pt-3 border-t">
                  <span className="text-sm text-muted-foreground">Notas de la transferencia:</span>
                  <p className="text-sm mt-1">{selectedTransfer.notas}</p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => {
                setSelectedTransfer(null)
                setConfirmedBy('')
              }}
              disabled={actionLoading}
            >
              Cancelar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {validationCodeRequest && (
        <ValidationCodeDialog
          open={Boolean(validationCodeRequest)}
          title="Confirmar transferencia"
          description="Ingrese el código de validación para confirmar la recepción de inventario."
          confirmLabel="Confirmar"
          onCancel={() => {
            validationCodeRequest.resolve(null)
            setValidationCodeRequest(null)
          }}
          onConfirm={code => {
            validationCodeRequest.resolve(code)
            setValidationCodeRequest(null)
          }}
        />
      )}
    </>
  )
}
