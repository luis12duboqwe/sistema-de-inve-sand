import type { ProductWithStock, OrderWithItems } from './types'

export interface OptimizationMetrics {
  optimizationScore: number
  potentialRevenue: number
  costSavings: number
  efficiencyGain: number
  lastAnalyzed: string
}

export interface PricingInsight {
  type: 'underpriced' | 'overpriced' | 'optimal' | 'dynamic_opportunity'
  productId: number
  productName: string
  currentPrice: number
  suggestedPrice: number
  reasoning: string
  potentialImpact: number
  confidence: number
}

export interface InventoryInsight {
  type: 'overstock' | 'understock' | 'dead_stock' | 'fast_mover' | 'seasonal'
  productId: number
  productName: string
  currentStock: number
  optimalStock: number
  reasoning: string
  action: string
  impact: number
}

export interface CustomerInsight {
  type: 'high_value' | 'at_risk' | 'growth_opportunity' | 'segment'
  customerName?: string
  customerPhone?: string
  metric: string
  value: string | number
  reasoning: string
  action: string
}

export interface ProductMixInsight {
  type: 'best_seller' | 'poor_performer' | 'bundle_opportunity' | 'category_trend'
  productIds: number[]
  productNames: string[]
  metric: string
  value: string | number
  reasoning: string
  action: string
  impact: number
}

export interface OperationalInsight {
  type: 'process' | 'timing' | 'resource' | 'automation'
  area: string
  metric: string
  value: string | number
  reasoning: string
  action: string
}

export interface OptimizationAnalysis {
  metrics: OptimizationMetrics
  pricing: {
    insights: PricingInsight[]
    summary: string
  }
  inventory: {
    insights: InventoryInsight[]
    summary: string
  }
  customer: {
    insights: CustomerInsight[]
    summary: string
  }
  productMix: {
    insights: ProductMixInsight[]
    summary: string
  }
  operations: {
    insights: OperationalInsight[]
    summary: string
  }
  aiRecommendations: string[]
}

export function calculateOptimizationScore(
  products: ProductWithStock[],
  orders: OrderWithItems[]
): number {
  let score = 0
  const weights = {
    stockHealth: 0.25,
    salesVelocity: 0.25,
    priceOptimization: 0.20,
    customerRetention: 0.15,
    productMix: 0.15
  }

  const activeProducts = products.filter(p => p.activo)
  if (activeProducts.length === 0) return 0

  const lowStockCount = activeProducts.filter(p => p.stock_disponible < 5).length
  const stockHealthScore = Math.max(0, 100 - (lowStockCount / activeProducts.length) * 100)
  score += stockHealthScore * weights.stockHealth

  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
  const recentOrders = orders.filter(o => new Date(o.created_at) >= thirtyDaysAgo)
  const salesVelocityScore = recentOrders.length > 0 ? Math.min(100, (recentOrders.length / activeProducts.length) * 50) : 0
  score += salesVelocityScore * weights.salesVelocity

  score += 70 * weights.priceOptimization
  score += 75 * weights.customerRetention
  score += 80 * weights.productMix

  return Math.round(score)
}

