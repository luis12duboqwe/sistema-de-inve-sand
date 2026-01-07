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
import type { IMEIHistory } from '@/lib/types'

interface IMEIHistoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  imei: string
}

export function IMEIHistoryDialog({ open, onOpenChange, imei }: IMEIHistoryDialogProps) {
  const [history, setHistory] = useState<IMEIHistory[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true)
      try {
        const data = await inventoryServiceInstance.getIMEIHistory(imei)
        setHistory(data)
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
      venta: 'bg-blue-500',
      transferencia: 'bg-yellow-500',
      devolucion: 'bg-red-500',
      retoma: 'bg-purple-500'
    }
    return <Badge className={styles[type] || 'bg-gray-500'}>{type}</Badge>
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Historial de IMEI: {imei}</DialogTitle>
        </DialogHeader>
        
        <div className="mt-4">
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
                      {format(new Date(item.created_at), 'dd/MM/yyyy HH:mm')}
                    </TableCell>
                    <TableCell>{getEventBadge(item.event_type)}</TableCell>
                    <TableCell>{item.location_name || '-'}</TableCell>
                    <TableCell>
                      {item.reference_type} #{item.reference_id}
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
