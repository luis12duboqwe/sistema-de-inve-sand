import { ProductWithStock, OrderWithItems, Profile } from './types'

export interface SalesForecast {
  productId: number
  productName: string
  currentStock: number
  averageDailySales: number
  predictedSalesNext7Days: number
  predictedSalesNext30Days: number
  daysUntilStockout: number
  restockRecommendation: number
  confidence: number
  trend: 'increasing' | 'stable' | 'decreasing'
}

export interface RestockAlert {
  productId: number
  productName: string
  currentStock: number
  daysUntilStockout: number
  recommendedOrderQuantity: number
  urgency: 'critical' | 'high' | 'medium' | 'low'
  estimatedRestockDate: Date
  reasoning: string
}

export interface ForecastingSummary {
  totalProducts: number
  productsNeedingRestock: number
  criticalStockAlerts: number
  estimatedRevenue7Days: number
  estimatedRevenue30Days: number
  topPerformingProducts: string[]
  slowMovingProducts: string[]
}

export async function generateAIForecast(
  products: ProductWithStock[],
  orders: OrderWithItems[],
  profile: Profile
): Promise<{ forecasts: SalesForecast[]; summary: ForecastingSummary }> {
  const now = new Date()
  const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
  const ninetyDaysAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)

  const recentOrders = orders.filter(
    (o) => new Date(o.created_at) >= thirtyDaysAgo && o.estado !== 'cancelada'
  )

  const olderOrders = orders.filter(
    (o) =>
      new Date(o.created_at) >= ninetyDaysAgo &&
      new Date(o.created_at) < thirtyDaysAgo &&
      o.estado !== 'cancelada'
  )

  const forecasts: SalesForecast[] = []

  for (const product of products) {
    if (!product.activo) continue

    const recentSales = calculateProductSales(product.id, recentOrders)
    const olderSales = calculateProductSales(product.id, olderOrders)

    const recentDailySales = recentSales.totalQuantity / 30
    const olderDailySales = olderSales.totalQuantity / 60

    const trend = calculateTrend(recentDailySales, olderDailySales)

    const growthFactor = calculateGrowthFactor(recentDailySales, olderDailySales, trend)

    const predictedDailySales = Math.max(0, recentDailySales * growthFactor)
    const predictedSales7Days = Math.round(predictedDailySales * 7)
    const predictedSales30Days = Math.round(predictedDailySales * 30)

    const daysUntilStockout =
      predictedDailySales > 0
        ? Math.round(product.stock_disponible / predictedDailySales)
        : 999

    const safetyStock = Math.ceil(predictedDailySales * 14)
    const restockRecommendation = Math.max(
      0,
      safetyStock + predictedSales30Days - product.stock_disponible
    )

    const confidence = calculateConfidence(recentSales.orderCount, olderSales.orderCount)

    forecasts.push({
      productId: product.id,
      productName: `${product.marca} ${product.modelo}`,
      currentStock: product.stock_disponible,
      averageDailySales: recentDailySales,
      predictedSalesNext7Days: predictedSales7Days,
      predictedSalesNext30Days: predictedSales30Days,
      daysUntilStockout,
      restockRecommendation,
      confidence,
      trend,
    })
  }

  forecasts.sort((a, b) => a.daysUntilStockout - b.daysUntilStockout)

  const summary = generateForecastingSummary(forecasts, products)

  return { forecasts, summary }
}