export function analyzePricing(
  products: ProductWithStock[],
  orders: OrderWithItems[]
): PricingInsight[] {
  const insights: PricingInsight[] = []
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  products.filter(p => p.activo).forEach(product => {
    const productOrders = orders.filter(o => 
      o.items.some(item => item.product_id === product.id) &&
      new Date(o.created_at) >= thirtyDaysAgo
    )

    const totalSold = productOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      return sum + (item?.cantidad || 0)
    }, 0)

    const avgSalesPerWeek = totalSold / 4

    if (avgSalesPerWeek > 5 && product.stock_disponible > 10) {
      const suggestedPrice = product.precio * 1.08
      insights.push({
        type: 'underpriced',
        productId: product.id,
        productName: product.nombre,
        currentPrice: product.precio,
        suggestedPrice: Math.round(suggestedPrice),
        reasoning: `Alta demanda (${totalSold} unidades/mes) con buen stock disponible. El mercado muestra disposición a pagar más por este producto.`,
        potentialImpact: Math.round((suggestedPrice - product.precio) * totalSold),
        confidence: 0.80
      })
    }

    if (avgSalesPerWeek < 1 && product.stock_disponible > 15) {
      const suggestedPrice = product.precio * 0.92
      insights.push({
        type: 'overpriced',
        productId: product.id,
        productName: product.nombre,
        currentPrice: product.precio,
        suggestedPrice: Math.round(suggestedPrice),
        reasoning: `Baja rotación con exceso de inventario. Reducir precio 8% podría acelerar ventas y liberar capital inmovilizado.`,
        potentialImpact: Math.round((product.precio - suggestedPrice) * product.stock_disponible * 0.5),
        confidence: 0.70
      })
    }

    if (product.stock_disponible < 5 && avgSalesPerWeek > 2) {
      const suggestedPrice = product.precio * 1.12
      insights.push({
        type: 'dynamic_opportunity',
        productId: product.id,
        productName: product.nombre,
        currentPrice: product.precio,
        suggestedPrice: Math.round(suggestedPrice),
        reasoning: `Stock limitado con demanda activa. Oportunidad de precio dinámico antes de reabastecer (+12%).`,
        potentialImpact: Math.round((suggestedPrice - product.precio) * product.stock_disponible),
        confidence: 0.75
      })
    }
  })

  return insights.sort((a, b) => b.potentialImpact - a.potentialImpact).slice(0, 8)
}

export function analyzeInventory(
  products: ProductWithStock[],
  orders: OrderWithItems[]
): InventoryInsight[] {
  const insights: InventoryInsight[] = []
  const ninetyDaysAgo = new Date()
  ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90)

  products.filter(p => p.activo).forEach(product => {
    const recentOrders = orders.filter(o => 
      o.items.some(item => item.product_id === product.id) &&
      new Date(o.created_at) >= ninetyDaysAgo
    )

    const totalSold = recentOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      return sum + (item?.cantidad || 0)
    }, 0)

    const avgMonthlyDemand = totalSold / 3
    const optimalStock = Math.ceil(avgMonthlyDemand * 1.5)

    if (product.stock_disponible > optimalStock * 2 && totalSold > 0) {
      const capitalTied = Math.round((product.stock_disponible - optimalStock) * product.precio * 0.6)
      insights.push({
        type: 'overstock',
        productId: product.id,
        productName: product.nombre,
        currentStock: product.stock_disponible,
        optimalStock: optimalStock,
        reasoning: `Stock actual es ${Math.round((product.stock_disponible / optimalStock) * 100)}% superior al óptimo. Capital inmovilizado que podría reinvertirse.`,
        action: `Reducir a ${optimalStock} unidades mediante promociones o ajuste de pedidos`,
        impact: capitalTied
      })
    }

    if (totalSold === 0 && product.stock_disponible > 5) {
      const deadCapital = Math.round(product.stock_disponible * product.precio * 0.6)
      insights.push({
        type: 'dead_stock',
        productId: product.id,
        productName: product.nombre,
        currentStock: product.stock_disponible,
        optimalStock: 0,
        reasoning: `Sin ventas en 90 días. ${product.stock_disponible} unidades representan $${deadCapital} en capital muerto.`,
        action: `Liquidación agresiva (30-40% desc.) o bundle con productos estrella para recuperar inversión`,
        impact: deadCapital
      })
    }

    if (avgMonthlyDemand > 10 && product.stock_disponible < avgMonthlyDemand * 0.5) {
      const lostSales = Math.round(avgMonthlyDemand * 0.3)
      const lostRevenue = Math.round(lostSales * product.precio * 0.3)
      insights.push({
        type: 'understock',
        productId: product.id,
        productName: product.nombre,
        currentStock: product.stock_disponible,
        optimalStock: optimalStock,
        reasoning: `Alta demanda (${Math.round(avgMonthlyDemand)}/mes) pero stock crítico. Riesgo de perder ~${lostSales} ventas mensuales.`,
        action: `Reorden urgente de ${optimalStock - product.stock_disponible} unidades. Prioridad máxima.`,
        impact: lostRevenue
      })
    }

    if (totalSold > 20 && avgMonthlyDemand > 0) {
      const monthlyProfit = Math.round(avgMonthlyDemand * product.precio * 0.25)
      insights.push({
        type: 'fast_mover',
        productId: product.id,
        productName: product.nombre,
        currentStock: product.stock_disponible,
        optimalStock: Math.ceil(avgMonthlyDemand * 2),
        reasoning: `Producto estrella: ${totalSold} unidades en 90 días. Genera ~$${monthlyProfit}/mes en margen.`,
        action: `Mantener stock mínimo de ${Math.ceil(avgMonthlyDemand * 2)} unidades. Nunca permitir quiebres.`,
        impact: monthlyProfit
      })
    }
  })

  return insights.sort((a, b) => b.impact - a.impact).slice(0, 10)
}

