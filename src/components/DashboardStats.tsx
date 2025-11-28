import { Card } from '@/components/ui/card'
import type { ProductWithStock, OrderWithItems } from '@/lib/types'
import { Package, ShoppingCart, ChartLineUp, WarningCircle } from '@phosphor-icons/react'

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
      icon: ShoppingCart,
      color: 'text-blue-600',
      bgColor: 'bg-blue-600/10',
    },
    {
      title: 'Valor del Inventario',
      value: `L ${inventoryValue.toFixed(2)}`,
      subtitle: 'Total en stock',
      icon: ChartLineUp,
      color: 'text-green-600',
      bgColor: 'bg-green-600/10',
    },
    {
      title: 'Stock Bajo',
      value: lowStockProducts,
      subtitle: `${outOfStockProducts} agotados`,
      icon: WarningCircle,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-600/10',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, index) => (
        <Card key={stat.title} className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm text-muted-foreground mb-1">{stat.title}</p>
              <p className="text-2xl font-semibold mb-1">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.subtitle}</p>
            </div>
            <div className={`p-3 rounded-lg ${stat.bgColor}`}>
              <stat.icon size={24} className={stat.color} />
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}



























