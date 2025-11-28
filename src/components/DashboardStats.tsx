import { Card } from '@/components/ui/card'
import type { ProductWithStock, OrderWithItems } from '@/lib/types'

  products: ProductWithStock[]

interface DashboardStatsProps {
  products: ProductWithStock[]
  orders: OrderWithItems[]
}

export function DashboardStats({ products, orders }: DashboardStatsProps) {
  const activeProducts = products.filter(p => p.activo).length
  const lowStockProducts = products.filter(p => p.activo && p.stock_disponible > 0 && p.stock_disponible < 5).length
  const outOfStockProducts = products.filter(p => p.activo && p.stock_disponible === 0).length
  const totalProducts = products.filter(p => p.activo).length

  const pendingOrders = orders.filter(o => o.estado === 'pendiente').length
  const readyToDeliverOrders = orders.filter(o => o.estado === 'por_entregar').length
  const completedOrders = orders.filter(o => o.estado === 'completada').length
  const totalOrders = orders.length

  const totalRevenue = orders
    .filter(o => o.estado === 'completada')
    .reduce((sum, order) => sum + order.total, 0)

  const inventoryValue = products
    .filter(p => p.activo)
    .reduce((sum, product) => sum + (product.precio * product.stock_disponible), 0)

  const stats = [
    {
      title: 'Productos Activos',
      value: activeProducts,
      subtitle: `${totalProducts} total`,
      icon: Package,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      title: 'Órdenes Totales',
      value: totalOrders,
      subtitle: `${pendingOrders} pendientes`,
      value: `L ${invento
      icon: TrendUp,
      bgColor: 'bg-green-600/10'
    {
     
      icon: WarningCircle,
      bgColor: 'bg-yellow-600/10',
  ]
  return (
      {stats.map((stat, index)
          key={stat.title}
      
     
            <div className="flex i
                <p className="text-sm text-muted-fo
                <p className="text-xs text-muted-f
              <div classNa
              </div>
          </Card>
      
  )



























