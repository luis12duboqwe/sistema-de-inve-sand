import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type {
  ProductWithStock,
  OrderWithItems,
  Location,
  SalesProfile,
  User,
  DashboardStats,
  InventoryAlert,
  SalesReport,
  StockSummaryByLocation,
  SalesSummaryByLocation,
  BusinessInsightsResponse,
  BusinessInsightRecommendation
} from '@/lib/types'
import { Package, ShoppingCart, ChartLineUp, WarningCircle, Money, TrendDown, MapPin, Robot, CalendarCheck, ArrowClockwise, MagicWand } from '@phosphor-icons/react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format, subDays, isSameDay } from 'date-fns'
import { motion } from 'framer-motion'
import { useMemo, useState, useEffect, useCallback, memo } from 'react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'

const ALERT_STYLES: Record<InventoryAlert['alert_level'], { label: string; className: string }> = {
  out_of_stock: {
    label: 'Agotado',
    className: 'border border-red-600 bg-red-600 text-white'
  },
  critical: {
    label: 'Crítico',
    className: 'border border-red-200 bg-red-100 text-red-700 dark:border-transparent dark:bg-red-500/20 dark:text-red-50'
  },
  low: {
    label: 'Stock Bajo',
    className: 'border border-amber-200 bg-amber-100 text-amber-800 dark:border-transparent dark:bg-amber-500/20 dark:text-amber-50'
  }
}

const INSIGHT_PRIORITY_STYLES: Record<BusinessInsightRecommendation['priority'], string> = {
  critica: 'bg-red-500/15 text-red-50 border border-red-400/40',
  alta: 'bg-orange-500/15 text-orange-50 border border-orange-400/40',
  media: 'bg-amber-500/15 text-amber-50 border border-amber-400/40',
  baja: 'bg-emerald-500/15 text-emerald-50 border border-emerald-400/40'
}

const INSIGHT_PRIORITY_LABELS: Record<BusinessInsightRecommendation['priority'], string> = {
  critica: 'Crítica',
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja'
}

interface DashboardStatsProps {
  products: ProductWithStock[]
  orders: OrderWithItems[]
  currentUser?: User | null
  onViewLowStockReport?: () => void
}

