import { ProductWithStock, OrderWithItems, Profile } from './types'

  productName: string
  productId: number
  productName: string
  currentStock: number
  averageDailySales: number
  predictedSalesNext7Days: number
  predictedSalesNext30Days: number
  trend: 'increasing' | 'st
  restockRecommendation: number
  confidence: number
  trend: 'increasing' | 'stable' | 'decreasing'
}

export interface RestockAlert {
  productId: number
  productName: string
  currentStock: number
  daysUntilStockout: number
}
export interface ForecastingSummary {
  productsNeedingRestock: nu
  estimatedRevenue7
 

export async function generateAIForec
  orders: OrderWithItem
): Promise<{ forecasts: SalesFor
  const thirtyDaysAgo = new D

    (o) => new Date(o.created_at

    (o) =>
 

  const forecasts: SalesForecast[] = []
  for (const product of product

    const olderSal
    const recentDailySales = recentSales.totalQuantity / 30





      predictedDailySales > 0
   

      0,
    )
    const confidence = calculateConfidence(recen
    forecasts.push({
      productName: `${product.
   

      restockRecommendation,

  }
  forecasts.sort((a, b) => a.days

  return { forecasts, summary }


): Promise<RestockAlert[]> {
  const lowStockThreshold = profile.settings?.lowStockThr

      forecast.daysUntilStockout <= 14 ||

    if (!needsRestock) continue

      forecast.currentStock,
    )
    const leadTimeDays = 7



      productId: forecast.productId,
      current

      estimatedRestockDate,
    })

    const urgencyOrder = { critical: 0, high: 1, medium: 2, low: 3 
  })



  products: ProductW
): Promise<string[]> {
    forecasts.slice(0, 10).map((f) => ({
      currentStock: f.currentStock,
      daysUntilStockout: f.daysUntilStocko
    }))

    alerts.slice(0, 5).m
      urgency: a.urgency,
    }))

  cons
   



Restock Alerts:

- Total Products: ${totalProduc
-

  try {
    const parsed = JSON.parse
  } catch (error) 
    return [
      'Considera aumentar pedidos p
    ]

function calculateProductSales(
  orders: OrderWithItems
  let totalQuantity = 0
  let orderCount = 0
  for (const order of orders) {

        totalRevenue += item.ca

  }
  return { totalQuantity, totalRe

  recentDailySales: num
): 'i



  if (changePercent < -15) return 'decreasing'
}

  olderDailySales: number,

    const growthR
    return 1 + Math.min(growthRate *

    const declineRate =
    return 1 - Math.min(declineRate * 0.3, 0.2)

}
function calculateConfidenc

  if (
  i

function generateForecast
  products: ProductWithStock[]
  const productsNeedingRestock = forecasts.filter(
  ).

  ).length
 


    const product = products.
  }, 0)
  const topPerformingProducts =
    .slice(0, 5)

    .filter((f) => f.averageDailySales < 0.1 && f.currentStock > 5)

  return {
    productsNeedi
    estimatedRevenue7Days,
    topPerformingProducts,
  }

  daysUntilStockout: number,
  lowStockThreshold: 
  if (d
  if

function genera
  urgency: string
): string {

    reasons.push('Sin sto
    reasons.push(`Stock bajo (${forecast.curr

    

    reasons.push('Tendenc

    reasons.push(`Alta demanda (${forecast.averageDailySales.












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
