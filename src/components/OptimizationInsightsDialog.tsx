import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { motion } from 'framer-motion'
import { 
  Sparkle, 
  TrendUp, 
  CurrencyDollar, 
  Package, 
  Users, 
  ChartBar,
  Lightbulb,
  ArrowRight,
  Check,
  Warning,
  Gear
} from '@phosphor-icons/react'
import type { ProductWithStock, OrderWithItems, Profile } from '@/lib/types'
import { useOptimizationInsights } from '@/hooks/use-optimization-insights'

interface OptimizationInsightsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  products: ProductWithStock[]
  orders: OrderWithItems[]
  profile: Profile | null
  onProductClick?: (product: ProductWithStock) => void
}

export function OptimizationInsightsDialog({
  open,
  onOpenChange,
  products,
  orders,
  profile,
  onProductClick
}: OptimizationInsightsDialogProps) {
  const { analysis, isGenerating, lastUpdated, generateAnalysis } = useOptimizationInsights(
    products,
    orders,
    profile,
    false
  )

  const handleGenerate = () => {
    generateAnalysis()
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success'
    if (score >= 60) return 'text-warning'
    return 'text-destructive'
  }

  const getScoreLabel = (score: number) => {
    if (score >= 80) return 'Excelente'
    if (score >= 60) return 'Bueno'
    if (score >= 40) return 'Regular'
    return 'Requiere atención'
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-7xl h-[90vh] max-h-[90vh] overflow-hidden flex flex-col p-0">
        <DialogHeader className="px-4 sm:px-6 pt-4 sm:pt-6 pb-4 border-b border-border flex-shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center flex-shrink-0">
                <Lightbulb size={20} className="sm:size-6 text-primary-foreground" weight="duotone" />
              </div>
              <div className="min-w-0 flex-1">
                <DialogTitle className="text-lg sm:text-2xl font-bold truncate">
                  Insights de Optimización
                </DialogTitle>
                <DialogDescription className="mt-1 text-xs sm:text-sm truncate">
                  Análisis multidimensional impulsado por IA
                </DialogDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {lastUpdated && (
                <span className="text-xs text-muted-foreground">
                  Actualizado {lastUpdated.toLocaleTimeString()}
                </span>
              )}
              <Button
                onClick={handleGenerate}
                disabled={isGenerating}
                size="sm"
                className="gap-2"
              >
                <Sparkle size={16} weight="duotone" />
                {isGenerating ? 'Analizando...' : 'Generar Análisis'}
              </Button>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-6 pb-6">
          {!analysis && !isGenerating && (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="w-20 h-20 rounded-full bg-accent/20 flex items-center justify-center mb-6">
                <Lightbulb size={40} className="text-accent" weight="duotone" />
              </div>
              <h3 className="text-xl font-semibold mb-2">
                Descubre Oportunidades de Optimización
              </h3>
              <p className="text-muted-foreground mb-6 max-w-md">
                El análisis de IA explorará 5 dimensiones clave de tu negocio para identificar
                oportunidades concretas de mejora en ingresos, costos y eficiencia.
              </p>
              <Button onClick={handleGenerate} size="lg" className="gap-2">
                <Sparkle size={20} weight="duotone" />
                Iniciar Análisis
              </Button>
            </div>
          )}

          {isGenerating && (
            <div className="flex flex-col items-center justify-center h-full">
              <motion.div
                animate={{ 
                  scale: [1, 1.2, 1],
                  rotate: [0, 180, 360]
                }}
                transition={{ 
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <Sparkle size={64} className="text-primary mb-6" weight="duotone" />
              </motion.div>
              <h3 className="text-xl font-semibold mb-2">Analizando datos del negocio...</h3>
              <p className="text-muted-foreground">
                Explorando oportunidades de optimización con IA
              </p>
            </div>
          )}

          {analysis && !isGenerating && (
            <div className="space-y-6 pt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-6 bg-gradient-to-br from-primary/10 to-accent/5 border-primary/20">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-muted-foreground">
                      Score de Optimización
                    </span>
                    <Gear size={20} className="text-primary" weight="duotone" />
                  </div>
                  <div className={`text-4xl font-bold ${getScoreColor(analysis.metrics.optimizationScore)} mb-2`}>
                    {analysis.metrics.optimizationScore}
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    {getScoreLabel(analysis.metrics.optimizationScore)}
                  </p>
                  <Progress value={analysis.metrics.optimizationScore} className="h-2" />
                </Card>

                <Card className="p-6 bg-gradient-to-br from-success/10 to-success/5 border-success/20">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-muted-foreground">
                      Ingresos Potenciales
                    </span>
                    <TrendUp size={20} className="text-success" weight="duotone" />
                  </div>
                  <div className="text-3xl font-bold text-success mb-2">
                    ${analysis.metrics.potentialRevenue.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Oportunidades identificadas
                  </p>
                </Card>

                <Card className="p-6 bg-gradient-to-br from-warning/10 to-warning/5 border-warning/20">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-muted-foreground">
                      Ahorro en Costos
                    </span>
                    <CurrencyDollar size={20} className="text-warning" weight="duotone" />
                  </div>
                  <div className="text-3xl font-bold text-warning mb-2">
                    ${analysis.metrics.costSavings.toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Capital a optimizar
                  </p>
                </Card>

                <Card className="p-6 bg-gradient-to-br from-accent/10 to-accent/5 border-accent/20">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-muted-foreground">
                      Ganancia en Eficiencia
                    </span>
                    <Sparkle size={20} className="text-accent" weight="duotone" />
                  </div>
                  <div className="text-3xl font-bold text-accent mb-2">
                    {analysis.metrics.efficiencyGain}%
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Mejora proyectada
                  </p>
                </Card>
              </div>

              {analysis.aiRecommendations.length > 0 && (
                <Card className="p-6 bg-gradient-to-br from-primary/5 to-accent/5">
                  <div className="flex items-center gap-2 mb-4">
                    <Sparkle size={24} className="text-primary" weight="duotone" />
                    <h3 className="text-lg font-semibold">Recomendaciones Estratégicas de IA</h3>
                  </div>
                  <div className="space-y-3">
                    {analysis.aiRecommendations.map((rec, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="flex gap-3 p-4 rounded-lg bg-background/50 border border-border/50"
                      >
                        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-primary text-sm font-bold">
                          {idx + 1}
                        </div>
                        <p className="text-sm flex-1">{rec}</p>
                      </motion.div>
                    ))}
                  </div>
                </Card>
              )}

              <Tabs defaultValue="pricing" className="w-full">
                <TabsList className="grid w-full grid-cols-5">
                  <TabsTrigger value="pricing" className="gap-2">
                    <CurrencyDollar size={16} />
                    <span className="hidden sm:inline">Precios</span>
                  </TabsTrigger>
                  <TabsTrigger value="inventory" className="gap-2">
                    <Package size={16} />
                    <span className="hidden sm:inline">Inventario</span>
                  </TabsTrigger>
                  <TabsTrigger value="customers" className="gap-2">
                    <Users size={16} />
                    <span className="hidden sm:inline">Clientes</span>
                  </TabsTrigger>
                  <TabsTrigger value="product-mix" className="gap-2">
                    <ChartBar size={16} />
                    <span className="hidden sm:inline">Mix</span>
                  </TabsTrigger>
                  <TabsTrigger value="operations" className="gap-2">
                    <Gear size={16} />
                    <span className="hidden sm:inline">Operaciones</span>
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="pricing" className="mt-6 space-y-4">
                  <div className="flex items-start gap-4 p-4 rounded-lg bg-accent/10">
                    <Lightbulb size={24} className="text-accent flex-shrink-0 mt-0.5" weight="duotone" />
                    <div>
                      <h4 className="font-semibold mb-1">Análisis de Precios</h4>
                      <p className="text-sm text-muted-foreground">{analysis.pricing.summary}</p>
                    </div>
                  </div>

                  {analysis.pricing.insights.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Check size={48} className="mx-auto mb-2 opacity-50" />
                      <p>No se detectaron oportunidades de optimización de precios</p>
                    </div>
                  ) : (
                    <div className="grid gap-4">
                      {analysis.pricing.insights.map((insight, idx) => {
                        const product = products.find(p => p.id === insight.productId)
                        return (
                          <Card key={idx} className="p-5 hover:shadow-md transition-shadow">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <h4 className="font-semibold">{insight.productName}</h4>
                                  <Badge variant={insight.type === 'underpriced' ? 'default' : 'secondary'}>
                                    {insight.type === 'underpriced' ? 'Subvalorado' : 'Sobrevalorado'}
                                  </Badge>
                                  <Badge variant="outline" className="text-xs">
                                    {Math.round(insight.confidence * 100)}% confianza
                                  </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground mb-3">
                                  {insight.reasoning}
                                </p>
                                <div className="flex items-center gap-4 text-sm">
                                  <div>
                                    <span className="text-muted-foreground">Actual: </span>
                                    <span className="font-semibold">${insight.currentPrice}</span>
                                  </div>
                                  <ArrowRight size={16} className="text-muted-foreground" />
                                  <div>
                                    <span className="text-muted-foreground">Sugerido: </span>
                                    <span className="font-semibold text-primary">${insight.suggestedPrice}</span>
                                  </div>
                                  <Separator orientation="vertical" className="h-4" />
                                  <div className="flex items-center gap-1 text-success">
                                    <TrendUp size={16} />
                                    <span className="font-semibold">+${insight.potentialImpact}</span>
                                  </div>
                                </div>
                              </div>
                              {product && onProductClick && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => onProductClick(product)}
                                >
                                  Editar
                                </Button>
                              )}
                            </div>
                          </Card>
                        )
                      })}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="inventory" className="mt-6 space-y-4">
                  <div className="flex items-start gap-4 p-4 rounded-lg bg-accent/10">
                    <Lightbulb size={24} className="text-accent flex-shrink-0 mt-0.5" weight="duotone" />
                    <div>
                      <h4 className="font-semibold mb-1">Análisis de Inventario</h4>
                      <p className="text-sm text-muted-foreground">{analysis.inventory.summary}</p>
                    </div>
                  </div>

                  {analysis.inventory.insights.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Check size={48} className="mx-auto mb-2 opacity-50" />
                      <p>Niveles de inventario óptimos</p>
                    </div>
                  ) : (
                    <div className="grid gap-4">
                      {analysis.inventory.insights.map((insight, idx) => {
                        const product = products.find(p => p.id === insight.productId)
                        const typeColors = {
                          overstock: 'warning',
                          understock: 'destructive',
                          dead_stock: 'secondary',
                          fast_mover: 'default',
                          seasonal: 'default'
                        }
                        const typeLabels = {
                          overstock: 'Exceso',
                          understock: 'Insuficiente',
                          dead_stock: 'Sin movimiento',
                          fast_mover: 'Alta rotación',
                          seasonal: 'Estacional'
                        }
                        return (
                          <Card key={idx} className="p-5 hover:shadow-md transition-shadow">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <h4 className="font-semibold">{insight.productName}</h4>
                                  <Badge variant={typeColors[insight.type] as any}>
                                    {typeLabels[insight.type]}
                                  </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground mb-3">
                                  {insight.reasoning}
                                </p>
                                <div className="flex items-start gap-2 p-3 rounded bg-accent/5 mb-3">
                                  <ArrowRight size={16} className="text-accent mt-0.5 flex-shrink-0" />
                                  <p className="text-sm font-medium">{insight.action}</p>
                                </div>
                                <div className="flex items-center gap-4 text-sm">
                                  <div>
                                    <span className="text-muted-foreground">Stock actual: </span>
                                    <span className="font-semibold">{insight.currentStock}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Óptimo: </span>
                                    <span className="font-semibold text-primary">{insight.optimalStock}</span>
                                  </div>
                                  {insight.impact > 0 && (
                                    <>
                                      <Separator orientation="vertical" className="h-4" />
                                      <div className="flex items-center gap-1 text-success">
                                        <CurrencyDollar size={16} />
                                        <span className="font-semibold">${insight.impact}</span>
                                      </div>
                                    </>
                                  )}
                                </div>
                              </div>
                              {product && onProductClick && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => onProductClick(product)}
                                >
                                  Ver
                                </Button>
                              )}
                            </div>
                          </Card>
                        )
                      })}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="customers" className="mt-6 space-y-4">
                  <div className="flex items-start gap-4 p-4 rounded-lg bg-accent/10">
                    <Lightbulb size={24} className="text-accent flex-shrink-0 mt-0.5" weight="duotone" />
                    <div>
                      <h4 className="font-semibold mb-1">Análisis de Clientes</h4>
                      <p className="text-sm text-muted-foreground">{analysis.customer.summary}</p>
                    </div>
                  </div>

                  {analysis.customer.insights.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Warning size={48} className="mx-auto mb-2 opacity-50" />
                      <p>Datos insuficientes para análisis de clientes</p>
                    </div>
                  ) : (
                    <div className="grid gap-4">
                      {analysis.customer.insights.map((insight, idx) => {
                        const typeColors = {
                          high_value: 'default',
                          at_risk: 'destructive',
                          growth_opportunity: 'default',
                          segment: 'secondary'
                        }
                        const typeLabels = {
                          high_value: 'VIP',
                          at_risk: 'En riesgo',
                          growth_opportunity: 'Oportunidad',
                          segment: 'Segmento'
                        }
                        return (
                          <Card key={idx} className="p-5">
                            <div className="flex items-start gap-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  {insight.customerName && (
                                    <h4 className="font-semibold">{insight.customerName}</h4>
                                  )}
                                  <Badge variant={typeColors[insight.type] as any}>
                                    {typeLabels[insight.type]}
                                  </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground mb-3">
                                  {insight.reasoning}
                                </p>
                                <div className="flex items-start gap-2 p-3 rounded bg-accent/5 mb-3">
                                  <ArrowRight size={16} className="text-accent mt-0.5 flex-shrink-0" />
                                  <p className="text-sm font-medium">{insight.action}</p>
                                </div>
                                <div className="text-sm">
                                  <span className="text-muted-foreground">{insight.metric}: </span>
                                  <span className="font-semibold">
                                    {typeof insight.value === 'number' && insight.metric.includes('Gastado') 
                                      ? `$${insight.value.toLocaleString()}` 
                                      : insight.value}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </Card>
                        )
                      })}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="product-mix" className="mt-6 space-y-4">
                  <div className="flex items-start gap-4 p-4 rounded-lg bg-accent/10">
                    <Lightbulb size={24} className="text-accent flex-shrink-0 mt-0.5" weight="duotone" />
                    <div>
                      <h4 className="font-semibold mb-1">Análisis de Mix de Productos</h4>
                      <p className="text-sm text-muted-foreground">{analysis.productMix.summary}</p>
                    </div>
                  </div>

                  {analysis.productMix.insights.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Warning size={48} className="mx-auto mb-2 opacity-50" />
                      <p>Se necesitan más datos históricos para el análisis</p>
                    </div>
                  ) : (
                    <div className="grid gap-4">
                      {analysis.productMix.insights.map((insight, idx) => {
                        const typeColors = {
                          best_seller: 'default',
                          poor_performer: 'destructive',
                          bundle_opportunity: 'default',
                          category_trend: 'secondary'
                        }
                        const typeLabels = {
                          best_seller: 'Estrella',
                          poor_performer: 'Bajo rendimiento',
                          bundle_opportunity: 'Bundle',
                          category_trend: 'Tendencia'
                        }
                        return (
                          <Card key={idx} className="p-5">
                            <div className="flex flex-col gap-3">
                              <div className="flex items-center gap-2">
                                <Badge variant={typeColors[insight.type] as any}>
                                  {typeLabels[insight.type]}
                                </Badge>
                                <span className="text-sm font-medium text-muted-foreground">
                                  {insight.productNames.length} {insight.productNames.length === 1 ? 'producto' : 'productos'}
                                </span>
                              </div>
                              <p className="text-sm text-muted-foreground">
                                {insight.reasoning}
                              </p>
                              <div className="flex items-start gap-2 p-3 rounded bg-accent/5">
                                <ArrowRight size={16} className="text-accent mt-0.5 flex-shrink-0" />
                                <p className="text-sm font-medium">{insight.action}</p>
                              </div>
                              <div className="flex items-center gap-4 text-sm">
                                <div>
                                  <span className="text-muted-foreground">{insight.metric}: </span>
                                  <span className="font-semibold">
                                    {insight.metric.includes('Ingresos') || insight.metric.includes('líder')
                                      ? `$${insight.value.toLocaleString()}`
                                      : insight.value}
                                  </span>
                                </div>
                                {insight.impact > 0 && (
                                  <>
                                    <Separator orientation="vertical" className="h-4" />
                                    <div className="flex items-center gap-1 text-success">
                                      <TrendUp size={16} />
                                      <span className="font-semibold">+${insight.impact.toLocaleString()}</span>
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          </Card>
                        )
                      })}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="operations" className="mt-6 space-y-4">
                  <div className="flex items-start gap-4 p-4 rounded-lg bg-accent/10">
                    <Lightbulb size={24} className="text-accent flex-shrink-0 mt-0.5" weight="duotone" />
                    <div>
                      <h4 className="font-semibold mb-1">Análisis Operacional</h4>
                      <p className="text-sm text-muted-foreground">{analysis.operations.summary}</p>
                    </div>
                  </div>

                  {analysis.operations.insights.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Check size={48} className="mx-auto mb-2 opacity-50" />
                      <p>Operaciones funcionando eficientemente</p>
                    </div>
                  ) : (
                    <div className="grid gap-4">
                      {analysis.operations.insights.map((insight, idx) => {
                        const typeIcons = {
                          process: Gear,
                          timing: TrendUp,
                          resource: Package,
                          automation: Sparkle
                        }
                        const Icon = typeIcons[insight.type]
                        return (
                          <Card key={idx} className="p-5">
                            <div className="flex items-start gap-4">
                              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                                <Icon size={20} className="text-primary" weight="duotone" />
                              </div>
                              <div className="flex-1">
                                <h4 className="font-semibold mb-1">{insight.area}</h4>
                                <p className="text-sm text-muted-foreground mb-3">
                                  {insight.reasoning}
                                </p>
                                <div className="flex items-start gap-2 p-3 rounded bg-accent/5 mb-3">
                                  <ArrowRight size={16} className="text-accent mt-0.5 flex-shrink-0" />
                                  <p className="text-sm font-medium">{insight.action}</p>
                                </div>
                                <div className="text-sm">
                                  <span className="text-muted-foreground">{insight.metric}: </span>
                                  <span className="font-semibold">{insight.value}</span>
                                </div>
                              </div>
                            </div>
                          </Card>
                        )
                      })}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