function DashboardStatsComponent({ products, orders, currentUser, onViewLowStockReport }: DashboardStatsProps) {
  const [locations, setLocations] = useState<Location[]>([])
  const [salesProfiles, setSalesProfiles] = useState<SalesProfile[]>([])
  const [apiError, setApiError] = useState<string | null>(null)
  const [dashboardMetrics, setDashboardMetrics] = useState<DashboardStats | null>(null)
  const [salesReport, setSalesReport] = useState<SalesReport | null>(null)
  const [inventoryAlerts, setInventoryAlerts] = useState<InventoryAlert[]>([])
  const [salesSummaryByLocation, setSalesSummaryByLocation] = useState<SalesSummaryByLocation[]>([])
  const [stockSummaryByLocation, setStockSummaryByLocation] = useState<StockSummaryByLocation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)
  const [businessInsights, setBusinessInsights] = useState<BusinessInsightsResponse | null>(null)
  const [insightsSource, setInsightsSource] = useState<'backend' | 'local' | null>(null)
  const [isRefreshingInsights, setIsRefreshingInsights] = useState(false)
  const [insightsError, setInsightsError] = useState<string | null>(null)

  const loadLocations = useCallback(async () => {
    try {
      const data = await inventoryServiceInstance.listLocations()
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
      const data = await inventoryServiceInstance.listSalesProfiles()
      setSalesProfiles(data)
      setApiError(null)
    } catch (error) {
      console.error('Error loading sales profiles:', error)
      // Si hay error, simplemente no mostramos datos de perfiles
      setSalesProfiles([])
    }
  }, [])

  const loadDashboardInsights = useCallback(async () => {
    try {
      setIsLoading(true)
      setApiError(null)
      const insightsPromise = inventoryServiceInstance.generateBusinessInsights({ use_cache: true }).catch(error => {
        console.error('Error loading business insights:', error)
        const message = error instanceof Error ? error.message : 'No fue posible generar insights con IA'
        setInsightsError(message)
        return null
      })

      const [stats, report, alerts, salesByLocation, stockByLocation, insights] = await Promise.all([
        inventoryServiceInstance.getDashboardStats().catch(() => null),
        inventoryServiceInstance.getSalesReport({ top_limit: 5 }).catch(() => null),
        inventoryServiceInstance.getInventoryAlerts().catch(() => []),
        inventoryServiceInstance.getSalesSummaryByLocation().catch(() => []),
        inventoryServiceInstance.getStockSummaryByLocation(true).catch(() => []),
        insightsPromise
      ])

      if (stats) {
        setDashboardMetrics(stats)
      }
      if (report) {
        setSalesReport(report)
      }
      setInventoryAlerts(alerts)
      setSalesSummaryByLocation(salesByLocation)
      setStockSummaryByLocation(stockByLocation)
      if (insights) {
        setBusinessInsights(insights)
        const source = insights.tokens_used > 0 || Boolean(insights.raw_response) ? 'backend' : 'local'
        setInsightsSource(source)
        setInsightsError(null)
      } else {
        setBusinessInsights(null)
        setInsightsSource(null)
      }
      setLastUpdated(new Date().toISOString())
    } catch (error) {
      console.error('Error loading dashboard insights:', error)
      const message = error instanceof Error ? error.message : 'Error desconocido'
      if (message.toLowerCase().includes('failed to fetch')) {
        setApiError('bloqueador')
      } else {
        setApiError(message)
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const refreshBusinessInsights = useCallback(async () => {
    setIsRefreshingInsights(true)
    try {
      const insights = await inventoryServiceInstance.generateBusinessInsights({
        use_cache: false,
        force_refresh: true
      })
      if (insights) {
        setBusinessInsights(insights)
        const source = insights.tokens_used > 0 || Boolean(insights.raw_response) ? 'backend' : 'local'
        setInsightsSource(source)
        setInsightsError(null)
      }
    } catch (error) {
      console.error('Error refreshing business insights:', error)
      const message = error instanceof Error ? error.message : 'No fue posible regenerar las recomendaciones'
      setInsightsError(message)
    } finally {
      setIsRefreshingInsights(false)
    }
  }, [])

  useEffect(() => {
    loadLocations()
    loadSalesProfiles()
    loadDashboardInsights()
  }, [loadLocations, loadSalesProfiles, loadDashboardInsights])

  const activeProducts = products.filter(p => p.activo).length
  const totalProducts = products.length

  const pendingOrders = orders.filter(o => o.estado === 'pendiente').length
  const readyToDeliverOrders = orders.filter(o => o.estado === 'por_entregar').length
  const completedOrders = orders.filter(o => o.estado === 'completada').length
  const totalOrders = orders.length

  const fallbackDashboardStats = useMemo<DashboardStats>(() => {
    const lowStockCount = products.filter(p => p.activo && p.stock_disponible > 0 && p.stock_disponible < 5).length
    const outOfStockCount = products.filter(p => p.activo && p.stock_disponible === 0).length
    const totalInventoryValue = products
      .filter(p => p.activo)
      .reduce((sum, product) => sum + (Number(product.precio) * product.stock_disponible), 0)

    const today = new Date()
    const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate())
    const endOfToday = new Date(startOfToday)
    endOfToday.setHours(23, 59, 59, 999)
    const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)
    const startOfLastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
    const endOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0)
    endOfLastMonth.setHours(23, 59, 59, 999)

    const nonCancelledOrders = orders.filter(o => o.estado !== 'cancelada')
    const ordersToday = nonCancelledOrders.filter(o => {
      const createdAt = new Date(o.created_at)
      return createdAt >= startOfToday && createdAt <= endOfToday
    })
    const ordersThisMonth = nonCancelledOrders.filter(o => new Date(o.created_at) >= startOfMonth)
    const ordersLastMonth = nonCancelledOrders.filter(o => {
      const createdAt = new Date(o.created_at)
      return createdAt >= startOfLastMonth && createdAt <= endOfLastMonth
    })

    const sumTotals = (list: OrderWithItems[]) => list.reduce((sum, order) => sum + Number(order.total || 0), 0)
    const totalRevenueToday = sumTotals(ordersToday)
    const totalRevenueMonth = sumTotals(ordersThisMonth)
    const totalRevenueLastMonth = sumTotals(ordersLastMonth)
    const averageTicketMonth = ordersThisMonth.length > 0
      ? Number((totalRevenueMonth / ordersThisMonth.length).toFixed(2))
      : 0

    return {
      active_products: activeProducts,
      total_products: totalProducts,
      low_stock_count: lowStockCount,
      out_of_stock_count: outOfStockCount,
      total_inventory_value: totalInventoryValue,
      pending_orders: pendingOrders,
      total_orders_today: ordersToday.length,
      total_revenue_today: totalRevenueToday,
      total_revenue_month: totalRevenueMonth,
      total_revenue_last_month: totalRevenueLastMonth,
      gross_margin_month: 0,
      average_ticket_month: averageTicketMonth
    }
  }, [products, orders, activeProducts, totalProducts, pendingOrders])

  const mergedDashboardStats = dashboardMetrics ?? fallbackDashboardStats
  const lowStockProducts = mergedDashboardStats.low_stock_count
  const outOfStockProducts = mergedDashboardStats.out_of_stock_count
  const inventoryValue = mergedDashboardStats.total_inventory_value

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

  const serviceTopProducts = useMemo(() => {
    if (!salesReport?.top_products?.length) return []
    return salesReport.top_products.map(product => ({
      nombre: product.product_name,
      cantidad: product.units_sold,
      ingresos: product.total_revenue
    }))
  }, [salesReport])

  const fallbackTopProducts = useMemo(() => {
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

  const topProducts = serviceTopProducts.length > 0 ? serviceTopProducts : fallbackTopProducts

  const inventorySummaryMap = useMemo(() => {
    const map = new Map<number, StockSummaryByLocation>()
    stockSummaryByLocation.forEach(summary => map.set(summary.location_id, summary))
    return map
  }, [stockSummaryByLocation])

  const serviceStatsByLocation = useMemo(() => {
    if (!salesSummaryByLocation.length) return []
    return salesSummaryByLocation.map(summary => {
      const location = locations.find(loc => loc.id === summary.location_id)
      const inventorySummary = inventorySummaryMap.get(summary.location_id)
      return {
        nombre: summary.location_nombre,
        tipo: location?.tipo ?? 'tienda',
        ordenes: summary.total_ordenes,
        completadas: summary.total_ordenes,
        ingresos: summary.total_ingresos,
        ticket_promedio: summary.ticket_promedio,
        unidades: summary.total_unidades_vendidas,
        inventory: inventorySummary ? inventorySummary.valor_inventario : null,
        productos_unicos: inventorySummary ? inventorySummary.total_productos : null
      }
    })
  }, [salesSummaryByLocation, locations, inventorySummaryMap])

  // V2.0: Stats by location
  const fallbackStatsByLocation = useMemo(() => {
    return locations.map(location => {
      const locationOrders = orders.filter(o => o.source_location_id === location.id)
      const completedLocationOrders = locationOrders.filter(o => o.estado === 'completada')
      const revenue = completedLocationOrders.reduce((sum, o) => sum + Number(o.total), 0)
      const unidades = completedLocationOrders.reduce((sum, order) => {
        const itemsTotal = order.items?.reduce((acc, item) => acc + item.cantidad, 0) ?? 0
        return sum + itemsTotal
      }, 0)
      const ticketPromedio = completedLocationOrders.length > 0 ? revenue / completedLocationOrders.length : null
      
      return {
        nombre: location.nombre,
        tipo: location.tipo,
        ordenes: locationOrders.length,
        completadas: completedLocationOrders.length,
        ingresos: revenue,
        unidades,
        ticket_promedio: ticketPromedio,
        inventory: null,
        productos_unicos: null
      }
    }).filter(s => s.ordenes > 0)
  }, [locations, orders])

  const statsByLocation = serviceStatsByLocation.length > 0 ? serviceStatsByLocation : fallbackStatsByLocation

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

  // Permission check for financial data
  const canViewFinancials = useMemo(() => {
    if (!currentUser) return true // Fallback for local mode
    return currentUser.role?.is_system_role || 
           currentUser.role?.permissions?.some(p => p.slug === 'reports:view')
  }, [currentUser])

  // Calculate daily orders for non-financial view
  const dailyOrders = useMemo(() => {
    const today = new Date()
    return orders.filter(o => isSameDay(new Date(o.created_at), today)).length
  }, [orders])

  const currencyFormatter = useMemo(() => new Intl.NumberFormat('es-HN', {
    style: 'currency',
    currency: 'HNL',
    maximumFractionDigits: 2
  }), [])

  const formatCurrency = useCallback((value: number) => currencyFormatter.format(value ?? 0), [currencyFormatter])

  const lastUpdatedLabel = useMemo(() => (lastUpdated ? format(new Date(lastUpdated), 'dd/MM HH:mm') : null), [lastUpdated])

  const stats = [
    {
      title: 'Productos Activos',
      value: mergedDashboardStats.active_products,
      subtitle: `${mergedDashboardStats.total_products} total`,
      icon: Package,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      title: 'Órdenes Totales',
      value: totalOrders,
      subtitle: `${completedOrders} completadas • ${mergedDashboardStats.pending_orders} pendientes`,
      icon: ShoppingCart,
      color: 'text-blue-600',
      bgColor: 'bg-blue-600/10',
    },
    {
      title: 'Ingresos del Mes',
      value: canViewFinancials ? formatCurrency(mergedDashboardStats.total_revenue_month) : '---',
      subtitle: canViewFinancials ? `Hoy: ${formatCurrency(mergedDashboardStats.total_revenue_today)}` : 'Ventas completadas',
      icon: Money,
      color: 'text-green-600',
      bgColor: 'bg-green-600/10',
    },
    canViewFinancials ? {
      title: 'Valor del Inventario',
      value: formatCurrency(inventoryValue),
      subtitle: `${lowStockProducts + outOfStockProducts} productos en alerta`,
      icon: ChartLineUp,
      color: 'text-accent',
      bgColor: 'bg-accent/10',
    } : {
      title: 'Órdenes de Hoy',
      value: mergedDashboardStats.total_orders_today || dailyOrders,
      subtitle: 'Procesadas hoy',
      icon: CalendarCheck,
      color: 'text-accent',
      bgColor: 'bg-accent/10',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold">Panel Inteligente</p>
          <p className="text-xs text-muted-foreground">
            Última actualización: {lastUpdatedLabel ?? 'Automática'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadDashboardInsights}
            disabled={isLoading}
            className="flex items-center"
          >
            <ArrowClockwise
              size={16}
              className={`mr-2 ${isLoading ? 'animate-spin' : ''}`}
            />
            {isLoading ? 'Actualizando...' : 'Actualizar'}
          </Button>
        </div>
      </div>

      {apiError && apiError !== 'bloqueador' && (
        <Card className="border-destructive/40 bg-destructive/5">
          <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <WarningCircle className="h-5 w-5 text-destructive" />
              <div>
                <p className="font-semibold text-destructive">No pudimos cargar los reportes</p>
                <p className="text-sm text-destructive/80">{apiError}</p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={loadDashboardInsights} disabled={isLoading}>
              Reintentar
            </Button>
          </div>
        </Card>
      )}

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

      {inventoryAlerts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45, duration: 0.3 }}
        >
          <Card className="p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold">Productos críticos</h3>
                <p className="text-sm text-muted-foreground">
                  Prioriza reposición en los próximos envíos
                </p>
              </div>
              <Badge variant="outline" className="border border-dashed border-muted-foreground/40">
                {inventoryAlerts.length} alertas
              </Badge>
            </div>
            <div className="space-y-3">
              {inventoryAlerts.slice(0, 5).map(alert => {
                const severity = ALERT_STYLES[alert.alert_level]
                return (
                  <div
                    key={`${alert.product_id}-${alert.sku}-${alert.alert_level}`}
                    className="flex items-center justify-between rounded-lg border px-4 py-3"
                  >
                    <div>
                      <p className="font-semibold">{alert.product_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {alert.sku} • {alert.category}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className={severity.className}>
                        {severity.label}
                      </Badge>
                      <span className="font-semibold">{alert.current_stock} u</span>
                    </div>
                  </div>
                )
              })}
              {inventoryAlerts.length > 5 && (
                <p className="text-xs text-muted-foreground">
                  y {inventoryAlerts.length - 5} producto{inventoryAlerts.length - 5 === 1 ? '' : 's'} más con alerta
                </p>
              )}
            </div>
          </Card>
        </motion.div>
      )}

      {businessInsights && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.3 }}
        >
          <Card className="relative overflow-hidden border border-slate-900/40 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6 text-white">
            <div className="pointer-events-none absolute inset-0 opacity-40">
              <div className="absolute -top-20 -right-16 h-48 w-48 rounded-full bg-emerald-400/30 blur-3xl" />
              <div className="absolute -bottom-16 -left-10 h-56 w-56 rounded-full bg-cyan-400/20 blur-3xl" />
            </div>
              <div className="relative flex flex-col gap-6">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-emerald-200">
                    <MagicWand size={16} className="text-emerald-300" />
                    IA Operativa
                  </div>
                  <h3 className="text-xl font-semibold mt-1">Recomendaciones Inteligentes</h3>
                  <p className="text-sm text-white/70">
                    {businessInsights.ai_summary ?? `Análisis de ${businessInsights.period_days} días de ventas.`}
                  </p>
                </div>
                  <div className="flex flex-col items-start gap-2 sm:items-end">
                    <Badge variant="outline" className="border-white/30 text-white">
                      {insightsSource === 'backend' ? 'Fuente: IA Avanzada' : insightsSource === 'local' ? 'Fuente: Análisis Local' : 'Fuente desconocida'}
                    </Badge>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={refreshBusinessInsights}
                      disabled={isRefreshingInsights}
                      className="bg-white/10 text-white hover:bg-white/20 border border-white/30"
                    >
                      <MagicWand size={14} className={`mr-2 ${isRefreshingInsights ? 'animate-spin' : ''}`} />
                      {isRefreshingInsights ? 'Generando...' : 'Regenerar IA'}
                    </Button>
                  </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-wide text-white/60">Órdenes Analizadas</p>
                  <p className="text-2xl font-semibold mt-1">{businessInsights.metrics.kpis.orders_count}</p>
                  <p className="text-xs text-white/60">Últimos {businessInsights.period_days} días</p>
                </div>
                {canViewFinancials && (
                  <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/60">Ingresos Evaluados</p>
                    <p className="text-2xl font-semibold mt-1">{formatCurrency(businessInsights.metrics.kpis.total_revenue)}</p>
                    <p className="text-xs text-white/60">Ticket promedio {formatCurrency(businessInsights.metrics.kpis.avg_order_value)}</p>
                  </div>
                )}
                <div className={`rounded-lg border border-white/10 bg-white/5 p-4 ${canViewFinancials ? '' : 'md:col-span-2'}`}>
                  <p className="text-xs uppercase tracking-wide text-white/60">Margen estimado</p>
                  <p className="text-2xl font-semibold mt-1">{(businessInsights.metrics.kpis.gross_margin_estimate ?? 0).toFixed(1)}%</p>
                  <p className="text-xs text-white/60">Proyección basada en ventas completadas</p>
                </div>
              </div>

              <div className="space-y-3">
                {businessInsights.recommendations.length > 0 ? (
                  businessInsights.recommendations.slice(0, 3).map((recommendation, index) => (
                    <div
                      key={`${recommendation.title}-${index}`}
                      className="rounded-lg border border-white/10 bg-white/5 p-4"
                    >
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="font-medium">{recommendation.title}</p>
                          {recommendation.action && (
                            <p className="text-sm text-white/70">{recommendation.action}</p>
                          )}
                          {recommendation.impact && (
                            <p className="text-xs text-white/50 mt-1">{recommendation.impact}</p>
                          )}
                        </div>
                        <Badge
                          variant="outline"
                          className={INSIGHT_PRIORITY_STYLES[recommendation.priority]}
                        >
                          {INSIGHT_PRIORITY_LABELS[recommendation.priority]}
                        </Badge>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-lg border border-dashed border-white/20 bg-white/5 p-4 text-sm text-white/70">
                    No hay recomendaciones todavía. Continúa registrando ventas para habilitar insights avanzados.
                  </div>
                )}
                {insightsError && (
                  <p className="text-xs text-red-200/90">
                    {insightsError}
                  </p>
                )}
              </div>

              {/* Usuario no desea detalle visual de top sellers / slow movers aquí */}
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
            <h3 className="text-lg font-semibold mb-4">{canViewFinancials ? 'Ventas Últimos 7 Días' : 'Órdenes Últimos 7 Días'}</h3>
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
                  dataKey={canViewFinancials ? "ventas" : "ordenes"} 
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
                <Bar dataKey={canViewFinancials ? "ingresos" : "cantidad"} fill="oklch(0.60 0.15 195)" radius={[8, 8, 0, 0]} />
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
                <h3 className="text-lg font-semibold mb-4">{canViewFinancials ? 'Ventas por Ubicación' : 'Órdenes por Ubicación'}</h3>
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
                    <Bar dataKey={canViewFinancials ? "ingresos" : "completadas"} fill="oklch(0.60 0.15 195)" radius={[8, 8, 0, 0]} />
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
                            {canViewFinancials && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Ingresos:</span>
                                <span className="font-medium">{formatCurrency(stat.ingresos)}</span>
                              </div>
                            )}
                            {canViewFinancials && typeof stat.ticket_promedio === 'number' && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Ticket promedio:</span>
                                <span className="font-medium">{formatCurrency(stat.ticket_promedio)}</span>
                              </div>
                            )}
                            {stat.unidades && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Unidades vendidas:</span>
                                <span className="font-medium">{stat.unidades}</span>
                              </div>
                            )}
                            {canViewFinancials && typeof stat.inventory === 'number' && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Inventario:</span>
                                <span className="font-medium">{formatCurrency(stat.inventory)}</span>
                              </div>
                            )}
                            {typeof stat.productos_unicos === 'number' && stat.productos_unicos > 0 && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Productos únicos:</span>
                                <span className="font-medium">{stat.productos_unicos}</span>
                              </div>
                            )}
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


























