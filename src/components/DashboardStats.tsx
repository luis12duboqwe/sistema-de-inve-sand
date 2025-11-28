import { Card } from '@/components/ui/card'
import { Package, ShoppingCart, TrendUp, WarningCircle } from '@phosphor-icons/react'
import type { ProductWithStock, OrderWithItems } from '@/lib/types'
import { motion } from 'framer-motion'

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
      title: 'Valor en Inventario',
      value: `L ${inventoryValue.toLocaleString('es-HN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      subtitle: `${products.reduce((sum, p) => sum + p.stock_disponible, 0)} unidades`,
      icon: TrendUp,
      color: 'text-green-600',
      bgColor: 'bg-green-600/10',
    },
    {
      title: 'Stock Bajo/Agotado',
      value: lowStockProducts + outOfStockProducts,
      subtitle: `${outOfStockProducts} sin stock`,
      icon: WarningCircle,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-600/10',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {stats.map((stat, index) => (
        <motion.div
          key={stat.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1, duration: 0.3 }}
        >
          <Card className="p-6 hover:shadow-lg transition-shadow duration-300">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm text-muted-foreground mb-1">{stat.title}</p>
                <h3 className="text-2xl font-semibold mb-1">{stat.value}</h3>
                <p className="text-xs text-muted-foreground">{stat.subtitle}</p>
              </div>
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon size={24} className={stat.color} weight="duotone" />
              </div>
            </div>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}
