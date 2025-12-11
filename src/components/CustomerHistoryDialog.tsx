import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { User, Phone, ShoppingCart, CurrencyDollar, Calendar } from '@phosphor-icons/react'
import { format } from 'date-fns'
import type { OrderWithItems, Profile } from '@/lib/types'
import { getCustomerHistory } from '@/lib/reportUtils'

interface CustomerHistoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  customerPhone: string
  orders: OrderWithItems[]
  profile: Profile
  onViewOrder: (order: OrderWithItems) => void
}

export function CustomerHistoryDialog({
  open,
  onOpenChange,
  customerPhone,
  orders,
  profile,
  onViewOrder
}: CustomerHistoryDialogProps) {
  const history = getCustomerHistory(orders, customerPhone)
  const currency = profile.settings?.currency || 'Lps'
  const currencySymbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : 'L'

  const formatCurrency = (value: number) => {
    return `${currencySymbol}${value.toLocaleString('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`
  }

  const getStatusVariant = (status: string): 'default' | 'secondary' | 'outline' | 'destructive' => {
    switch (status) {
      case 'completada':
        return 'default'
      case 'por_entregar':
        return 'secondary'
      case 'pendiente':
        return 'outline'
      case 'cancelada':
        return 'destructive'
      default:
        return 'outline'
    }
  }

  const getStatusLabel = (status: string): string => {
    const labels: Record<string, string> = {
      pendiente: 'Pendiente',
      por_entregar: 'Por Entregar',
      completada: 'Completada',
      cancelada: 'Cancelada'
    }
    return labels[status] || status
  }

  if (history.orders.length === 0) {
    return null
  }

  const customerName = history.orders[0]?.customer_name || 'Cliente'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User size={24} />
            Historial del Cliente
          </DialogTitle>
          <DialogDescription>
            Revisa las órdenes anteriores de {customerName} ({customerPhone})
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          <Card className="p-6 bg-accent/20">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-lg font-semibold">
                <User size={20} />
                {customerName}
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <Phone size={16} />
                {customerPhone}
              </div>
            </div>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <ShoppingCart size={20} className="text-primary" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Órdenes</p>
                  <p className="text-xl font-bold">{history.orderCount}</p>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/10 rounded-lg">
                  <CurrencyDollar size={20} className="text-green-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Gastado</p>
                  <p className="text-xl font-bold">{formatCurrency(history.totalSpent)}</p>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent/10 rounded-lg">
                  <CurrencyDollar size={20} className="text-accent" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Promedio</p>
                  <p className="text-xl font-bold">{formatCurrency(history.averageOrderValue)}</p>
                </div>
              </div>
            </Card>
          </div>

          <div>
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Calendar size={20} />
              Historial de Órdenes
            </h3>
            <div className="space-y-3">
              {history.orders.map(order => (
                <Card key={order.id} className="p-4 hover:bg-accent/50 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-semibold">Orden #{order.id}</span>
                        <Badge variant={getStatusVariant(order.estado)}>
                          {getStatusLabel(order.estado)}
                        </Badge>
                      </div>
                      
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p>{format(new Date(order.created_at), 'dd/MM/yyyy HH:mm')}</p>
                        <p>{order.items.length} producto{order.items.length !== 1 ? 's' : ''}</p>
                        {order.notas && (
                          <p className="italic">Nota: {order.notas}</p>
                        )}
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-lg font-bold mb-2">{formatCurrency(order.total)}</p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          onViewOrder(order)
                          onOpenChange(false)
                        }}
                      >
                        Ver Detalles
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
