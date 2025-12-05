import type { ProductWithStock, OrderWithItems, Profile } from './types'

  potentialRevenue: number
  efficiencyGain: number
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

  metric: string
  reasoning: string
}
export interface Produc
  productIds: nu
  metric: strin
  reasoning: string
  impact: number


  metric: string
  reasoning: string
  impact: number

  metrics: Optim
    insights: P
  }
    insights: In
  }
 

    insights: ProductMixInsight[]
  }
    insights: 
  }
}
export function cal
  orders: OrderW
  let score = 0
 

    productMix: 0.15
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
  const sixtyDaysAgo = new Date(

    if (customer.orders.length >= 3 && customer
      insights.push({
        customerPho
        metric: 'Días 
        reasoning: `Cliente recurrente (${cust
      })
  })
  return insights.slice(0, 12)

  products: ProductWithStock[],
): ProductMixInsight[] {
  const thirtyDaysAgo = new Date()

    


      const item = order.items.f
    }, 0)
    const totalPr

      return sum + (revenue - cost)

      const item = 
    }, 0)
    return { product, revenue: total

    .filter(p => p.revenue > 0
    .slice(0, 3)
  if (topByRevenue.length > 0) {
      type: 'best_seller',
      
    

    })

    .filter(p => p.revenue > 0 &&
  if (poorPerformers.length > 0) {

      productNames: poorPerformer
      value: poorPerformers.length,
      action: `Revisar precios inmediatamente o descontinuar estos productos`,
    })

  productPerformance.forEach(p => {
    if (!brandGroups.has(brand)) {
    }
  })
  const topBrand = Array.from(brandGroups.entries())
      brand,
      pr
    .
  if

      productNames: topBrand.p
 

    })

}
export function analyzeO
  orders: OrderWithItems[]
  const insights: OperationalInsig
  const ordersByDay = new Map<number, number>()

  })
  const peakDay = Array.from(ordersByDay.entr

    const days = ['Domingo', 'Lunes', 'Martes'
    i

      value: peakDay[1],
      action: `Asegurar personal y stock adecuado los ${days[peakDay[
    })


      type: 'process',
      metric: 'Órdenes pendientes',
      reasoning: `${pendingOrders.length} órdenes en estado pendiente pued
      impact: 0
  }
  const l

      area: 'Gestión de inventario',
      value: lowStockItems.length,
      action: `Implementar alertas autom
    })

  if (avgOrderValue && avgOrderValue < 500) {
    

      reasoning: `Valor promedio de orden
      impact: Math.round(orders
  }
  return insight





































































































































