import { useState, useEffect, useCallback } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { Sparkle, TrendUp, TrendDown, Minus, WarningCircle, Package, CalendarBlank, ChartLine, Lightbulb } from '@phosphor-icons/react'
import { ProductWithStock, OrderWithItems, Profile } from '@/lib/types'
import { generateAIForecasts, generateRestockAlerts, generateAIInsights, SalesForecast, RestockAlert, ForecastingSummary } from '@/lib/aiForecasting'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'

interface AIForecastingDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  products: ProductWithStock[]
  orders: OrderWithItems[]
  profile: Profile
  onProductClick?: (product: ProductWithStock) => void
}

export function AIForecastingDialog({
  open,
  onOpenChange,
  products,
  orders,
  profile,
  onProductClick,
}: AIForecastingDialogProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [forecasts, setForecasts] = useState<SalesForecast[]>([])
  const [alerts, setAlerts] = useState<RestockAlert[]>([])
  const [summary, setSummary] = useState<ForecastingSummary | null>(null)
  const [insights, setInsights] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState('summary')

  const generateForecasts = useCallback(async () => {
    setIsLoading(true)
    try {
      const { forecasts: newForecasts, summary: newSummary } = await generateAIForecasts(
        products,
        orders
      )
      setForecasts(newForecasts)
      setSummary(newSummary)

      const newAlerts = await generateRestockAlerts(newForecasts, profile)
      setAlerts(newAlerts)

      const newInsights = await generateAIInsights(newForecasts, newAlerts, products)
      setInsights(newInsights)

      toast.success('Análisis predictivo completado')
    } catch (error) {
      console.error('Error generating forecasts:', error)
      toast.error('Error al generar pronósticos')
    } finally {
      setIsLoading(false)
    }
  }, [products, orders, profile])

  useEffect(() => {
    if (open) {
      generateForecasts()
    }
  }, [open, generateForecasts])

  const getTrendIcon = (trend: 'increasing' | 'stable' | 'decreasing') => {
    if (trend === 'increasing') return <TrendUp size={16} className="text-success" weight="bold" />
    if (trend === 'decreasing') return <TrendDown size={16} className="text-destructive" weight="bold" />
    return <Minus size={16} className="text-muted-foreground" weight="bold" />
  }

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical':
        return 'destructive'
      case 'high':
        return 'default'
      case 'medium':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  const getUrgencyLabel = (urgency: string) => {
    switch (urgency) {
      case 'critical':
        return 'Crítico'
      case 'high':
        return 'Alto'
      case 'medium':
        return 'Medio'
      default:
        return 'Bajo'
    }
  }

  const formatCurrency = (amount: number) => {
    return `Lps ${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-2xl">
            <Sparkle size={28} className="text-primary" weight="duotone" />
            Pronóstico de Ventas con IA
          </DialogTitle>
          <DialogDescription>
            Análisis predictivo de demanda y alertas de reabastecimiento.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <motion.div
              animate={{
                rotate: [0, 360],
                scale: [1, 1.1, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            >
              <Sparkle size={48} className="text-primary" weight="duotone" />
            </motion.div>
            <p className="text-muted-foreground">Analizando datos y generando pronósticos...</p>
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="summary">Resumen</TabsTrigger>
              <TabsTrigger value="forecasts">Pronósticos</TabsTrigger>
              <TabsTrigger value="alerts">Alertas</TabsTrigger>
              <TabsTrigger value="insights">Insights IA</TabsTrigger>
            </TabsList>

            <TabsContent value="summary" className="space-y-4">
              {summary && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardDescription>Productos Analizados</CardDescription>
                        <CardTitle className="text-3xl">{summary.totalProducts}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">Total de productos activos</p>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardDescription>Necesitan Reabastecimiento</CardDescription>
                        <CardTitle className="text-3xl text-warning">
                          {summary.productsNeedingRestock}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">
                          Productos con stock bajo o agotándose
                        </p>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardDescription>Alertas Críticas</CardDescription>
                        <CardTitle className="text-3xl text-destructive">
                          {summary.criticalStockAlerts}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">
                          Productos que se agotarán en 7 días
                        </p>
                      </CardContent>
                    </Card>

                    <Card className="md:col-span-2">
                      <CardHeader className="pb-3">
                        <CardDescription>Ingresos Proyectados (7 días)</CardDescription>
                        <CardTitle className="text-3xl text-success">
                          {formatCurrency(summary.estimatedRevenue7Days)}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">
                          Basado en análisis de tendencias de venta
                        </p>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-3">
                        <CardDescription>Ingresos Proyectados (30 días)</CardDescription>
                        <CardTitle className="text-2xl text-success">
                          {formatCurrency(summary.estimatedRevenue30Days)}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">Estimación mensual</p>
                      </CardContent>
                    </Card>
                  </div>

                  {summary.topPerformingProducts.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <TrendUp size={20} className="text-success" />
                          Top Productos en Crecimiento
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          {summary.topPerformingProducts.map((product, idx) => (
                            <Badge key={idx} variant="secondary" className="text-sm">
                              {product}
                            </Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {summary.slowMovingProducts.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <TrendDown size={20} className="text-warning" />
                          Productos de Movimiento Lento
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          {summary.slowMovingProducts.map((product, idx) => (
                            <Badge key={idx} variant="outline" className="text-sm">
                              {product}
                            </Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </TabsContent>

            <TabsContent value="forecasts" className="space-y-3">
              <div className="flex justify-between items-center">
                <p className="text-sm text-muted-foreground">
                  {forecasts.length} productos analizados
                </p>
                <Button variant="outline" size="sm" onClick={generateForecasts}>
                  <Sparkle size={16} className="mr-2" />
                  Regenerar
                </Button>
              </div>

              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                <AnimatePresence>
                  {forecasts.slice(0, 50).map((forecast, idx) => {
                    const product = products.find((p) => p.id === forecast.productId)
                    if (!product) return null

                    return (
                      <motion.div
                        key={forecast.productId}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.02 }}
                      >
                        <Card
                          className="cursor-pointer hover:bg-accent/50 transition-colors"
                          onClick={() => onProductClick?.(product)}
                        >
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-2">
                                  <h4 className="font-semibold truncate">{forecast.productName}</h4>
                                  {getTrendIcon(forecast.trend)}
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                                  <div>
                                    <p className="text-muted-foreground text-xs">Stock Actual</p>
                                    <p className="font-medium">{forecast.currentStock}</p>
                                  </div>
                                  <div>
                                    <p className="text-muted-foreground text-xs">Ventas/día</p>
                                    <p className="font-medium">
                                      {forecast.averageDailySales.toFixed(1)}
                                    </p>
                                  </div>
                                  <div>
                                    <p className="text-muted-foreground text-xs">Días hasta agotar</p>
                                    <p className="font-medium">
                                      {forecast.daysUntilStockout > 999
                                        ? '∞'
                                        : forecast.daysUntilStockout}
                                    </p>
                                  </div>
                                  <div>
                                    <p className="text-muted-foreground text-xs">Reabastecer</p>
                                    <p className="font-medium text-primary">
                                      {forecast.restockRecommendation} uds
                                    </p>
                                  </div>
                                </div>

                                <div className="mt-3">
                                  <div className="flex justify-between text-xs mb-1">
                                    <span className="text-muted-foreground">Confianza</span>
                                    <span className="font-medium">
                                      {(forecast.confidence * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                  <Progress value={forecast.confidence * 100} />
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                    )
                  })}
                </AnimatePresence>
              </div>
            </TabsContent>

            <TabsContent value="alerts" className="space-y-3">
              <div className="flex justify-between items-center">
                <p className="text-sm text-muted-foreground">{alerts.length} alertas activas</p>
              </div>

              {alerts.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <Package size={48} className="text-muted-foreground mb-4" weight="duotone" />
                    <p className="text-muted-foreground">No hay alertas de reabastecimiento</p>
                    <p className="text-sm text-muted-foreground">
                      Todos los productos tienen stock suficiente
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                  <AnimatePresence>
                    {alerts.map((alert, idx) => {
                      const product = products.find((p) => p.id === alert.productId)
                      if (!product) return null

                      return (
                        <motion.div
                          key={alert.productId}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.03 }}
                        >
                          <Card
                            className="cursor-pointer hover:bg-accent/50 transition-colors border-l-4"
                            style={{
                              borderLeftColor:
                                alert.urgency === 'critical'
                                  ? 'hsl(var(--destructive))'
                                  : alert.urgency === 'high'
                                    ? 'hsl(var(--warning))'
                                    : 'hsl(var(--muted))',
                            }}
                            onClick={() => onProductClick?.(product)}
                          >
                            <CardContent className="p-4">
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-2">
                                    <WarningCircle
                                      size={20}
                                      className={
                                        alert.urgency === 'critical'
                                          ? 'text-destructive'
                                          : alert.urgency === 'high'
                                            ? 'text-warning'
                                            : 'text-muted-foreground'
                                      }
                                      weight="fill"
                                    />
                                    <h4 className="font-semibold">{alert.productName}</h4>
                                    <Badge variant={getUrgencyColor(alert.urgency) as any}>
                                      {getUrgencyLabel(alert.urgency)}
                                    </Badge>
                                  </div>

                                  <p className="text-sm text-muted-foreground mb-3">
                                    {alert.reasoning}
                                  </p>

                                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                                    <div>
                                      <p className="text-muted-foreground text-xs">Stock Actual</p>
                                      <p className="font-medium">{alert.currentStock} uds</p>
                                    </div>
                                    <div>
                                      <p className="text-muted-foreground text-xs">
                                        Días hasta agotar
                                      </p>
                                      <p className="font-medium text-destructive">
                                        {alert.daysUntilStockout} días
                                      </p>
                                    </div>
                                    <div>
                                      <p className="text-muted-foreground text-xs">
                                        Cantidad recomendada
                                      </p>
                                      <p className="font-medium text-primary">
                                        {alert.recommendedOrderQuantity} uds
                                      </p>
                                    </div>
                                  </div>

                                  <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                                    <CalendarBlank size={14} />
                                    <span>
                                      Reabastecer antes del:{' '}
                                      {alert.estimatedRestockDate.toLocaleDateString('es-MX')}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        </motion.div>
                      )
                    })}
                  </AnimatePresence>
                </div>
              )}
            </TabsContent>

            <TabsContent value="insights" className="space-y-3">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Lightbulb size={24} className="text-primary" weight="duotone" />
                    Insights Generados por IA
                  </CardTitle>
                  <CardDescription>
                    Recomendaciones personalizadas basadas en análisis predictivo
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {insights.length === 0 ? (
                    <p className="text-muted-foreground text-center py-8">
                      Generando insights...
                    </p>
                  ) : (
                    <AnimatePresence>
                      {insights.map((insight, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: idx * 0.1 }}
                          className="flex items-start gap-3 p-4 bg-accent/30 rounded-lg"
                        >
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                            <span className="text-sm font-bold text-primary">{idx + 1}</span>
                          </div>
                          <p className="flex-1 text-sm leading-relaxed">{insight}</p>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  )}

                  <div className="mt-6 pt-4 border-t border-border">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={generateForecasts}
                      className="w-full"
                    >
                      <Sparkle size={16} className="mr-2" />
                      Regenerar Análisis
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-muted/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <ChartLine size={20} />
                    Metodología
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • Análisis de tendencias basado en 90 días de historial de ventas
                  </p>
                  <p>
                    • Cálculo de velocidad de venta promedio ponderada por recencia
                  </p>
                  <p>
                    • Predicción de agotamiento considerando tendencias de crecimiento
                  </p>
                  <p>
                    • Recomendaciones de reabastecimiento con stock de seguridad de 14 días
                  </p>
                  <p>• Insights generados por GPT-4 considerando contexto del negocio</p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  )
}
