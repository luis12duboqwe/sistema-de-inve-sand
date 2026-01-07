import { useState, useEffect, useCallback } from 'react'
import type { ProductWithStock, OrderWithItems, Profile, BusinessInsightRecommendation } from '@/lib/types'
import type { OptimizationAnalysis } from '@/lib/optimizationAnalytics'
import {
  calculateOptimizationScore,
  analyzePricing,
  analyzeInventory,
  analyzeCustomers,
  analyzeProductMix,
  analyzeOperations
} from '@/lib/optimizationAnalytics'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { buildBusinessInsightRecommendations } from '@/lib/businessInsightsFallback'

export function useOptimizationInsights(
  products: ProductWithStock[],
  orders: OrderWithItems[],
  profile: Profile | null,
  autoGenerate: boolean = false
) {
  const [analysis, setAnalysis] = useState<OptimizationAnalysis | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [aiInsights, setAiInsights] = useState<string[]>([])
  const [recommendationDetails, setRecommendationDetails] = useState<BusinessInsightRecommendation[]>([])
  const [insightsSource, setInsightsSource] = useState<'backend' | 'local'>('local')
  const [insightsError, setInsightsError] = useState<string | null>(null)

  // V2.0: Products are global, Orders filter by sales_profile_id
  const profileProducts = products.filter(p => p.activo)
  const profileOrders = orders.filter(o => 
    !profile || o.sales_profile_id === profile.id
  )

  const generateAnalysis = useCallback(async () => {
    if (isGenerating) return

    setIsGenerating(true)
    setInsightsError(null)

    try {
      const optimizationScore = calculateOptimizationScore(profileProducts, profileOrders)

      const pricingInsights = analyzePricing(profileProducts, profileOrders)
      const inventoryInsights = analyzeInventory(profileProducts, profileOrders)
      const customerInsights = analyzeCustomers(profileOrders)
      const productMixInsights = analyzeProductMix(profileProducts, profileOrders)
      const operationalInsights = analyzeOperations(profileProducts, profileOrders)

      const totalPotentialRevenue = pricingInsights.reduce((sum, i) => sum + i.potentialImpact, 0) +
                                   inventoryInsights.reduce((sum, i) => sum + i.impact, 0)

      const totalCostSavings = inventoryInsights
        .filter(i => i.type === 'overstock' || i.type === 'dead_stock')
        .reduce((sum, i) => sum + i.impact, 0)

      let analysisTimestamp = new Date()

      const newAnalysis: OptimizationAnalysis = {
        metrics: {
          optimizationScore,
          potentialRevenue: totalPotentialRevenue,
          costSavings: totalCostSavings,
          efficiencyGain: Math.round((100 - optimizationScore) * 0.5),
          lastAnalyzed: analysisTimestamp.toISOString()
        },
        pricing: {
          insights: pricingInsights,
          summary: generatePricingSummary(pricingInsights)
        },
        inventory: {
          insights: inventoryInsights,
          summary: generateInventorySummary(inventoryInsights)
        },
        customer: {
          insights: customerInsights,
          summary: generateCustomerSummary(customerInsights)
        },
        productMix: {
          insights: productMixInsights,
          summary: generateProductMixSummary(productMixInsights)
        },
        operations: {
          insights: operationalInsights,
          summary: generateOperationsSummary(operationalInsights)
        },
        aiRecommendations: []
      }

      let aiRecommendations: string[] = []
      let detailedRecommendations: BusinessInsightRecommendation[] = []
      let recommendationSource: 'backend' | 'local' = 'local'

      try {
        const insightsResponse = await inventoryServiceInstance.generateBusinessInsights({
          sales_profile_slug: profile?.slug || undefined,
          sales_profile_id: profile?.id,
          days: 45,
          use_cache: true,
          force_refresh: Boolean(analysis)
        })

        if (insightsResponse) {
          if (insightsResponse.recommendations?.length) {
            detailedRecommendations = insightsResponse.recommendations
            aiRecommendations = insightsResponse.recommendations
              .map(rec => rec.action || rec.title)
              .filter(Boolean)
            recommendationSource = aiRecommendations.length > 0 ? 'backend' : 'local'
          }

          if (insightsResponse.generated_at) {
            analysisTimestamp = new Date(insightsResponse.generated_at)
            newAnalysis.metrics.lastAnalyzed = analysisTimestamp.toISOString()
          }
        }
      } catch (error) {
        console.error('Error fetching backend insights:', error)
        setInsightsError(error instanceof Error ? error.message : 'No fue posible generar insights con IA')
      }

      if (aiRecommendations.length === 0) {
        const fallbackRecommendations = buildBusinessInsightRecommendations(
          pricingInsights,
          inventoryInsights,
          customerInsights
        )

        detailedRecommendations = fallbackRecommendations
        aiRecommendations = fallbackRecommendations
          .map(rec => rec.action || rec.title)
          .filter(Boolean)
        recommendationSource = 'local'
      }

      if (aiRecommendations.length === 0) {
        aiRecommendations = [
          'Enfócate en mantener stock óptimo de tus productos más rentables para maximizar ingresos.',
          'Revisa los productos con baja rotación y considera estrategias de liquidación para liberar capital.',
          'Identifica y retén a tus clientes de alto valor con programas de lealtad personalizados.',
          'Optimiza precios basándote en la demanda y disponibilidad de cada producto.',
          'Automatiza alertas de reorden para reducir quiebres de stock en productos críticos.'
        ]
      }

      newAnalysis.aiRecommendations = aiRecommendations

      setAnalysis(newAnalysis)
      setAiInsights(aiRecommendations)
      setRecommendationDetails(detailedRecommendations)
      setInsightsSource(recommendationSource)
      setLastUpdated(analysisTimestamp)
    } catch (error) {
      console.error('Error generating optimization analysis:', error)
      setInsightsError(error instanceof Error ? error.message : 'No fue posible generar insights con IA')
    } finally {
      setIsGenerating(false)
    }
  }, [analysis, isGenerating, profileProducts, profileOrders, profile])

  useEffect(() => {
    if (autoGenerate && profileProducts.length > 0 && !analysis) {
      generateAnalysis()
    }
  }, [autoGenerate, profileProducts.length, analysis, generateAnalysis])

  return {
    analysis,
    isGenerating,
    lastUpdated,
    aiInsights,
    recommendationDetails,
    insightsSource,
    insightsError,
    generateAnalysis
  }
}