export function analyzeCustomers(orders: OrderWithItems[]): CustomerInsight[] {
  const insights: CustomerInsight[] = []
  const customerMap = new Map<string, { 
    name: string
    phone: string
    orders: OrderWithItems[]
    totalSpent: number
    lastOrder: Date 
  }>()

  orders.forEach(order => {
    const key = order.customer_phone || 'unknown'
    if (!customerMap.has(key)) {
      customerMap.set(key, {
        name: order.customer_name,
        phone: order.customer_phone,
        orders: [],
        totalSpent: 0,
        lastOrder: new Date(order.created_at)
      })
    }
    const customer = customerMap.get(key)!
    customer.orders.push(order)
    customer.totalSpent += order.total
    const orderDate = new Date(order.created_at)
    if (orderDate > customer.lastOrder) {
      customer.lastOrder = orderDate
    }
  })

  const sixtyDaysAgo = new Date()
  sixtyDaysAgo.setDate(sixtyDaysAgo.getDate() - 60)

  customerMap.forEach(customer => {
    if (customer.orders.length >= 3 && customer.totalSpent > 5000) {
      insights.push({
        type: 'high_value',
        customerName: customer.name,
        customerPhone: customer.phone,
        metric: 'Total Gastado',
        value: customer.totalSpent,
        reasoning: `Cliente VIP con ${customer.orders.length} compras y $${customer.totalSpent} en valor total. Top 10% de la base.`,
        action: `Programa de lealtad VIP: descuentos exclusivos 5-10%, prioridad en nuevos lanzamientos, seguimiento personalizado`
      })
    }

    if (customer.orders.length >= 3 && customer.lastOrder < sixtyDaysAgo) {
      const daysSinceLastOrder = Math.round((Date.now() - customer.lastOrder.getTime()) / (1000 * 60 * 60 * 24))
      insights.push({
        type: 'at_risk',
        customerName: customer.name,
        customerPhone: customer.phone,
        metric: 'Días desde última compra',
        value: daysSinceLastOrder,
        reasoning: `Cliente recurrente (${customer.orders.length} compras) inactivo ${daysSinceLastOrder} días. Alto riesgo de pérdida.`,
        action: `Campaña de reactivación: WhatsApp personalizado, oferta especial 15%, recordatorio de productos que compró antes`
      })
    }

    if (customer.orders.length === 2 && customer.lastOrder >= sixtyDaysAgo) {
      insights.push({
        type: 'growth_opportunity',
        customerName: customer.name,
        customerPhone: customer.phone,
        metric: 'Compras',
        value: customer.orders.length,
        reasoning: `Cliente con potencial: 2 compras recientes mostrando interés. Está en fase de conversión a recurrente.`,
        action: `Incentivo de tercera compra: cupón 10%, cross-sell de accesorios, invitar a seguir redes sociales`
      })
    }
  })

  const avgOrderValue = orders.length > 0 
    ? orders.reduce((sum, o) => sum + o.total, 0) / orders.length 
    : 0

  if (avgOrderValue > 0) {
    const highValueCustomers = Array.from(customerMap.values())
      .filter(c => c.totalSpent / c.orders.length > avgOrderValue * 1.5)
      .length

    if (highValueCustomers > 0) {
      insights.push({
        type: 'segment',
        metric: 'Clientes alto valor',
        value: highValueCustomers,
        reasoning: `${highValueCustomers} clientes gastan 50%+ sobre el promedio ($${Math.round(avgOrderValue)}).`,
        action: `Crear segmento premium: ofertas de bundles, financiamiento preferencial, atención prioritaria`
      })
    }
  }

  return insights.slice(0, 12)
}

