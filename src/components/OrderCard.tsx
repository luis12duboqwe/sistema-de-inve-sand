import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import type { OrderWithItems, Order } from '@/lib/types'
import { format } from 'date-fns'

interface OrderCardProps {
  order: OrderWithItems
  onStatusChange?: (orderId: number, newStatus: Order['estado']) => void
}

export function OrderCard({ order, onStatusChange }: OrderCardProps) {
  const getStatusBadgeColor = (estado: Order['estado']) => {
    const colors: Record<Order['estado'], string> = {
      pendiente: 'bg-yellow-500 text-white',
      por_entregar: 'bg-blue-500 text-white',
      completada: 'bg-green-600 text-white',
      cancelada: 'bg-muted text-muted-foreground'
    }
    return colors[estado]
  }

  const getStatusText = (estado: Order['estado']) => {
    const text: Record<Order['estado'], string> = {
      pendiente: 'Pendiente',
      por_entregar: 'Por Entregar',
      completada: 'Completada',
      cancelada: 'Cancelada'
    }
    return text[estado]
  }

  const getChannelText = (canal: string) => {
    const text: Record<string, string> = {
      whatsapp: 'WhatsApp',
      facebook: 'Facebook',
      instagram: 'Instagram'
    }
    return text[canal] || canal
  }

  const getPaymentText = (metodo: string) => {
    const text: Record<string, string> = {
      efectivo: 'Efectivo',
      transferencia: 'Transferencia',
      tarjeta: 'Tarjeta',
      financiamiento: 'Financiamiento'
    }
    return text[metodo] || metodo
  }

  return (
    <Card className="p-6">
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="font-semibold text-lg">Orden #{order.id}</h3>
            <p className="text-sm text-muted-foreground">
              {format(new Date(order.created_at), 'dd/MM/yyyy HH:mm')}
            </p>
          </div>
          <Badge className={getStatusBadgeColor(order.estado)}>
            {getStatusText(order.estado)}
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-muted-foreground">Cliente:</span>
            <p className="font-medium">{order.customer_name}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Teléfono:</span>
            <p className="font-medium">{order.customer_phone}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Canal:</span>
            <p className="font-medium">{getChannelText(order.canal)}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Método de Pago:</span>
            <p className="font-medium">{getPaymentText(order.metodo_pago)}</p>
          </div>
        </div>

        <div className="border-t pt-3">
          <h4 className="font-medium text-sm mb-2">Productos:</h4>
          <div className="space-y-2">
            {order.items.map(item => (
              <div
                key={item.id}
                className="flex items-center justify-between text-sm bg-muted/50 p-2 rounded"
              >
                <div className="flex-1">
                  <p className="font-medium">{item.product.nombre}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.cantidad}x {item.product.moneda}{' '}
                    {item.precio_unitario.toLocaleString()}
                  </p>
                </div>
                <p className="font-semibold">
                  {item.product.moneda}{' '}
                  {(item.cantidad * item.precio_unitario).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t">
          <div>
            <p className="text-sm text-muted-foreground">Total</p>
            <p className="text-2xl font-bold text-primary">
              HNL {order.total.toLocaleString()}
            </p>
          </div>
          {onStatusChange && order.estado !== 'completada' && order.estado !== 'cancelada' && (
            <Select
              value={order.estado}
              onValueChange={(value) => onStatusChange(order.id, value as Order['estado'])}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pendiente">Pendiente</SelectItem>
                <SelectItem value="por_entregar">Por Entregar</SelectItem>
                <SelectItem value="completada">Completada</SelectItem>
                <SelectItem value="cancelada">Cancelada</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>
      </div>
    </Card>
  )
}