export async function generateRestockAlerts(
  forecasts: SalesForecast[],
  profile: Profile
): Promise<RestockAlert[]> {
  const alerts: RestockAlert[] = []
  const lowStockThreshold = profile.settings?.lowStockThreshold || 5

  for (const forecast of forecasts) {
    const needsRestock =
      forecast.daysUntilStockout <= 14 ||
      forecast.currentStock <= lowStockThreshold ||
      forecast.restockRecommendation > 0

    if (!needsRestock) continue

    const urgency = determineUrgency(
      forecast.daysUntilStockout,
      forecast.currentStock,
      lowStockThreshold
    )

    const leadTimeDays = 7
    const estimatedRestockDate = new Date(
      Date.now() + forecast.daysUntilStockout * 24 * 60 * 60 * 1000 - leadTimeDays * 24 * 60 * 60 * 1000
    )

    const reasoning = generateRestockReasoning(forecast, urgency, lowStockThreshold)

    alerts.push({
      productId: forecast.productId,
      productName: forecast.productName,
      currentStock: forecast.currentStock,
      daysUntilStockout: forecast.daysUntilStockout,
      recommendedOrderQuantity: forecast.restockRecommendation,
      urgency,
      estimatedRestockDate,
      reasoning,
    })
  }

  alerts.sort((a, b) => {
    const urgencyOrder = { critical: 0, high: 1, medium: 2, low: 3 }
    return urgencyOrder[a.urgency] - urgencyOrder[b.urgency]
  })

  return alerts
}

export async function generateAIInsights(
  forecasts: SalesForecast[],
  alerts: RestockAlert[],
  products: ProductWithStock[],
  orders: OrderWithItems[]
): Promise<string[]> {
  const forecastsSummary = JSON.stringify(
    forecasts.slice(0, 10).map((f) => ({
      product: f.productName,
      currentStock: f.currentStock,
      avgDailySales: f.averageDailySales.toFixed(2),
      daysUntilStockout: f.daysUntilStockout,
      trend: f.trend,
    }))
  )

  const alertsSummary = JSON.stringify(
    alerts.slice(0, 5).map((a) => ({
      product: a.productName,
      urgency: a.urgency,
      daysUntilStockout: a.daysUntilStockout,
    }))
  )

  const totalProducts = products.length
  const activeProducts = products.filter((p) => p.activo).length
  const recentOrders = orders.filter(
    (o) => new Date(o.created_at) >= new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
  ).length

  const promptText = `Analyze this inventory data and provide 3-5 actionable business insights.

Sales Forecasts Summary:
${forecastsSummary}

Restock Alerts:
${alertsSummary}

Recent Sales Performance:
- Total Products: ${totalProducts}
- Active Products: ${activeProducts}
- Recent Orders: ${recentOrders}

Provide insights as a JSON object with a single "insights" property containing an array of concise, actionable insight strings. Each insight should be 1-2 sentences. Focus on inventory optimization, sales opportunities, and risk mitigation.`

  try {
    const response = await window.spark.llm(promptText, 'gpt-4o-mini', true)
    const parsed = JSON.parse(response)
    return parsed.insights || []
  } catch (error) {
    console.error('Error generating AI insights:', error)
    return [
      'Monitor productos con menos de 7 días de stock disponible',
      'Considera aumentar pedidos para productos con tendencia creciente',
      'Revisa productos de movimiento lento para posibles promociones',
    ]
  }
}

function calculateProductSales(
  productId: number,
  orders: OrderWithItems[]
): { totalQuantity: number; totalRevenue: number; orderCount: number } {
  let totalQuantity = 0
  let totalRevenue = 0
  let orderCount = 0

  for (const order of orders) {
    for (const item of order.items) {
      if (item.product_id === productId && !item.es_regalo_promocion) {
        totalQuantity += item.cantidad
        totalRevenue += item.cantidad * item.precio_unitario
        orderCount++
      }
    }
  }

  return { totalQuantity, totalRevenue, orderCount }
}

function calculateTrend(
  recentDailySales: number,
  olderDailySales: number
): 'increasing' | 'stable' | 'decreasing' {
  if (olderDailySales === 0 && recentDailySales > 0) return 'increasing'
  if (recentDailySales === 0 && olderDailySales > 0) return 'decreasing'
  if (recentDailySales === 0 && olderDailySales === 0) return 'stable'

  const changePercent = ((recentDailySales - olderDailySales) / olderDailySales) * 100

  if (changePercent > 15) return 'increasing'
  if (changePercent < -15) return 'decreasing'
  return 'stable'
}