export function analyzeProductMix(
  products: ProductWithStock[],
  orders: OrderWithItems[]
): ProductMixInsight[] {
  const insights: ProductMixInsight[] = []
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  const productPerformance = products.filter(p => p.activo).map(product => {
    const productOrders = orders.filter(o => 
      o.items.some(item => item.product_id === product.id) &&
      new Date(o.created_at) >= thirtyDaysAgo
    )

    const totalRevenue = productOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      return sum + ((item?.precio_unitario || 0) * (item?.cantidad || 0))
    }, 0)

    const totalQuantity = productOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      return sum + (item?.cantidad || 0)
    }, 0)

    const profit = totalRevenue - (totalQuantity * product.precio * 0.6)
    return { product, revenue: totalRevenue, quantity: totalQuantity, profit }
  })

  const topByRevenue = productPerformance
    .filter(p => p.revenue > 0)
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, 3)

  if (topByRevenue.length > 0) {
    const totalRevenue = topByRevenue.reduce((sum, p) => sum + p.revenue, 0)
    insights.push({
      type: 'best_seller',
      productIds: topByRevenue.map(p => p.product.id),
      productNames: topByRevenue.map(p => p.product.nombre),
      metric: 'Ingresos últimos 30 días',
      value: totalRevenue,
      reasoning: `Top 3 productos generan $${totalRevenue} (${topByRevenue.map(p => p.product.nombre).join(', ')}). Concentrar estrategia aquí.`,
      action: `Asegurar stock perpetuo, invertir en marketing de estos SKUs, crear bundles alrededor de ellos`,
      impact: Math.round(totalRevenue * 0.2)
    })
  }

  const poorPerformers = productPerformance
    .filter(p => p.revenue > 0 && p.profit < 0)
    .sort((a, b) => a.profit - b.profit)
    .slice(0, 3)

  if (poorPerformers.length > 0) {
    insights.push({
      type: 'poor_performer',
      productIds: poorPerformers.map(p => p.product.id),
      productNames: poorPerformers.map(p => p.product.nombre),
      metric: 'Productos con pérdida',
      value: poorPerformers.length,
      reasoning: `${poorPerformers.length} productos vendiendo por debajo del costo. Están destruyendo margen.`,
      action: `Revisar precios inmediatamente o descontinuar. No seguir invirtiendo en inventario de estos SKUs`,
      impact: Math.round(Math.abs(poorPerformers.reduce((sum, p) => sum + p.profit, 0)))
    })
  }

  const brandGroups = new Map<string, { products: ProductWithStock[]; revenue: number }>()
  productPerformance.forEach(p => {
    const brand = p.product.marca
    if (!brandGroups.has(brand)) {
      brandGroups.set(brand, { products: [], revenue: 0 })
    }
    brandGroups.get(brand)!.products.push(p.product)
    brandGroups.get(brand)!.revenue += p.revenue
  })

  const topBrand = Array.from(brandGroups.entries())
    .sort((a, b) => b[1].revenue - a[1].revenue)[0]

  if (topBrand && topBrand[1].revenue > 0) {
    insights.push({
      type: 'category_trend',
      productIds: topBrand[1].products.map(p => p.id),
      productNames: topBrand[1].products.map(p => p.nombre),
      metric: 'Marca líder',
      value: topBrand[1].revenue,
      reasoning: `${topBrand[0]} domina con $${topBrand[1].revenue} en ingresos. ${topBrand[1].products.length} SKUs activos.`,
      action: `Expandir catálogo de ${topBrand[0]}, negociar mejores términos con distribuidor, marketing enfocado en esta marca`,
      impact: Math.round(topBrand[1].revenue * 0.15)
    })
  }

  return insights.filter(i => i.impact > 0)
}

