import type { ProductWithStock, OrderWithItems, Profile } from './types'

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
  customerPhone?: string
  customerName?: string
  metric: string
  value: number
  reasoning: string
  action: string
}

export interface ProductMixInsight {
  type: 'best_seller' | 'poor_performer' | 'bundle_opportunity' | 'category_trend'
  productIds: number[]
  productNames: string[]
  metric: string
  value: number
  reasoning: string
  action: string
  impact: number
}

export interface OperationalInsight {
  type: 'process' | 'timing' | 'resource' | 'automation'
  area: string
  metric: string
  value: number
  reasoning: string
  action: string
  impact: number
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
  const recentOrders = orders.filter(o => new Date(o.fecha_orden) >= thirtyDaysAgo)
  const salesVelocityScore = Math.min(100, (recentOrders.length / 30) * 10)
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
      new Date(o.fecha_orden) >= thirtyDaysAgo
    )

    const totalSold = productOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      return sum + (item?.cantidad || 0)
    }, 0)

    const avgSalesPerWeek = totalSold / 4

    if (avgSalesPerWeek > 5 && product.stock_disponible > 10) {
      const suggestedPrice = product.precio_venta * 1.08
      insights.push({
        type: 'underpriced',
        productId: product.id,
        productName: product.nombre,
        currentPrice: product.precio_venta,
        suggestedPrice: Math.round(suggestedPrice),
        reasoning: `Alta demanda (${totalSold} unidades/mes) con buen stock. El producto puede soportar un incremento de precio del 8%.`,
        potentialImpact: Math.round((suggestedPrice - product.precio_venta) * totalSold),
        confidence: 0.85
      })
    }

    if (avgSalesPerWeek < 1 && product.stock_disponible > 15) {
      const suggestedPrice = product.precio_venta * 0.92
      insights.push({
        type: 'overpriced',
        productId: product.id,
        productName: product.nombre,
        currentPrice: product.precio_venta,
        suggestedPrice: Math.round(suggestedPrice),
        reasoning: `Baja rotación con exceso de inventario. Reducir precio 8% podría acelerar ventas y liberar capital.`,
        potentialImpact: Math.round(product.stock_disponible * suggestedPrice * 0.5),
        confidence: 0.70
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
      new Date(o.fecha_orden) >= ninetyDaysAgo
    )

    const totalSold = recentOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      return sum + (item?.cantidad || 0)
    }, 0)

    const avgMonthlyDemand = totalSold / 3
    const optimalStock = Math.ceil(avgMonthlyDemand * 1.5)

    if (product.stock_disponible > optimalStock * 2 && totalSold > 0) {
      insights.push({
        type: 'overstock',
        productId: product.id,
        productName: product.nombre,
        currentStock: product.stock_disponible,
        optimalStock: optimalStock,
        reasoning: `Stock actual es ${Math.round((product.stock_disponible / optimalStock) * 100)}% superior al óptimo basado en demanda de 90 días.`,
        action: `Reducir inventario a ${optimalStock} unidades para liberar ${Math.round((product.stock_disponible - optimalStock) * product.precio_compra)} en capital`,
        impact: Math.round((product.stock_disponible - optimalStock) * product.precio_compra)
      })
    }

    if (totalSold === 0 && product.stock_disponible > 5) {
      insights.push({
        type: 'dead_stock',
        productId: product.id,
        productName: product.nombre,
        currentStock: product.stock_disponible,
        optimalStock: 0,
        reasoning: `Sin ventas en 90 días. Inventario inmovilizado representa ${Math.round(product.stock_disponible * product.precio_compra)} en capital muerto.`,
        action: `Considerar promoción agresiva, liquidación, o descontinuar producto`,
        impact: Math.round(product.stock_disponible * product.precio_compra * 0.7)
      })
    }

    if (avgMonthlyDemand > 10 && product.stock_disponible < avgMonthlyDemand * 0.5) {
      insights.push({
        type: 'understock',
        productId: product.id,
        productName: product.nombre,
        currentStock: product.stock_disponible,
        optimalStock: optimalStock,
        reasoning: `Alta demanda (${Math.round(avgMonthlyDemand)}/mes) pero stock crítico. Riesgo de perder ${Math.round(avgMonthlyDemand * 0.3)} ventas mensuales.`,
        action: `Ordenar ${optimalStock - product.stock_disponible} unidades urgentemente`,
        impact: Math.round((avgMonthlyDemand * 0.3) * (product.precio_venta - product.precio_compra))
      })
    }

    if (totalSold > 20) {
      insights.push({
        type: 'fast_mover',
        productId: product.id,
        productName: product.nombre,
        currentStock: product.stock_disponible,
        optimalStock: Math.ceil(avgMonthlyDemand * 2),
        reasoning: `Producto estrella con ${totalSold} unidades vendidas en 90 días. Máxima prioridad de restock.`,
        action: `Mantener stock mínimo de ${Math.ceil(avgMonthlyDemand * 2)} unidades para evitar quiebres`,
        impact: Math.round(avgMonthlyDemand * (product.precio_venta - product.precio_compra))
      })
    }
  })

  return insights.sort((a, b) => b.impact - a.impact).slice(0, 10)
}

