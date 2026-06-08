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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { apiClient } from '@/lib/apiClient'
import { ValidationCodeDialog } from '@/components/ValidationCodeDialog'
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
  const [receivedQuantity, setReceivedQuantity] = useState<Record<number, number>>({})
  const [receivedImeis, setReceivedImeis] = useState<Record<number, string>>({})
  const [incidentNotes, setIncidentNotes] = useState<Record<number, string>>({})
  const [processingId, setProcessingId] = useState<number | null>(null)
  const [validationCodeRequest, setValidationCodeRequest] = useState<{
    resolve: (code: string | null) => void
  } | null>(null)

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
    const quantityReceived = receivedQuantity[transfer.id] ?? transfer.cantidad
    if (!Number.isInteger(quantityReceived) || quantityReceived < 0 || quantityReceived > transfer.cantidad) {
      toast.error(`La cantidad recibida debe estar entre 0 y ${transfer.cantidad}`)
      return
    }

    const missingQuantity = transfer.cantidad - quantityReceived
    const notes = incidentNotes[transfer.id]?.trim()
    if (missingQuantity > 0 && !notes) {
      toast.error('Indica notas de incidencia para una recepción parcial')
      return
    }

    let scannedImeis: string[] | undefined
    
    if (transfer.imeis && transfer.imeis.length > 0) {
      const rawImeis = receivedImeis[transfer.id] ?? ''
      scannedImeis = rawImeis
        .split(/[\n,;\s]+/)
        .map(value => value.trim())
        .filter(Boolean)

      if (scannedImeis.length !== quantityReceived) {
        toast.error(`Debes registrar ${quantityReceived} IMEI(s) recibido(s) para esta transferencia`)
        return
      }

      const expectedSet = new Set(transfer.imeis)
      const invalidImeis = scannedImeis.filter(imei => !expectedSet.has(imei))
      if (invalidImeis.length > 0) {
        toast.error(`IMEIs fuera de esta transferencia: ${invalidImeis.join(', ')}`)
        return
      }
    } else {
        if (!confirm(`¿Confirmar la recepción de ${quantityReceived} de ${transfer.cantidad} unidad(es) de "${transfer.product_nombre}"?`)) {
            return
        }
    }

    const validationCode = await getTransferValidationCode()
    if (validationCode === null) return

    setProcessingId(transfer.id)
    try {
      await inventoryServiceInstance.confirmStockTransfer(
        transfer.id,
        'Sistema',
        scannedImeis,
        validationCode,
        quantityReceived,
        notes || undefined
      )

      toast.success(
        missingQuantity > 0
          ? `Recepción parcial registrada. ${quantityReceived} recibidas, ${missingQuantity} con incidencia.`
          : `Transferencia confirmada. ${quantityReceived} unidad(es) agregadas al inventario.`
      )

      setReceivedQuantity(prev => {
        const next = { ...prev }
        delete next[transfer.id]
        return next
      })
      setReceivedImeis(prev => {
        const next = { ...prev }
        delete next[transfer.id]
        return next
      })
      setIncidentNotes(prev => {
        const next = { ...prev }
        delete next[transfer.id]
        return next
      })
      
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
                            <strong>Origen físico:</strong> {transfer.from_location_name || `Ubicación ${transfer.from_location_id}`}
                          </div>
                          <div>
                            <strong>Destino:</strong> {transfer.to_location_name || `Ubicación ${transfer.to_location_id}`}
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
                          Al confirmar, se agregará la cantidad recibida al destino. Si recibes menos, el faltante queda registrado como incidencia y se libera en origen.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="space-y-2">
                          <Label htmlFor={`received-${transfer.id}`} className="text-xs">
                            Cantidad recibida
                          </Label>
                          <Input
                            id={`received-${transfer.id}`}
                            type="number"
                            min={0}
                            max={transfer.cantidad}
                            value={receivedQuantity[transfer.id] ?? transfer.cantidad}
                            onChange={(event) => setReceivedQuantity(prev => ({
                              ...prev,
                              [transfer.id]: Number(event.target.value)
                            }))}
                          />
                          <p className="text-xs text-muted-foreground">
                            Transferidas: {transfer.cantidad}
                          </p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor={`incident-${transfer.id}`} className="text-xs">
                            Incidencia de recepción parcial
                          </Label>
                          <Textarea
                            id={`incident-${transfer.id}`}
                            value={incidentNotes[transfer.id] || ''}
                            onChange={(event) => setIncidentNotes(prev => ({
                              ...prev,
                              [transfer.id]: event.target.value
                            }))}
                            placeholder="Ej: llegaron 2 de 3 unidades, queda una pendiente de revisión"
                            rows={2}
                            className="text-sm"
                          />
                        </div>
                      </div>

                      {transfer.imeis && transfer.imeis.length > 0 && (
                        <div className="space-y-2">
                          <Label htmlFor={`imeis-${transfer.id}`} className="text-xs">
                            IMEIs recibidos verificados
                          </Label>
                          <Textarea
                            id={`imeis-${transfer.id}`}
                            value={receivedImeis[transfer.id] ?? ''}
                            onChange={(event) => setReceivedImeis(prev => ({
                              ...prev,
                              [transfer.id]: event.target.value
                            }))}
                            placeholder="Escanea o pega un IMEI por línea"
                            rows={Math.min(Math.max(transfer.imeis.length, 2), 6)}
                            className="font-mono text-xs"
                          />
                          <p className="text-xs text-muted-foreground">
                            Debe coincidir con la cantidad recibida.
                          </p>
                        </div>
                      )}

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
    </Dialog>
  )
}
