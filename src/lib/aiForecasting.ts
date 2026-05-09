import { ProductWithStock, OrderWithItems, Profile } from './types'
import { isFinalSaleStatus } from './orderStatus'

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
  urgency: 'critical' | 'high' | 'medium' | 'low'
  reasoning: string
  recommendedOrderQuantity: number
  estimatedRestockDate: Date
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

export async function generateAIForecasts(
  products: ProductWithStock[],
  orders: OrderWithItems[]
): Promise<{ forecasts: SalesForecast[]; summary: ForecastingSummary }> {
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
  const sixtyDaysAgo = new Date()
  sixtyDaysAgo.setDate(sixtyDaysAgo.getDate() - 60)

  const recentOrders = orders.filter(
    (o) => new Date(o.created_at) >= thirtyDaysAgo && isFinalSaleStatus(o.estado)
  )
  const olderOrders = orders.filter(
    (o) =>
      new Date(o.created_at) >= sixtyDaysAgo &&
      new Date(o.created_at) < thirtyDaysAgo &&
      isFinalSaleStatus(o.estado)
  )

  const forecasts: SalesForecast[] = []

  for (const product of products.filter((p) => p.activo)) {
    const recentSales = calculateProductSales(product.id, recentOrders)
    const olderSales = calculateProductSales(product.id, olderOrders)

    const recentDailySales = recentSales.totalQuantity / 30
    const olderDailySales = olderSales.totalQuantity / 30

    const trend = calculateTrend(recentDailySales, olderDailySales)
    const growthFactor = calculateGrowthFactor(recentDailySales, olderDailySales, trend)

    const predictedDailySales = recentDailySales * growthFactor
    const predictedSalesNext7Days = Math.round(predictedDailySales * 7)
    const predictedSalesNext30Days = Math.round(predictedDailySales * 30)

    const daysUntilStockout =
      predictedDailySales > 0
        ? Math.round(product.stock_disponible / predictedDailySales)
        : 999

    const restockRecommendation = Math.max(
      0,
      predictedSalesNext30Days - product.stock_disponible
    )

    const confidence = calculateConfidence(recentSales.orderCount, olderSales.orderCount)

    forecasts.push({
      productId: product.id,
      productName: `${product.marca} ${product.modelo}`,
      currentStock: product.stock_disponible,
      averageDailySales: recentDailySales,
      predictedSalesNext7Days,
      predictedSalesNext30Days,
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
  const lowStockThreshold = profile.settings?.lowStockThreshold || 5
  const alerts: RestockAlert[] = []

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

    const recommendedOrderQuantity = Math.max(
      forecast.restockRecommendation,
      Math.ceil(forecast.averageDailySales * 30)
    )

    const leadTimeDays = 7
    const estimatedRestockDate = new Date()
    estimatedRestockDate.setDate(estimatedRestockDate.getDate() + leadTimeDays)

    const reasoning = generateRestockReasoning(forecast, urgency, lowStockThreshold)

    alerts.push({
      productId: forecast.productId,
      productName: forecast.productName,
      currentStock: forecast.currentStock,
      daysUntilStockout: forecast.daysUntilStockout,
      urgency,
      reasoning,
      recommendedOrderQuantity,
      estimatedRestockDate,
    })
  }

  const urgencyOrder = { critical: 0, high: 1, medium: 2, low: 3 }
  alerts.sort((a, b) => urgencyOrder[a.urgency] - urgencyOrder[b.urgency])

  return alerts
}

export async function generateAIInsights(
  forecasts: SalesForecast[],
  alerts: RestockAlert[],
  products: ProductWithStock[]
): Promise<string[]> {
  const forecastData = forecasts.slice(0, 10).map((f) => ({
    product: f.productName,
    currentStock: f.currentStock,
    daysUntilStockout: f.daysUntilStockout,
    trend: f.trend,
    dailySales: f.averageDailySales.toFixed(2),
  }))

  const alertData = alerts.slice(0, 5).map((a) => ({
    product: a.productName,
    urgency: a.urgency,
    recommendedOrder: a.recommendedOrderQuantity,
  }))

  const totalProducts = products.filter((p) => p.activo).length
  const criticalAlerts = alerts.filter((a) => a.urgency === 'critical').length

  const prompt = spark.llmPrompt`Actúa como analista de inventario experto. Analiza estos datos de pronóstico de ventas y genera exactamente 5 insights estratégicos:

Forecasts (Top 10):
${JSON.stringify(forecastData, null, 2)}

Restock Alerts:
${JSON.stringify(alertData, null, 2)}

Métricas:
- Total Products: ${totalProducts}
- Critical Alerts: ${criticalAlerts}

Genera SOLO un objeto JSON con el formato:
{
  "insights": ["insight 1", "insight 2", "insight 3", "insight 4", "insight 5"]
}

Cada insight debe:
1. Ser específico y accionable
2. Basarse en los datos proporcionados
3. Incluir números concretos
4. Ser conciso (máximo 2 líneas)`

  try {
    const response = await spark.llm(prompt, 'gpt-4o', true)
    const parsed = JSON.parse(response)
    return parsed.insights || []
  } catch (error) {
    console.error('Error generating AI insights:', error)
    return [
      'Prioriza reabastecer productos con alertas críticas para evitar quiebres de stock',
      'Considera aumentar pedidos para productos con tendencia creciente',
      'Revisa productos de movimiento lento para posibles promociones o descontinuación',
      'Implementa alertas automáticas para mantener stock óptimo de tus top performers',
      'Analiza patrones de demanda semanales para optimizar niveles de inventario',
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

export function generateForecastingSummary(
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
