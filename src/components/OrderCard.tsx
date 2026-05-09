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
import type { OrderWithItems, Order, SalesProfile, Location } from '@/lib/types'
import { format } from 'date-fns'
import { PencilSimple, User, FilePdf, Trash, Robot, MapPin, ArrowCounterClockwise } from '@phosphor-icons/react'
import { useState, useEffect } from 'react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { canEditOrderStatus, isFinalSaleStatus } from '@/lib/orderStatus'
import { ReturnDialog } from './ReturnDialog'

interface OrderCardProps {
  order: OrderWithItems
  onStatusChange?: (orderId: number, newStatus: Order['estado']) => void
  onEdit?: (order: OrderWithItems) => void
  onViewCustomerHistory?: (customerPhone: string) => void
  onExportPDF?: (order: OrderWithItems) => void
  onDelete?: (order: OrderWithItems) => void
}

export function OrderCard({ order, onStatusChange, onEdit, onViewCustomerHistory, onExportPDF, onDelete }: OrderCardProps) {
  const [salesProfile, setSalesProfile] = useState<SalesProfile | null>(null)
  const [sourceLocation, setSourceLocation] = useState<Location | null>(null)
  const [isReturnDialogOpen, setIsReturnDialogOpen] = useState(false)

  useEffect(() => {
    if (order.sales_profile_id) {
      loadSalesProfile(order.sales_profile_id)
    }
    if (order.source_location_id) {
      loadSourceLocation(order.source_location_id)
    }
  }, [order.sales_profile_id, order.source_location_id])

  const loadSalesProfile = async (id: number) => {
    try {
      const data = await inventoryServiceInstance.getSalesProfile(id)
      setSalesProfile(data)
    } catch (error) {
      console.error('Error loading sales profile:', error)
    }
  }

  const loadSourceLocation = async (id: number) => {
    try {
      const data = await inventoryServiceInstance.getLocation(id)
      setSourceLocation(data)
    } catch (error) {
      console.error('Error loading location:', error)
    }
  }

  const getStatusBadgeColor = (estado: Order['estado']) => {
    const colors: Record<Order['estado'], string> = {
      pendiente: 'bg-yellow-500 text-white',
      por_entregar: 'bg-blue-500 text-white',
      completada: 'bg-green-600 text-white',
      validada: 'bg-emerald-700 text-white',
      cancelada: 'bg-muted text-muted-foreground'
    }
    return colors[estado]
  }

  const getStatusText = (estado: Order['estado']) => {
    const text: Record<Order['estado'], string> = {
      pendiente: 'Pendiente',
      por_entregar: 'Por Entregar',
      completada: 'Completada',
      validada: 'Validada',
      cancelada: 'Cancelada'
    }
    return text[estado]
  }

  const getChannelText = (canal?: string) => {
    const text: Record<string, string> = {
      whatsapp: 'WhatsApp',
      facebook: 'Facebook',
      instagram: 'Instagram',
      tienda: 'Tienda Física'
    }
    return canal ? (text[canal] || canal) : 'N/A'
  }

  const getPaymentText = (metodo?: string) => {
    const text: Record<string, string> = {
      efectivo: 'Efectivo',
      transferencia: 'Transferencia',
      tarjeta: 'Tarjeta',
      financiamiento: 'Financiamiento'
    }
    return metodo ? (text[metodo] || metodo) : 'N/A'
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
          <div className="flex items-center gap-2">
            {onEdit && canEditOrderStatus(order.estado) && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onEdit(order)}
                title="Editar orden"
              >
                <PencilSimple size={18} />
              </Button>
            )}
            <Badge className={getStatusBadgeColor(order.estado)}>
              {getStatusText(order.estado)}
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-muted-foreground">Cliente:</span>
            <div className="flex items-center gap-2">
              <p className="font-medium">{order.customer_name || 'N/A'}</p>
              {onViewCustomerHistory && order.customer_phone && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onViewCustomerHistory(order.customer_phone)}
                  className="h-6 px-2"
                >
                  <User size={14} className="mr-1" />
                  Historial
                </Button>
              )}
            </div>
          </div>
          <div>
            <span className="text-muted-foreground">Teléfono:</span>
            <p className="font-medium">{order.customer_phone || 'N/A'}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Canal:</span>
            <p className="font-medium">{getChannelText(order.canal)}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Método de Pago:</span>
            <p className="font-medium">{getPaymentText(order.metodo_pago)}</p>
          </div>

          {order.metodo_pago === 'transferencia' && (order.transfer_bank_name || order.transfer_reference) && (
            <div className="md:col-span-2 rounded-md border border-blue-200 bg-blue-50 p-2 text-sm">
              <p>
                <span className="text-muted-foreground">Banco:</span>{' '}
                <span className="font-medium">{order.transfer_bank_name || 'N/A'}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Referencia:</span>{' '}
                <span className="font-mono font-medium">{order.transfer_reference || 'N/A'}</span>
              </p>
            </div>
          )}
          
          {/* V2.0: Sales Profile */}
          {salesProfile && (
            <div>
              <span className="text-muted-foreground">Perfil de Venta:</span>
              <div className="flex items-center gap-1.5 mt-0.5">
                <Robot size={14} className="text-primary" />
                <p className="font-medium">{salesProfile.name}</p>
                <Badge variant="outline" className="text-xs capitalize">
                  {salesProfile.tipo.replace('_', ' ')}
                </Badge>
              </div>
            </div>
          )}
          
          {/* V2.0: Source Location */}
          {sourceLocation && (
            <div>
              <span className="text-muted-foreground">{order.canal === 'tienda' ? 'Tienda reportada:' : 'Origen del Stock:'}</span>
              <div className="flex items-center gap-1.5 mt-0.5">
                <MapPin size={14} className="text-primary" />
                <p className="font-medium">{sourceLocation.nombre}</p>
                <Badge variant="outline" className="text-xs capitalize">
                  {sourceLocation.tipo}
                </Badge>
              </div>
            </div>
          )}
        </div>

        {order.notas && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-sm font-medium text-yellow-900 mb-1">Notas:</p>
            <p className="text-sm text-yellow-800">{order.notas}</p>
          </div>
        )}

        <div className="border-t pt-3">
          <h4 className="font-medium text-sm mb-2">Productos:</h4>
          <div className="space-y-2">
            {order.items.map(item => (
              <div
                key={item.id}
                className="flex items-center justify-between text-sm bg-muted/50 p-2 rounded"
              >
                <div className="flex-1">
                  <p className="font-medium">{item.product?.nombre || 'Producto desconocido'}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.cantidad}x {item.product?.moneda || 'HNL'}{' '}
                    {item.precio_unitario.toLocaleString()}
                  </p>
                </div>
                <p className="font-semibold">
                  {item.product?.moneda || 'HNL'}{' '}
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
          <div className="flex items-center gap-2">
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  console.log('🗑️ Click en botón eliminar orden, onDelete:', typeof onDelete)
                  onDelete(order)
                }}
                className="hover:text-destructive"
                disabled={!isFinalSaleStatus(order.estado) && order.estado !== 'cancelada'}
                title={
                  isFinalSaleStatus(order.estado) || order.estado === 'cancelada'
                    ? 'Eliminar orden'
                    : 'Solo se pueden eliminar órdenes completadas, validadas o canceladas'
                }
              >
                <Trash size={16} />
              </Button>
            )}
            {isFinalSaleStatus(order.estado) && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsReturnDialogOpen(true)}
                title="Procesar devolución"
              >
                <ArrowCounterClockwise size={16} className="mr-2" />
                Devolución
              </Button>
            )}
            {onExportPDF && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onExportPDF(order)}
              >
                <FilePdf size={16} className="mr-2" />
                PDF
              </Button>
            )}
            {onStatusChange && canEditOrderStatus(order.estado) && (
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
      </div>

      <ReturnDialog 
        open={isReturnDialogOpen} 
        onOpenChange={setIsReturnDialogOpen}
        order={order}
        onSuccess={() => setIsReturnDialogOpen(false)}
      />
    </Card>
  )
}
