import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Sparkle, TrendUp, WarningCircle, ChartLine } from '@phosphor-icons/react'
import { ForecastingSummary, RestockAlert } from '@/lib/aiForecasting'
import { motion } from 'framer-motion'

interface ForecastingWidgetProps {
  summary: ForecastingSummary | null
  criticalAlerts: RestockAlert[]
  lastUpdated: string | null
  isGenerating: boolean
  onViewDetails: () => void
  onRefresh: () => void
}

export function ForecastingWidget({
  summary,
  criticalAlerts,
  lastUpdated,
  isGenerating,
  onViewDetails,
  onRefresh,
}: ForecastingWidgetProps) {
  const formatCurrency = (amount: number) => {
    return `Lps ${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`
  }

  const getTimeSinceUpdate = () => {
    if (!lastUpdated) return 'Nunca'
    const hours = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / (1000 * 60 * 60))
    if (hours < 1) return 'Hace menos de 1 hora'
    if (hours === 1) return 'Hace 1 hora'
    if (hours < 24) return `Hace ${hours} horas`
    const days = Math.floor(hours / 24)
    return days === 1 ? 'Hace 1 día' : `Hace ${days} días`
  }

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-primary/10 to-transparent rounded-full blur-2xl" />
      
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkle size={24} className="text-primary" weight="duotone" />
              Pronóstico IA
            </CardTitle>
            <CardDescription className="mt-1">
              {lastUpdated ? getTimeSinceUpdate() : 'No generado'}
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={isGenerating}
            className="hover:bg-primary/10"
          >
            {isGenerating ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              >
                <Sparkle size={18} className="text-primary" />
              </motion.div>
            ) : (
              <Sparkle size={18} />
            )}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {!summary ? (
          <div className="text-center py-6">
            <p className="text-sm text-muted-foreground mb-3">
              Genera un pronóstico de ventas con IA
            </p>
            <Button onClick={onRefresh} disabled={isGenerating}>
              <Sparkle size={16} className="mr-2" />
              {isGenerating ? 'Generando...' : 'Generar Pronóstico'}
            </Button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-accent/30 rounded-lg p-3">
                <p className="text-xs text-muted-foreground mb-1">Ingresos 7d</p>
                <p className="text-lg font-bold text-success">
                  {formatCurrency(summary.estimatedRevenue7Days)}
                </p>
              </div>
              <div className="bg-accent/30 rounded-lg p-3">
                <p className="text-xs text-muted-foreground mb-1">Ingresos 30d</p>
                <p className="text-lg font-bold text-success">
                  {formatCurrency(summary.estimatedRevenue30Days)}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Alertas Críticas</span>
                <Badge variant="destructive" className="font-mono">
                  {summary.criticalStockAlerts}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Necesitan Reabastecimiento</span>
                <Badge variant="secondary" className="font-mono">
                  {summary.productsNeedingRestock}
                </Badge>
              </div>
            </div>

            {criticalAlerts.length > 0 && (
              <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <WarningCircle size={16} className="text-destructive" weight="fill" />
                  <p className="text-sm font-semibold text-destructive">
                    {criticalAlerts.length} Alerta{criticalAlerts.length !== 1 ? 's' : ''} Urgente
                    {criticalAlerts.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="space-y-1">
                  {criticalAlerts.slice(0, 3).map((alert, idx) => (
                    <p key={idx} className="text-xs text-muted-foreground truncate">
                      • {alert.productName} ({alert.daysUntilStockout}d)
                    </p>
                  ))}
                  {criticalAlerts.length > 3 && (
                    <p className="text-xs text-muted-foreground">
                      +{criticalAlerts.length - 3} más
                    </p>
                  )}
                </div>
              </div>
            )}

            {summary.topPerformingProducts.length > 0 && (
              <div className="bg-success/10 border border-success/20 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <TrendUp size={16} className="text-success" weight="bold" />
                  <p className="text-sm font-semibold text-success">Productos en Crecimiento</p>
                </div>
                <div className="space-y-1">
                  {summary.topPerformingProducts.slice(0, 2).map((product, idx) => (
                    <p key={idx} className="text-xs text-muted-foreground truncate">
                      • {product}
                    </p>
                  ))}
                </div>
              </div>
            )}

            <Button onClick={onViewDetails} className="w-full" variant="outline">
              <ChartLine size={16} className="mr-2" />
              Ver Análisis Completo
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
