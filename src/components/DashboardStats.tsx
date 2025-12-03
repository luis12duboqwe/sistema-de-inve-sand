import { Card } from '@/components/ui/card'
import type { ProductWithStock, OrderWithItems } from '@/lib/types'
import { Package, ShoppingCart, ChartLineUp, WarningCircle, TrendUp, Money } from '@phosphor-icons/react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { format, subDays, startOfDay, isSameDay } from 'date-fns'
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

  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const date = subDays(new Date(), 6 - i)
    const dayOrders = orders.filter(o => {
      const orderDate = new Date(o.created_at)
      return isSameDay(orderDate, date)
    })
    return {
      date: format(date, 'dd/MM'),
      ordenes: dayOrders.length,
      ventas: dayOrders.filter(o => o.estado === 'completada').reduce((sum, o) => sum + o.total, 0)
    }
  })

  const ordersByStatus = [
    { name: 'Pendiente', value: pendingOrders, color: '#f59e0b' },
    { name: 'Por Entregar', value: readyToDeliverOrders, color: '#3b82f6' },
    { name: 'Completada', value: completedOrders, color: '#10b981' },
    { name: 'Cancelada', value: orders.filter(o => o.estado === 'cancelada').length, color: '#ef4444' },
  ].filter(s => s.value > 0)

  const productSales = orders
    .filter(o => o.estado === 'completada')
    .flatMap(o => o.items)
    .filter(item => item.product?.nombre)
    .reduce((acc, item) => {
      const key = item.product!.nombre
      if (!acc[key]) {
        acc[key] = { nombre: key, cantidad: 0, ingresos: 0 }
      }
      acc[key].cantidad += item.cantidad
      acc[key].ingresos += item.cantidad * item.precio_unitario
      return acc
    }, {} as Record<string, { nombre: string; cantidad: number; ingresos: number }>)

  const topProducts = Object.values(productSales)
    .sort((a, b) => b.ingresos - a.ingresos)
    .slice(0, 5)

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
      subtitle: `${completedOrders} completadas`,
      icon: ShoppingCart,
      color: 'text-blue-600',
      bgColor: 'bg-blue-600/10',
    },
    {
      title: 'Ingresos Totales',
      value: `L ${totalRevenue.toFixed(2)}`,
      subtitle: 'Ventas completadas',
      icon: Money,
      color: 'text-green-600',
      bgColor: 'bg-green-600/10',
    },
    {
      title: 'Valor del Inventario',
      value: `L ${inventoryValue.toFixed(2)}`,
      subtitle: 'Total en stock',
      icon: ChartLineUp,
      color: 'text-accent',
      bgColor: 'bg-accent/10',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1, duration: 0.3 }}
          >
            <Card className="p-6 hover:shadow-lg transition-shadow">
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
          </motion.div>
        ))}
      </div>

      {(lowStockProducts > 0 || outOfStockProducts > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.3 }}
        >
          <Card className="p-6 border-yellow-500/50 bg-yellow-50/50">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-lg bg-yellow-500/10">
                <WarningCircle size={24} className="text-yellow-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-1 text-yellow-900">Alertas de Inventario</h3>
                <p className="text-sm text-yellow-800">
                  {lowStockProducts > 0 && `${lowStockProducts} producto${lowStockProducts > 1 ? 's' : ''} con stock bajo`}
                  {lowStockProducts > 0 && outOfStockProducts > 0 && ' • '}
                  {outOfStockProducts > 0 && `${outOfStockProducts} producto${outOfStockProducts > 1 ? 's' : ''} agotado${outOfStockProducts > 1 ? 's' : ''}`}
                </p>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.3 }}
        >
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Ventas Últimos 7 Días</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={last7Days}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.90 0.005 250)" />
                <XAxis dataKey="date" stroke="oklch(0.50 0.01 250)" fontSize={12} />
                <YAxis stroke="oklch(0.50 0.01 250)" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'oklch(1 0 0)', 
                    border: '1px solid oklch(0.90 0.005 250)',
                    borderRadius: '0.5rem'
                  }}
                  formatter={(value: number, name: string) => {
                    if (name === 'ventas') return [`L ${value.toFixed(2)}`, 'Ventas']
                    return [value, 'Órdenes']
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="ventas" 
                  stroke="oklch(0.45 0.12 250)" 
                  strokeWidth={2}
                  dot={{ fill: 'oklch(0.45 0.12 250)', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.3 }}
        >
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Estado de Órdenes</h3>
            {ordersByStatus.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={ordersByStatus}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {ordersByStatus.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                No hay órdenes registradas
              </div>
            )}
          </Card>
        </motion.div>
      </div>

      {topProducts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.3 }}
        >
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Top 5 Productos Más Vendidos</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topProducts}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.90 0.005 250)" />
                <XAxis 
                  dataKey="nombre" 
                  stroke="oklch(0.50 0.01 250)" 
                  fontSize={12}
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis stroke="oklch(0.50 0.01 250)" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'oklch(1 0 0)', 
                    border: '1px solid oklch(0.90 0.005 250)',
                    borderRadius: '0.5rem'
                  }}
                  formatter={(value: number, name: string) => {
                    if (name === 'ingresos') return [`L ${value.toFixed(2)}`, 'Ingresos']
                    return [value, 'Cantidad']
                  }}
                />
                <Bar dataKey="ingresos" fill="oklch(0.60 0.15 195)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </motion.div>
      )}
    </div>
  )
}



