export function analyzeCustomers(orders: OrderWithItems[]): CustomerInsight[] {
  const insights: CustomerInsight[] = []
  const customerMap = new Map<string, { name: string; phone: string; orders: OrderWithItems[]; totalSpent: number; lastOrder: Date }>()

  orders.forEach(order => {
    const key = order.customer_phone || 'unknown'
    if (!customerMap.has(key)) {
      customerMap.set(key, {
        name: order.customer_name || 'Unknown',
        phone: order.customer_phone || '',
        orders: [],
        totalSpent: 0,
        lastOrder: new Date(order.fecha_orden)
      })
    }
    const customer = customerMap.get(key)!
    customer.orders.push(order)
    customer.totalSpent += order.total
    if (new Date(order.fecha_orden) > customer.lastOrder) {
      customer.lastOrder = new Date(order.fecha_orden)
    }
  })

  const customers = Array.from(customerMap.values())
  const topCustomers = customers
    .sort((a, b) => b.totalSpent - a.totalSpent)
    .slice(0, 10)

  topCustomers.slice(0, 5).forEach(customer => {
    const avgOrderValue = customer.totalSpent / customer.orders.length
    insights.push({
      type: 'high_value',
      customerPhone: customer.phone,
      customerName: customer.name,
      metric: 'Total Gastado',
      value: customer.totalSpent,
      reasoning: `Cliente VIP con ${customer.orders.length} órdenes y gasto promedio de ${Math.round(avgOrderValue)} por compra.`,
      action: `Ofrecer programa de lealtad o descuentos exclusivos para retener este cliente de alto valor`
    })
  })

  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
  const sixtyDaysAgo = new Date()
  sixtyDaysAgo.setDate(sixtyDaysAgo.getDate() - 60)

  customers.forEach(customer => {
    if (customer.orders.length >= 3 && customer.lastOrder < sixtyDaysAgo) {
      const daysSinceLastOrder = Math.floor((Date.now() - customer.lastOrder.getTime()) / (1000 * 60 * 60 * 24))
      insights.push({
        type: 'at_risk',
        customerPhone: customer.phone,
        customerName: customer.name,
        metric: 'Días sin comprar',
        value: daysSinceLastOrder,
        reasoning: `Cliente recurrente (${customer.orders.length} compras) sin actividad por ${daysSinceLastOrder} días. Riesgo de pérdida.`,
        action: `Contactar con oferta personalizada o descuento de reactivación del 10%`
      })
    }
  })

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
      new Date(o.fecha_orden) >= thirtyDaysAgo
    )

    const totalRevenue = productOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      return sum + ((item?.precio_unitario || 0) * (item?.cantidad || 0))
    }, 0)

    const totalProfit = productOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      const revenue = (item?.precio_unitario || 0) * (item?.cantidad || 0)
      const cost = product.precio_compra * (item?.cantidad || 0)
      return sum + (revenue - cost)
    }, 0)

    const unitsSold = productOrders.reduce((sum, order) => {
      const item = order.items.find(i => i.product_id === product.id)
      return sum + (item?.cantidad || 0)
    }, 0)

    return { product, revenue: totalRevenue, profit: totalProfit, unitsSold }
  })

  const topByRevenue = productPerformance
    .filter(p => p.revenue > 0)
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, 3)

  if (topByRevenue.length > 0) {
    insights.push({
      type: 'best_seller',
      productIds: topByRevenue.map(p => p.product.id),
      productNames: topByRevenue.map(p => p.product.nombre),
      metric: 'Ingresos (30 días)',
      value: topByRevenue.reduce((sum, p) => sum + p.revenue, 0),
      reasoning: `Top 3 productos generan ${Math.round((topByRevenue.reduce((sum, p) => sum + p.revenue, 0) / productPerformance.reduce((sum, p) => sum + p.revenue, 0)) * 100)}% de ingresos totales.`,
      action: `Asegurar stock constante de estos productos críticos y considerar aumentar márgenes`,
      impact: topByRevenue.reduce((sum, p) => sum + p.profit, 0)
    })
  }

  const poorPerformers = productPerformance
    .filter(p => p.revenue > 0 && p.profit < 0)

  if (poorPerformers.length > 0) {
    insights.push({
      type: 'poor_performer',
      productIds: poorPerformers.map(p => p.product.id),
      productNames: poorPerformers.map(p => p.product.nombre),
      metric: 'Productos con margen negativo',
      value: poorPerformers.length,
      reasoning: `${poorPerformers.length} productos vendiendo por debajo del costo de adquisición.`,
      action: `Revisar precios inmediatamente o descontinuar estos productos`,
      impact: Math.abs(poorPerformers.reduce((sum, p) => sum + p.profit, 0))
    })
  }

  const brandGroups = new Map<string, typeof productPerformance>()
  productPerformance.forEach(p => {
    const brand = p.product.marca || 'Sin marca'
    if (!brandGroups.has(brand)) {
      brandGroups.set(brand, [])
    }
    brandGroups.get(brand)!.push(p)
  })

  const topBrand = Array.from(brandGroups.entries())
    .map(([brand, products]) => ({
      brand,
      revenue: products.reduce((sum, p) => sum + p.revenue, 0),
      products: products.map(p => p.product)
    }))
    .sort((a, b) => b.revenue - a.revenue)[0]

  if (topBrand && topBrand.products.length > 1) {
    insights.push({
      type: 'category_trend',
      productIds: topBrand.products.map(p => p.id),
      productNames: topBrand.products.map(p => p.nombre),
      metric: 'Marca líder',
      value: topBrand.revenue,
      reasoning: `${topBrand.brand} es la marca más rentable con ${topBrand.revenue} en ingresos mensuales.`,
      action: `Ampliar catálogo de ${topBrand.brand} y negociar mejores términos con proveedor`,
      impact: Math.round(topBrand.revenue * 0.15)
    })
  }

  return insights
}

