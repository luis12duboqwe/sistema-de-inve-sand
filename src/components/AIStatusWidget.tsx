import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Robot, WarningCircle, Gauge, ArrowsClockwise } from '@phosphor-icons/react'
import type { AIStatusResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface AIStatusWidgetProps {
  status: AIStatusResponse | null
  isLoading: boolean
  error: string | null
  isApiMode: boolean
  onRefresh: () => void
  onOpenDetails: () => void
}

export function AIStatusWidget({
  status,
  isLoading,
  error,
  isApiMode,
  onRefresh,
  onOpenDetails,
}: AIStatusWidgetProps) {
  const topProfiles = [...(status?.ai_profiles ?? [])]
    .sort((a, b) => b.interactions_last_7_days - a.interactions_last_7_days)
    .slice(0, 3)

  const alerts = (status?.forecasting_alerts ?? []).slice(0, 3)

  const lastUpdatedLabel = status?.snapshot_generated_at
    ? new Date(status.snapshot_generated_at).toLocaleString()
    : 'Sin datos'

  const emptyState = !isApiMode
    ? {
        title: 'Modo API requerido',
        description: 'Activa la conexión con backend para ver actividad de bots.',
      }
    : error
      ? {
          title: 'Error al cargar métricas',
          description: error,
        }
      : isLoading
        ? {
            title: 'Cargando IA Ops...',
            description: 'Sincronizando métricas en tiempo real',
          }
        : null

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950/5 via-primary/5 to-transparent pointer-events-none" />
      <CardHeader className="relative z-10">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Robot size={22} className="text-primary" weight="duotone" />
              IA Ops Snapshot
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">{lastUpdatedLabel}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="icon" onClick={onRefresh} disabled={!isApiMode || isLoading}>
              <ArrowsClockwise
                size={18}
                className={cn('text-muted-foreground transition-transform', {
                  'animate-spin': isLoading,
                  'text-primary': !isLoading,
                })}
              />
            </Button>
            <Button variant="outline" size="sm" onClick={onOpenDetails} disabled={!isApiMode}>
              Ver Panel
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative z-10 space-y-4">
        {emptyState ? (
          <div className="rounded-lg border-dashed border px-4 py-6 text-center text-sm text-muted-foreground">
            <p className="font-semibold text-foreground">{emptyState.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{emptyState.description}</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-primary/10 p-3">
                <p className="text-xs text-muted-foreground">Bots activos</p>
                <p className="text-2xl font-semibold text-primary">
                  {status?.ai_profiles_active ?? 0}
                  <span className="text-xs text-muted-foreground font-normal ml-1">
                    /{status?.total_sales_profiles ?? 0}
                  </span>
                </p>
              </div>
              <div className="rounded-xl bg-success/10 p-3">
                <p className="text-xs text-muted-foreground">Interacciones 24h</p>
                <p className="text-2xl font-semibold text-success">
                  {status?.interactions_last_24h ?? 0}
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-border/50 p-3">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Backlog de entrenamiento</span>
                <Badge variant={status && status.training_backlog > 0 ? 'destructive' : 'secondary'}>
                  {status?.training_backlog ?? 0}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground mt-2">
                <span>Clientes señalados</span>
                <Badge variant="outline">{status?.customers_flagged ?? 0}</Badge>
              </div>
            </div>

            {topProfiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Bots más activos
                </p>
                <div className="space-y-1">
                  {topProfiles.map((profile) => (
                    <div key={profile.sales_profile_id} className="flex items-center justify-between text-sm">
                      <div>
                        <p className="font-medium text-foreground">{profile.sales_profile_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {profile.interactions_last_7_days} interacciones · {profile.tokens_last_7_days} tokens
                        </p>
                      </div>
                      <Badge variant={profile.is_ai_active ? 'secondary' : 'outline'}>
                        {profile.is_ai_active ? 'Activo' : 'Pausado'}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {alerts.length > 0 && (
              <div className="rounded-2xl bg-destructive/5 border border-destructive/30 p-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-destructive mb-2">
                  <WarningCircle size={18} weight="duotone" />
                  Alertas de inventario IA
                </div>
                <div className="space-y-1">
                  {alerts.map((alert) => (
                    <div key={alert.product_id} className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="truncate pr-2">{alert.product_name}</span>
                      <span>
                        {alert.days_until_stockout}d · +{alert.restock_recommendation} uds
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {status && alerts.length === 0 && (
              <div className="flex items-center gap-2 rounded-lg bg-success/10 border border-success/20 px-3 py-2 text-xs text-success">
                <Gauge size={16} weight="duotone" />
                Inventario balanceado según IA
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
