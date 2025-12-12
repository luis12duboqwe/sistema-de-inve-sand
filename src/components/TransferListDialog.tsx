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
import { StockTransfer, Location } from '../lib/types'
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
  const [rejectionReason, setRejectionReason] = useState('')
  const [confirmedBy, setConfirmedBy] = useState('')
  const [activeTab, setActiveTab] = useState<'pending' | 'completed'>('pending')

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

  const handleConfirm = async (transfer: StockTransfer) => {
    if (!confirmedBy.trim()) {
      toast.error('Por favor ingresa tu nombre para confirmar')
      return
    }
    
    setActionLoading(true)
    try {
      const service = inventoryServiceInstance
      await service.confirmStockTransfer(transfer.id, confirmedBy)
      toast.success('Transferencia confirmada exitosamente')
      setSelectedTransfer(null)
      setConfirmedBy('')
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

  const pendingTransfers = transfers.filter(t => t.estado === 'pendiente')
  const completedTransfers = transfers.filter(t => t.estado !== 'pendiente')

  const renderTransferCard = (transfer: StockTransfer) => {
    const canConfirm = transfer.estado === 'pendiente'  // Siempre permitir confirmar si está pendiente
    const canCancel = transfer.estado === 'pendiente'  // Siempre permitir cancelar si está pendiente

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
              <span>{getLocationName(transfer.from_location_id)}</span>
              <ArrowRight className="h-3 w-3" />
              <span className="font-medium">{getLocationName(transfer.to_location_id)}</span>
            </div>
          </div>
          {getStatusBadge(transfer.estado)}
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
              ⏳ Transferencia pendiente - Stock reservado en origen
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
                Confirmar Recepción
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
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="pending" className="gap-2">
                <Clock className="h-4 w-4" />
                Pendientes
                {pendingTransfers.length > 0 && (
                  <Badge variant="secondary" className="ml-1">
                    {pendingTransfers.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="completed">
                Completadas ({completedTransfers.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="pending" className="mt-4">
              <ScrollArea className="h-[400px] pr-4">
                {loading ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : pendingTransfers.length === 0 ? (
                  <div className="text-center py-12 space-y-3">
                    <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
                    <div>
                      <p className="font-medium text-foreground mb-1">No hay transferencias pendientes</p>
                      <p className="text-sm text-muted-foreground">Las transferencias aparecerán aquí cuando se creen</p>
                    </div>
                    <div className="pt-2 text-xs text-muted-foreground">
                      <p>Para crear una transferencia:</p>
                      <p className="mt-1">Productos → Selecciona producto → Transferir</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {pendingTransfers.map(renderTransferCard)}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="completed" className="mt-4">
              <ScrollArea className="h-[400px] pr-4">
                {loading ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : completedTransfers.length === 0 ? (
                  <div className="text-center py-12 space-y-3">
                    <Package className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
                    <div>
                      <p className="font-medium text-foreground mb-1">No hay transferencias completadas</p>
                      <p className="text-sm text-muted-foreground">El historial de transferencias confirmadas/rechazadas aparecerá aquí</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {completedTransfers.map(renderTransferCard)}
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
              Confirma que has recibido el stock transferido. Esto moverá el stock a tu ubicación.
            </DialogDescription>
          </DialogHeader>

          {selectedTransfer && (
            <div className="space-y-4 mt-4">
              <div className="p-3 border rounded-lg space-y-2">
                <div className="font-medium">{selectedTransfer.product?.nombre}</div>
                <div className="text-sm text-muted-foreground">
                  De: {getLocationName(selectedTransfer.from_location_id)} → 
                  A: {getLocationName(selectedTransfer.to_location_id)}
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

              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  onClick={() => handleConfirm(selectedTransfer)}
                  disabled={actionLoading || !confirmedBy.trim()}
                >
                  {actionLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  <Check className="h-4 w-4 mr-2" />
                  Confirmar
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
                setRejectionReason('')
              }}
              disabled={actionLoading}
            >
              Cancelar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
