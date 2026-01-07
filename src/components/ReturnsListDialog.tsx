import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { Return } from '@/lib/types'
import { toast } from 'sonner'
import { ArrowCounterClockwise } from '@phosphor-icons/react'

interface ReturnsListDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ReturnsListDialog({ open, onOpenChange }: ReturnsListDialogProps) {
  const [returns, setReturns] = useState<Return[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open) {
      loadReturns()
    }
  }, [open])

  const loadReturns = async () => {
    setLoading(true)
    try {
      const data = await inventoryServiceInstance.getReturns()
      setReturns(data)
    } catch (error) {
      console.error('Error loading returns:', error)
      toast.error('Error al cargar devoluciones')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500'
      case 'pending': return 'bg-yellow-500'
      case 'rejected': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'refund': return 'Reembolso'
      case 'warranty_exchange': return 'Cambio por Garantía'
      case 'store_credit': return 'Crédito en Tienda'
      default: return action
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowCounterClockwise className="h-5 w-5" />
            Historial de Devoluciones
          </DialogTitle>
          <DialogDescription>
            Registro de todas las devoluciones y garantías procesadas.
          </DialogDescription>
        </DialogHeader>

        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Orden</TableHead>
                <TableHead>Razón</TableHead>
                <TableHead>Items</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    Cargando devoluciones...
                  </TableCell>
                </TableRow>
              ) : returns.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No hay devoluciones registradas
                  </TableCell>
                </TableRow>
              ) : (
                returns.map((ret) => (
                  <TableRow key={ret.id}>
                    <TableCell>#{ret.id}</TableCell>
                    <TableCell>
                      {format(new Date(ret.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                    </TableCell>
                    <TableCell>#{ret.order_id}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={ret.reason}>
                      {ret.reason || '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        {ret.items.map((item, idx) => (
                          <div key={idx} className="text-xs">
                            <span className="font-semibold">{item.quantity}x</span> Producto #{item.product_id}
                            <Badge variant="outline" className="ml-1 text-[10px]">
                              {getActionLabel(item.action)}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(ret.status)}>
                        {ret.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  )
}
