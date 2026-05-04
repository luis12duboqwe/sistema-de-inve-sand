import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { format } from 'date-fns'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { IMEIDetail, IMEIHistory } from '@/lib/types'

interface IMEIHistoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  imei: string
}

export function IMEIHistoryDialog({ open, onOpenChange, imei }: IMEIHistoryDialogProps) {
  const [history, setHistory] = useState<IMEIHistory[]>([])
  const [detail, setDetail] = useState<IMEIDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true)
      try {
        const [historyData, detailData] = await Promise.all([
          inventoryServiceInstance.getIMEIHistory(imei),
          inventoryServiceInstance.getIMEIDetail(imei),
        ])
        setHistory(historyData)
        setDetail(detailData)
      } catch (error) {
        console.error('Error loading IMEI history:', error)
      } finally {
        setLoading(false)
      }
    }

    if (open && imei) {
      loadHistory()
    }
  }, [open, imei])

  const getEventBadge = (type: string) => {
    const styles: Record<string, string> = {
      ingreso: 'bg-green-500',
      purchase: 'bg-green-600',
      venta: 'bg-blue-500',
      transferencia: 'bg-yellow-500',
      devolucion: 'bg-red-500',
      retoma: 'bg-purple-500',
      liberacion: 'bg-slate-500',
      retoma_cancelada: 'bg-rose-500',
    }
    return <Badge className={styles[type] || 'bg-gray-500'}>{type}</Badge>
  }

  const formatDate = (value?: string) => {
    if (!value) return '-'
    try {
      return format(new Date(value), 'dd/MM/yyyy HH:mm')
    } catch {
      return value
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[96vw] max-w-6xl max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Historial de IMEI: {imei}</DialogTitle>
        </DialogHeader>
        
        <div className="mt-4">
          {detail && (
            <div className="mb-4 rounded-lg border p-4 space-y-3 bg-muted/20">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{detail.status_label || 'sin estado'}</Badge>
                {detail.product_name && <span className="font-semibold">{detail.product_name}</span>}
                {detail.product_sku && <span className="text-sm text-muted-foreground">SKU: {detail.product_sku}</span>}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-muted-foreground">Fecha de ingreso</div>
                  <div>{formatDate(detail.received_at || detail.created_at)}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Proveedor</div>
                  <div>{detail.supplier_name || '-'}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Ubicación actual</div>
                  <div>{detail.location_name || '-'}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Tipo de ingreso</div>
                  <div>{detail.acquisition_type || '-'}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Fecha de venta</div>
                  <div>{formatDate(detail.sold_at)}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Cliente</div>
                  <div>{detail.customer_name || '-'}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Teléfono cliente</div>
                  <div>{detail.customer_phone || '-'}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Vence garantía</div>
                  <div>{formatDate(detail.warranty_expires_at)}</div>
                </div>
              </div>

              {detail.received_notes && (
                <div>
                  <div className="text-muted-foreground text-sm">Notas de ingreso</div>
                  <div className="text-sm">{detail.received_notes}</div>
                </div>
              )}
            </div>
          )}

          {loading ? (
            <div className="text-center py-4">Cargando historial...</div>
          ) : history.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">
              No hay historial registrado para este IMEI.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Evento</TableHead>
                  <TableHead>Ubicación</TableHead>
                  <TableHead>Referencia</TableHead>
                  <TableHead>Usuario</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {formatDate(item.created_at)}
                    </TableCell>
                    <TableCell>{getEventBadge(item.event_type)}</TableCell>
                    <TableCell>{item.location_name || '-'}</TableCell>
                    <TableCell>
                      {item.reference_type} #{item.reference_id}
                      {item.supplier_name && (
                        <div className="text-xs text-muted-foreground mt-1">
                          Proveedor: {item.supplier_name}
                        </div>
                      )}
                      {item.notes && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {item.notes}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>{item.created_by || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
