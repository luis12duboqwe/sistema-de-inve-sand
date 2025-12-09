import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { ProductWithStock, OrderWithItems, Location, SalesProfile } from '@/lib/types'
import { Package, ShoppingCart, ChartLineUp, WarningCircle, Money, TrendDown, MapPin, Robot } from '@phosphor-icons/react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format, subDays, isSameDay } from 'date-fns'
import { motion } from 'framer-motion'
import { useMemo, useState, useEffect, useCallback, memo } from 'react'
import { apiClient } from '@/lib/apiClient'

interface DashboardStatsProps {
  products: ProductWithStock[]
  orders: OrderWithItems[]
  onViewLowStockReport?: () => void
}

function DashboardStatsComponent({ products, orders, onViewLowStockReport }: DashboardStatsProps) {
  const [locations, setLocations] = useState<Location[]>([])
  const [salesProfiles, setSalesProfiles] = useState<SalesProfile[]>([])
  const [apiError, setApiError] = useState<string | null>(null)

  const loadLocations = useCallback(async () => {
    try {
      const data = await apiClient.listLocations()
      setLocations(data)
      setApiError(null)
    } catch (error) {
      console.error('Error loading locations:', error)
      // Si hay error, simplemente no mostramos datos de ubicaciones
      setLocations([])
    }
  }, [])

  const loadSalesProfiles = useCallback(async () => {
    try {
      const data = await apiClient.listSalesProfiles()
      setSalesProfiles(data)
      setApiError(null)
    } catch (error) {
      console.error('Error loading sales profiles:', error)
      // Si hay error, simplemente no mostramos datos de perfiles
      setSalesProfiles([])
    }
  }, [])

  useEffect(() => {
    loadLocations()
    loadSalesProfiles()
  }, [loadLocations, loadSalesProfiles])

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
    .reduce((sum, order) => sum + Number(order.total), 0)

  const inventoryValue = products
    .filter(p => p.activo)
    .reduce((sum, product) => sum + (Number(product.precio) * product.stock_disponible), 0)

  const last7Days = useMemo(() => Array.from({ length: 7 }, (_, i) => {
    const date = subDays(new Date(), 6 - i)
    const dayOrders = orders.filter(o => {
      const orderDate = new Date(o.created_at)
      return isSameDay(orderDate, date)
    })
    return {
      date: format(date, 'dd/MM'),
      ordenes: dayOrders.length,
      ventas: dayOrders.filter(o => o.estado === 'completada').reduce((sum, o) => sum + Number(o.total), 0)
    }
  }), [orders])

  const ordersByStatus = useMemo(() => [
    { name: 'Pendiente', value: pendingOrders, color: '#f59e0b' },
    { name: 'Por Entregar', value: readyToDeliverOrders, color: '#3b82f6' },
    { name: 'Completada', value: completedOrders, color: '#10b981' },
    { name: 'Cancelada', value: orders.filter(o => o.estado === 'cancelada').length, color: '#ef4444' },
  ].filter(s => s.value > 0), [pendingOrders, readyToDeliverOrders, completedOrders, orders])

  const topProducts = useMemo(() => {
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
        acc[key].ingresos += item.cantidad * Number(item.precio_unitario)
        return acc
      }, {} as Record<string, { nombre: string; cantidad: number; ingresos: number }>)

    return Object.values(productSales)
      .sort((a, b) => b.ingresos - a.ingresos)
      .slice(0, 5)
  }, [orders])

  // V2.0: Stats by location
  const statsByLocation = useMemo(() => {
    return locations.map(location => {
      const locationOrders = orders.filter(o => o.source_location_id === location.id)
      const completedLocationOrders = locationOrders.filter(o => o.estado === 'completada')
      const revenue = completedLocationOrders.reduce((sum, o) => sum + Number(o.total), 0)
      
      return {
        nombre: location.nombre,
        tipo: location.tipo,
        ordenes: locationOrders.length,
        completadas: completedLocationOrders.length,
        ingresos: revenue
      }
    }).filter(s => s.ordenes > 0)
  }, [locations, orders])

  // V2.0: Stats by sales profile
  const statsByProfile = useMemo(() => {
    return salesProfiles.map(profile => {
      const profileOrders = orders.filter(o => o.sales_profile_id === profile.id)
      const completedProfileOrders = profileOrders.filter(o => o.estado === 'completada')
      const revenue = completedProfileOrders.reduce((sum, o) => sum + Number(o.total), 0)
      
      return {
        nombre: profile.name,
        tipo: profile.tipo,
        ordenes: profileOrders.length,
        completadas: completedProfileOrders.length,
        ingresos: revenue
      }
    }).filter(s => s.ordenes > 0)
  }, [salesProfiles, orders])

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
      {/* Advertencia de bloqueador de anuncios */}
      {apiError === 'bloqueador' && (
        <Card className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20">
          <div className="p-4">
            <div className="flex items-start gap-3">
              <WarningCircle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="font-semibold text-yellow-900 dark:text-yellow-100">
                  ⚠️ Bloqueador de Anuncios Detectado
                </h3>
                <p className="text-sm text-yellow-800 dark:text-yellow-200 mt-1">
                  Tu bloqueador de anuncios está bloqueando las peticiones al backend.
                  Las estadísticas por ubicación y perfil no están disponibles.
                </p>
                <div className="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
                  <strong>Solución:</strong>
                  <ul className="list-disc list-inside ml-2 mt-1">
                    <li>Desactiva el bloqueador para <code className="bg-yellow-100 dark:bg-yellow-900 px-1 rounded">localhost:5173</code></li>
                    <li>O agrega <code className="bg-yellow-100 dark:bg-yellow-900 px-1 rounded">localhost</code> a la lista blanca</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}
      
      <Tabs defaultValue="general" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="general">
            <ChartLineUp className="mr-2 h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="ubicaciones">
            <MapPin className="mr-2 h-4 w-4" />
            Por Ubicación
          </TabsTrigger>
          <TabsTrigger value="perfiles">
            <Robot className="mr-2 h-4 w-4" />
            Por Perfil de Venta
          </TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6 mt-6">
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
            <div className="flex items-start justify-between gap-4">
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
              {onViewLowStockReport && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onViewLowStockReport}
                  className="shrink-0"
                >
                  <TrendDown size={16} className="mr-2" />
                  Ver Reporte
                </Button>
              )}
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
        </TabsContent>

        <TabsContent value="ubicaciones" className="space-y-6 mt-6">
          {statsByLocation.length > 0 ? (
            <>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Ventas por Ubicación</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={statsByLocation}>
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
                        if (name === 'completadas') return [value, 'Completadas']
                        return [value, 'Órdenes']
                      }}
                    />
                    <Bar dataKey="ingresos" fill="oklch(0.60 0.15 195)" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {statsByLocation.map((stat, index) => (
                  <motion.div
                    key={stat.nombre}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1, duration: 0.3 }}
                  >
                    <Card className="p-6">
                      <div className="flex items-start gap-3">
                        <div className="p-3 rounded-lg bg-primary/10">
                          <MapPin size={24} className="text-primary" />
                        </div>
                        <div className="flex-1">
                          <p className="font-semibold">{stat.nombre}</p>
                          <p className="text-xs text-muted-foreground capitalize mb-2">{stat.tipo}</p>
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Órdenes:</span>
                              <span className="font-medium">{stat.ordenes}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Completadas:</span>
                              <span className="font-medium">{stat.completadas}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Ingresos:</span>
                              <span className="font-medium">L {stat.ingresos.toFixed(2)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </>
          ) : (
            <Card className="p-12 text-center">
              <MapPin size={48} className="mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No hay órdenes con información de ubicación aún
              </p>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="perfiles" className="space-y-6 mt-6">
          {statsByProfile.length > 0 ? (
            <>
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Ventas por Perfil de Venta</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={statsByProfile}>
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
                        if (name === 'completadas') return [value, 'Completadas']
                        return [value, 'Órdenes']
                      }}
                    />
                    <Bar dataKey="ingresos" fill="oklch(0.55 0.15 160)" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {statsByProfile.map((stat, index) => (
                  <motion.div
                    key={stat.nombre}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1, duration: 0.3 }}
                  >
                    <Card className="p-6">
                      <div className="flex items-start gap-3">
                        <div className="p-3 rounded-lg bg-accent/10">
                          <Robot size={24} className="text-accent" />
                        </div>
                        <div className="flex-1">
                          <p className="font-semibold">{stat.nombre}</p>
                          <p className="text-xs text-muted-foreground capitalize mb-2">
                            {stat.tipo.replace('_', ' ')}
                          </p>
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Órdenes:</span>
                              <span className="font-medium">{stat.ordenes}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Completadas:</span>
                              <span className="font-medium">{stat.completadas}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Ingresos:</span>
                              <span className="font-medium">L {stat.ingresos.toFixed(2)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </>
          ) : (
            <Card className="p-12 text-center">
              <Robot size={48} className="mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No hay órdenes con información de perfil de venta aún
              </p>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

// Envolver con memo para evitar re-renders innecesarios
export const DashboardStats = memo(DashboardStatsComponent)


