export function analyzeOperations(
  products: ProductWithStock[],
  orders: OrderWithItems[]
): OperationalInsight[] {
  const insights: OperationalInsight[] = []

  const ordersByDay = new Map<number, number>()
  orders.forEach(order => {
    const day = new Date(order.fecha_orden).getDay()
    ordersByDay.set(day, (ordersByDay.get(day) || 0) + 1)
  })

  const peakDay = Array.from(ordersByDay.entries())
    .sort((a, b) => b[1] - a[1])[0]

  if (peakDay) {
    const days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    const peakPercentage = Math.round((peakDay[1] / orders.length) * 100)
    insights.push({
      type: 'timing',
      area: 'Patrones de venta',
      metric: 'Día pico',
      value: peakDay[1],
      reasoning: `${days[peakDay[0]]} concentra ${peakPercentage}% de las ventas semanales.`,
      action: `Asegurar personal y stock adecuado los ${days[peakDay[0]]}s`,
      impact: 0
    })
  }

  const pendingOrders = orders.filter(o => o.estado === 'pendiente')
  if (pendingOrders.length > 5) {
    insights.push({
      type: 'process',
      area: 'Gestión de órdenes',
      metric: 'Órdenes pendientes',
      value: pendingOrders.length,
      reasoning: `${pendingOrders.length} órdenes en estado pendiente pueden indicar cuellos de botella en el proceso.`,
      action: `Revisar workflow de órdenes y asignar recursos para procesar backlog`,
      impact: 0
    })
  }

  const lowStockItems = products.filter(p => p.activo && p.stock_disponible < 5)
  if (lowStockItems.length > products.length * 0.2) {
    insights.push({
      type: 'automation',
      area: 'Gestión de inventario',
      metric: 'Productos con stock bajo',
      value: lowStockItems.length,
      reasoning: `${Math.round((lowStockItems.length / products.length) * 100)}% del catálogo en stock crítico sugiere proceso de reorden manual ineficiente.`,
      action: `Implementar alertas automáticas de reorden y considerar sistema de punto de reorden`,
      impact: 0
    })
  }

  const avgOrderValue = orders.reduce((sum, o) => sum + o.total, 0) / orders.length
  if (avgOrderValue && avgOrderValue < 500) {
    insights.push({
      type: 'process',
      area: 'Optimización de ventas',
      metric: 'Valor promedio de orden',
      value: Math.round(avgOrderValue),
      reasoning: `Valor promedio de orden relativamente bajo (${Math.round(avgOrderValue)}). Oportunidad de aumentar ticket promedio.`,
      action: `Implementar estrategias de upselling, bundles, o mínimo de compra para envío gratis`,
      impact: Math.round(orders.length * avgOrderValue * 0.15)
    })
  }

  return insights
}