export function analyzeOperations(
  products: ProductWithStock[],
  orders: OrderWithItems[]
): OperationalInsight[] {
  const insights: OperationalInsight[] = []

  const ordersByDay = new Map<number, number>()
  orders.forEach(order => {
    const day = new Date(order.created_at).getDay()
    ordersByDay.set(day, (ordersByDay.get(day) || 0) + 1)
  })

  const peakDay = Array.from(ordersByDay.entries())
    .sort((a, b) => b[1] - a[1])[0]

  if (peakDay) {
    const days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    insights.push({
      type: 'timing',
      area: 'Patrones de demanda',
      metric: 'Día pico',
      value: days[peakDay[0]],
      reasoning: `${days[peakDay[0]]} concentra ${peakDay[1]} órdenes, ${Math.round((peakDay[1] / orders.length) * 100)}% del total.`,
      action: `Asegurar personal y stock adecuado los ${days[peakDay[0]]}s. Planear promociones en días de baja demanda.`
    })
  }

  const pendingOrders = orders.filter(o => o.estado === 'pendiente')
  if (pendingOrders.length > 5) {
    insights.push({
      type: 'process',
      area: 'Procesamiento de órdenes',
      metric: 'Órdenes pendientes',
      value: pendingOrders.length,
      reasoning: `${pendingOrders.length} órdenes en estado pendiente pueden indicar cuellos de botella en fulfillment.`,
      action: `Revisar proceso de confirmación y empaque. Automatizar notificaciones de seguimiento. Asignar responsable.`
    })
  }

  const lowStockItems = products.filter(p => p.activo && p.stock_disponible < 5).length
  if (lowStockItems > 3) {
    insights.push({
      type: 'automation',
      area: 'Gestión de inventario',
      metric: 'Productos en riesgo de quiebre',
      value: lowStockItems,
      reasoning: `${lowStockItems} productos bajo umbral crítico. Reorden manual es ineficiente y riesgoso.`,
      action: `Implementar alertas automáticas por WhatsApp cuando stock < 5. Crear lista de reorden semanal automatizada.`
    })
  }

  const avgOrderValue = orders.length > 0 
    ? orders.reduce((sum, o) => sum + o.total, 0) / orders.length 
    : 0

  if (avgOrderValue && avgOrderValue < 500) {
    insights.push({
      type: 'resource',
      area: 'Valor de transacción',
      metric: 'Ticket promedio',
      value: `$${Math.round(avgOrderValue)}`,
      reasoning: `Ticket promedio bajo ($${Math.round(avgOrderValue)}). Pequeño incremento tiene gran impacto acumulado.`,
      action: `Implementar upselling: "lleva 2 x precio especial", bundles de accesorios, financiamiento en compras >$1000`
    })
  }

  const completedOrders = orders.filter(o => o.estado === 'completada')
  const cancelledOrders = orders.filter(o => o.estado === 'cancelada')
  if (cancelledOrders.length > 0) {
    const cancellationRate = (cancelledOrders.length / orders.length) * 100
    if (cancellationRate > 10) {
      insights.push({
        type: 'process',
        area: 'Retención de ventas',
        metric: 'Tasa de cancelación',
        value: `${cancellationRate.toFixed(1)}%`,
        reasoning: `${cancellationRate.toFixed(1)}% de órdenes canceladas. Cada cancelación es ingreso perdido.`,
        action: `Investigar razones: confirmar disponibilidad antes de venta, mejorar comunicación de tiempos de entrega, ofrecer alternativas`
      })
    }
  }

  return insights.slice(0, 8)
}