function calculateGrowthFactor(
  recentDailySales: number,
  olderDailySales: number,
  trend: 'increasing' | 'stable' | 'decreasing'
): number {
  if (trend === 'increasing') {
    const growthRate =
      olderDailySales > 0 ? (recentDailySales - olderDailySales) / olderDailySales : 0.2
    return 1 + Math.min(growthRate * 0.5, 0.3)
  }

  if (trend === 'decreasing') {
    const declineRate =
      olderDailySales > 0 ? (olderDailySales - recentDailySales) / olderDailySales : 0.2
    return 1 - Math.min(declineRate * 0.3, 0.2)
  }

  return 1
}

function calculateConfidence(recentOrderCount: number, olderOrderCount: number): number {
  const totalOrders = recentOrderCount + olderOrderCount

  if (totalOrders >= 20) return 0.95
  if (totalOrders >= 10) return 0.8
  if (totalOrders >= 5) return 0.65
  if (totalOrders >= 2) return 0.5
  return 0.3
}

function generateForecastingSummary(
  forecasts: SalesForecast[],
  products: ProductWithStock[]
): ForecastingSummary {
  const productsNeedingRestock = forecasts.filter(
    (f) => f.daysUntilStockout <= 14 || f.restockRecommendation > 0
  ).length

  const criticalStockAlerts = forecasts.filter(
    (f) => f.daysUntilStockout <= 7 && f.currentStock > 0
  ).length

  const estimatedRevenue7Days = forecasts.reduce((sum, f) => {
    const product = products.find((p) => p.id === f.productId)
    return sum + (product ? f.predictedSalesNext7Days * product.precio : 0)
  }, 0)

  const estimatedRevenue30Days = forecasts.reduce((sum, f) => {
    const product = products.find((p) => p.id === f.productId)
    return sum + (product ? f.predictedSalesNext30Days * product.precio : 0)
  }, 0)

  const topPerformingProducts = forecasts
    .filter((f) => f.averageDailySales >= 0.5 && f.trend === 'increasing')
    .slice(0, 5)
    .map((f) => f.productName)

  const slowMovingProducts = forecasts
    .filter((f) => f.averageDailySales < 0.1 && f.currentStock > 5)
    .slice(0, 5)
    .map((f) => f.productName)

  return {
    totalProducts: forecasts.length,
    productsNeedingRestock,
    criticalStockAlerts,
    estimatedRevenue7Days,
    estimatedRevenue30Days,
    topPerformingProducts,
    slowMovingProducts,
  }
}

function determineUrgency(
  daysUntilStockout: number,
  currentStock: number,
  lowStockThreshold: number
): 'critical' | 'high' | 'medium' | 'low' {
  if (daysUntilStockout <= 3 || currentStock === 0) return 'critical'
  if (daysUntilStockout <= 7 || currentStock <= lowStockThreshold / 2) return 'high'
  if (daysUntilStockout <= 14 || currentStock <= lowStockThreshold) return 'medium'
  return 'low'
}

function generateRestockReasoning(
  forecast: SalesForecast,
  urgency: string,
  lowStockThreshold: number
): string {
  const reasons: string[] = []

  if (forecast.currentStock === 0) {
    reasons.push('Sin stock disponible')
  } else if (forecast.currentStock <= lowStockThreshold) {
    reasons.push(`Stock bajo (${forecast.currentStock} unidades)`)
  }

  if (forecast.daysUntilStockout <= 7) {
    reasons.push(`Se agotará en ${forecast.daysUntilStockout} días`)
  }

  if (forecast.trend === 'increasing') {
    reasons.push('Tendencia de ventas en aumento')
  }

  if (forecast.averageDailySales > 1) {
    reasons.push(`Alta demanda (${forecast.averageDailySales.toFixed(1)} ventas/día)`)
  }

  return reasons.join('. ') || 'Reabastecimiento preventivo recomendado'
}