interface PricingInsightSummary {
  type: string
  potentialImpact: number
}

interface InventoryInsightSummary {
  type: string
  impact: number
}

function generatePricingSummary(insights: PricingInsightSummary[]): string {
  if (insights.length === 0) return 'Sin oportunidades de optimización de precios detectadas.'
  
  const underpriced = insights.filter(i => i.type === 'underpriced').length
  const overpriced = insights.filter(i => i.type === 'overpriced').length
  const totalImpact = insights.reduce((sum, i) => sum + i.potentialImpact, 0)
  
  if (underpriced > 0 && overpriced === 0) {
    return `${underpriced} productos con potencial de incremento de precio podrían generar $${totalImpact} adicionales en ingresos.`
  }
  if (overpriced > 0 && underpriced === 0) {
    return `${overpriced} productos sobrevaluados están limitando ventas. Ajustes de precio podrían acelerar rotación.`
  }
  return `Oportunidades mixtas: ${underpriced} productos pueden aumentar precio, ${overpriced} requieren reducción para optimizar rotación.`
}

function generateInventorySummary(insights: InventoryInsightSummary[]): string {
  if (insights.length === 0) return 'Niveles de inventario están balanceados.'
  
  const overstock = insights.filter(i => i.type === 'overstock').length
  const understock = insights.filter(i => i.type === 'understock').length
  const deadStock = insights.filter(i => i.type === 'dead_stock').length
  
  const parts: string[] = []
  if (overstock > 0) parts.push(`${overstock} productos con exceso de inventario`)
  if (understock > 0) parts.push(`${understock} productos con stock insuficiente`)
  if (deadStock > 0) parts.push(`${deadStock} productos sin movimiento`)
  
  return parts.length > 0 ? parts.join(', ') + '. Optimización requerida para mejorar capital de trabajo.' : 'Niveles de inventario están balanceados.'
}

interface CustomerInsightSummary {
  type: string
}

interface ProductMixInsightSummary {
  type: string
}

interface OperationalInsightSummary {
  type: string
  reasoning: string
  action: string
}

function generateCustomerSummary(insights: CustomerInsightSummary[]): string {
  if (insights.length === 0) return 'Datos insuficientes para análisis de clientes.'
  
  const highValue = insights.filter(i => i.type === 'high_value').length
  const atRisk = insights.filter(i => i.type === 'at_risk').length
  
  if (highValue > 0 && atRisk === 0) {
    return `${highValue} clientes VIP identificados. Implementa programas de retención para maximizar valor de vida del cliente.`
  }
  if (atRisk > 0) {
    return `${atRisk} clientes recurrentes en riesgo de pérdida. Acciones inmediatas de reactivación necesarias.`
  }
  return `Base de clientes saludable con ${highValue} compradores de alto valor.`
}

function generateProductMixSummary(insights: ProductMixInsightSummary[]): string {
  if (insights.length === 0) return 'Mix de productos requiere más datos históricos para análisis.'
  
  const bestSellers = insights.filter(i => i.type === 'best_seller')
  const poorPerformers = insights.filter(i => i.type === 'poor_performer')
  
  if (bestSellers.length > 0) {
    return `Productos estrella identificados generando la mayoría de ingresos. ${poorPerformers.length > 0 ? `${poorPerformers.length} productos con bajo rendimiento requieren atención.` : 'Continúa enfoque en estos ganadores.'}`
  }
  return 'Diversifica el catálogo para reducir dependencia en pocos productos.'
}

function generateOperationsSummary(insights: OperationalInsightSummary[]): string {
  if (insights.length === 0) return 'Operaciones funcionando eficientemente.'
  
  const processInsights = insights.filter(i => i.type === 'process').length
  const automationInsights = insights.filter(i => i.type === 'automation').length
  
  if (automationInsights > 0) {
    return `${automationInsights} oportunidades de automatización detectadas. Implementar sistemas automáticos podría reducir carga operativa.`
  }
  if (processInsights > 0) {
    return `${processInsights} cuellos de botella en procesos identificados. Optimización de workflow recomendada.`
  }
  return 'Identifica patrones de demanda para optimizar asignación de recursos.'
}
