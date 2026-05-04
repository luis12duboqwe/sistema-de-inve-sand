import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { Location, StockTransfer } from '@/lib/types'
import { 
  ArrowRightLeft, 
  Check, 
  X, 
  Clock, 
  Package,
  AlertCircle 
} from 'lucide-react'

interface PendingTransfersDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  locations: Location[]
  onTransferUpdate: () => void
}

export function PendingTransfersDialog({
  open,
  onOpenChange,
  locations,
  onTransferUpdate
}: PendingTransfersDialogProps) {
  const [transfers, setTransfers] = useState<StockTransfer[]>([])
  const [loading, setLoading] = useState(false)
  const [rejectionReason, setRejectionReason] = useState<Record<number, string>>({})
  const [processingId, setProcessingId] = useState<number | null>(null)

  const loadPendingTransfers = async () => {
    setLoading(true)
    try {
      const allTransfers = await inventoryServiceInstance.listStockTransfers({ estado: 'pendiente' })
      const myLocationIds = locations.map(l => l.id)
      const pending = allTransfers.filter(t => myLocationIds.includes(t.to_location_id))
      setTransfers(pending)
    } catch (error) {
      console.error('Error loading transfers:', error)
      toast.error('Error al cargar transferencias pendientes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && locations.length > 0) {
      loadPendingTransfers()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, locations])

  const handleConfirm = async (transfer: StockTransfer) => {
    // V2.0: Check for serialized items
    let scannedImeis: string[] | undefined = undefined;
    
    if (transfer.imeis && transfer.imeis.length > 0) {
        // For now, we'll just auto-confirm with the expected IMEIs if the user agrees.
        // In a real app, we would open a scanning dialog.
        const message = `Esta transferencia incluye ${transfer.imeis.length} productos serializados (IMEIs).\n\n` +
                        `IMEIs esperados:\n${transfer.imeis.join('\\n')}\n\n` +
                        `¿Confirma que ha verificado físicamente estos seriales?`;
        
        if (!confirm(message)) {
            return;
        }
        scannedImeis = transfer.imeis;
    } else {
        if (!confirm(`¿Confirmar la recepción de ${transfer.cantidad} unidad(es) de "${transfer.product_nombre}"?`)) {
            return
        }
    }

    setProcessingId(transfer.id)
    try {
      await inventoryServiceInstance.confirmStockTransfer(transfer.id, 'Sistema', scannedImeis)

      toast.success(
        `Transferencia confirmada. ${transfer.cantidad} unidad(es) agregadas al inventario.`
      )
      
      await loadPendingTransfers()
      onTransferUpdate()
    } catch (error) {
      console.error('Error confirming transfer:', error)
      toast.error(error instanceof Error ? error.message : 'Error al confirmar transferencia')
    } finally {
      setProcessingId(null)
    }
  }

  const handleReject = async (transfer: StockTransfer) => {
    const reason = rejectionReason[transfer.id]
    if (!reason || reason.trim() === '') {
      toast.error('Por favor indica la razón del rechazo')
      return
    }

    if (!confirm(`¿Rechazar la transferencia de "${transfer.product_nombre}"?`)) {
      return
    }

    setProcessingId(transfer.id)
    try {
      await inventoryServiceInstance.rejectStockTransfer(transfer.id, 'Sistema', reason.trim())

      toast.success('Transferencia rechazada')
      
      setRejectionReason(prev => {
        const next = { ...prev }
        delete next[transfer.id]
        return next
      })
      
      await loadPendingTransfers()
      onTransferUpdate()
    } catch (error) {
      console.error('Error rejecting transfer:', error)
      toast.error(error instanceof Error ? error.message : 'Error al rechazar transferencia')
    } finally {
      setProcessingId(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-HN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Transferencias Pendientes
          </DialogTitle>
          <DialogDescription>
            Revisa y confirma las transferencias entrantes a este perfil
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {loading ? (
            <p className="text-muted-foreground text-center py-8">
              Cargando transferencias...
            </p>
          ) : transfers.length === 0 ? (
            <Card className="p-8 text-center">
              <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-2">
                No hay transferencias pendientes
              </p>
              <p className="text-sm text-muted-foreground">
                Las transferencias entrantes aparecerán aquí para su confirmación
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {transfers.map(transfer => (
                <Card key={transfer.id} className="p-4">
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <ArrowRightLeft className="h-4 w-4 text-primary" />
                          <h4 className="font-medium">{transfer.product_nombre}</h4>
                          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                            Pendiente
                          </Badge>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                          <div>
                            <strong>SKU:</strong> {transfer.product_sku}
                          </div>
                          <div>
                            <strong>Cantidad:</strong> {transfer.cantidad} unidad(es)
                          </div>
                          <div>
                            <strong>Desde:</strong> {transfer.from_profile_name}
                          </div>
                          <div>
                            <strong>Solicitada:</strong> {formatDate(transfer.created_at)}
                          </div>
                        </div>
                        {transfer.notas && (
                          <div className="mt-2 p-2 bg-muted rounded text-sm">
                            <strong>Notas:</strong> {transfer.notas}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="space-y-3 border-t pt-3">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                        <p className="text-xs text-muted-foreground">
                          Al confirmar, se agregarán {transfer.cantidad} unidad(es) a tu inventario.
                          Al rechazar, el stock permanecerá en el perfil de origen.
                        </p>
                      </div>

                      <div className="flex gap-2">
                        <Button
                          onClick={() => handleConfirm(transfer)}
                          disabled={processingId === transfer.id}
                          className="flex-1"
                        >
                          <Check className="h-4 w-4 mr-2" />
                          Confirmar Recepción
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            if (!rejectionReason[transfer.id]) {
                              toast.error('Por favor indica la razón del rechazo')
                            } else {
                              handleReject(transfer)
                            }
                          }}
                          disabled={processingId === transfer.id}
                        >
                          <X className="h-4 w-4 mr-2" />
                          Rechazar
                        </Button>
                      </div>

                      {/* Rejection reason input */}
                      <div className="space-y-2">
                        <Label htmlFor={`reason-${transfer.id}`} className="text-xs">
                          Razón del rechazo (requerido para rechazar):
                        </Label>
                        <Textarea
                          id={`reason-${transfer.id}`}
                          value={rejectionReason[transfer.id] || ''}
                          onChange={(e) => setRejectionReason(prev => ({
                            ...prev,
                            [transfer.id]: e.target.value
                          }))}
                          placeholder="Ej: Stock no recibido, producto equivocado, etc."
                          rows={2}
                          className="text-sm"
                        />
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
