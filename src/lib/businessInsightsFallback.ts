import type { BusinessInsightRecommendation } from './types'
import type { PricingInsight, InventoryInsight, CustomerInsight } from './optimizationAnalytics'

export function buildBusinessInsightRecommendations(
  pricingInsights: PricingInsight[],
  inventoryInsights: InventoryInsight[],
  customerInsights: CustomerInsight[]
): BusinessInsightRecommendation[] {
  const recommendations: BusinessInsightRecommendation[] = []

  const topPricing = pricingInsights[0]
  if (topPricing) {
    recommendations.push({
      title: `Optimiza precio de ${topPricing.productName}`,
      action: `${topPricing.reasoning} Ajusta hacia ${topPricing.suggestedPrice} para capturar ~$${topPricing.potentialImpact}.`,
      impact: `$${topPricing.potentialImpact}`,
      category: 'precio',
      priority: topPricing.type === 'underpriced' ? 'alta' : 'media'
    })
  }

  const criticalUnderstock = inventoryInsights.find(i => i.type === 'understock')
  if (criticalUnderstock) {
    recommendations.push({
      title: `Evita quiebre en ${criticalUnderstock.productName}`,
      action: `${criticalUnderstock.reasoning} ${criticalUnderstock.action}.`,
      impact: `$${criticalUnderstock.impact}`,
      category: 'inventario',
      priority: 'critica'
    })
  }

  const heavyOverstock = inventoryInsights.find(i => i.type === 'overstock' || i.type === 'dead_stock')
  if (heavyOverstock) {
    recommendations.push({
      title: `Liquida exceso de ${heavyOverstock.productName}`,
      action: `${heavyOverstock.reasoning} ${heavyOverstock.action}.`,
      impact: `$${heavyOverstock.impact}`,
      category: 'inventario',
      priority: 'alta'
    })
  }

  const vipCustomer = customerInsights.find(i => i.type === 'high_value')
  if (vipCustomer) {
    recommendations.push({
      title: `Programa VIP para ${vipCustomer.customerName || 'clientes clave'}`,
      action: `${vipCustomer.reasoning} ${vipCustomer.action}.`,
      impact: 'Mayor retención y ticket promedio',
      category: 'clientes',
      priority: 'media'
    })
  }

  const atRiskCustomer = customerInsights.find(i => i.type === 'at_risk')
  if (atRiskCustomer) {
    recommendations.push({
      title: `Recupera cliente en riesgo (${atRiskCustomer.customerName || atRiskCustomer.customerPhone || 'sin nombre'})`,
      action: `${atRiskCustomer.reasoning} ${atRiskCustomer.action}.`,
      impact: 'Protege ingresos recurrentes',
      category: 'clientes',
      priority: 'alta'
    })
  }

  while (recommendations.length < 5) {
    recommendations.push({
      title: 'Optimiza rotación de inventario',
      action: 'Prioriza reorden para top sellers y liquida productos sin movimiento con bundles o descuentos escalonados.',
      impact: 'Mejor uso de capital',
      category: 'operaciones',
      priority: 'media'
    })
  }

  return recommendations.slice(0, 5)
}
