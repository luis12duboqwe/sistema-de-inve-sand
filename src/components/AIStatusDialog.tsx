import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Card, CardContent, CardHeader, CardTitle as CardHeading } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Robot, WarningCircle, Lightning, UserSwitch, BatteryChargingVertical, ArrowsClockwise } from '@phosphor-icons/react'
import type { AIStatusResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface AIStatusDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  status: AIStatusResponse | null
  isLoading: boolean
  error: string | null
  onRefresh: () => void
  isApiMode: boolean
}

const numberFormatter = new Intl.NumberFormat('es-HN')

export function AIStatusDialog({
  open,
  onOpenChange,
  status,
  isLoading,
  error,
  onRefresh,
  isApiMode,
}: AIStatusDialogProps) {
  const formatNumber = (value?: number) => numberFormatter.format(value ?? 0)

  const alerts = status?.forecasting_alerts ?? []
  const profiles = status?.ai_profiles ?? []

  const snapshot = status?.snapshot_generated_at
    ? new Date(status.snapshot_generated_at).toLocaleString()
    : null

  const renderEmpty = () => {
    if (!isApiMode) {
      return 'Activa la conexión con backend para monitorear tus bots de IA.'
    }
    if (error) {
      return error
    }
    if (isLoading) {
      return 'Recopilando métricas en tiempo real...'
    }
    return 'No hay datos disponibles aún.'
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-2xl">
            <Robot size={28} className="text-primary" weight="duotone" />
            Centro de Operaciones IA
          </DialogTitle>
          <DialogDescription>
            Estado consolidado de bots conversacionales, backlog de entrenamiento y alertas predictivas.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between rounded-lg border bg-muted/40 px-4 py-3 text-sm">
          <div className="space-y-1">
            <p className="font-semibold text-muted-foreground">
              Snapshot generado: {snapshot ?? 'Sin datos'}
            </p>
            <p className="text-xs text-muted-foreground">
              Promedio de tokens/respuesta · {status ? status.avg_tokens_per_response.toFixed(2) : '--'}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onRefresh} disabled={!isApiMode || isLoading}>
              <ArrowsClockwise
                size={16}
                className={cn('mr-2 text-muted-foreground', { 'animate-spin': isLoading })}
              />
              Actualizar
            </Button>
          </div>
        </div>

        <ScrollArea className="flex-1 mt-4 pr-4">
          {!status ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              {renderEmpty()}
            </div>
          ) : (
            <div className="space-y-6 pb-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardHeading className="text-sm text-muted-foreground">Bots activos</CardHeading>
                    <p className="text-3xl font-bold">
                      {status.ai_profiles_active}
                      <span className="text-base text-muted-foreground font-normal">
                        /{status.total_sales_profiles}
                      </span>
                    </p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">
                      Canales con IA habilitada actualmente
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardHeading className="text-sm text-muted-foreground">Interacciones 24h</CardHeading>
                    <p className="text-3xl font-bold text-primary">{formatNumber(status.interactions_last_24h)}</p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">Mensajes procesados en las últimas 24 horas</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardHeading className="text-sm text-muted-foreground">Tokens consumidos</CardHeading>
                    <p className="text-3xl font-bold text-primary/90">{formatNumber(status.tokens_last_24h)}</p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">Uso agregado de GPT en las últimas 24 horas</p>
                  </CardContent>
                </Card>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="border-blue-200">
                  <CardHeader className="pb-2">
                    <CardHeading className="flex items-center gap-2 text-blue-900">
                      <Lightning size={18} />
                      Riesgos Inmediatos
                    </CardHeading>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span>Backlog de entrenamiento</span>
                      <Badge variant={status.training_backlog > 0 ? 'destructive' : 'secondary'}>
                        {formatNumber(status.training_backlog)}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Clientes bloqueados / trolls</span>
                      <Badge variant="outline">{formatNumber(status.customers_flagged)}</Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-amber-200">
                  <CardHeader className="pb-2">
                    <CardHeading className="flex items-center gap-2 text-amber-900">
                      <BatteryChargingVertical size={18} />
                      Salud de Bots
                    </CardHeading>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span>Bots activos</span>
                      <Badge variant="secondary">{status.ai_profiles_active}</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Bots inactivos</span>
                      <Badge variant="outline">{status.ai_profiles_inactive}</Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <UserSwitch size={18} className="text-muted-foreground" />
                    <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                      Actividad por perfil
                    </p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Ordenado por interacciones de los últimos 7 días
                  </span>
                </div>

                <div className="rounded-xl border overflow-hidden">
                  <div className="grid grid-cols-5 bg-muted/60 px-4 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    <span>Perfil</span>
                    <span className="text-center">Estado</span>
                    <span className="text-center">Interacciones</span>
                    <span className="text-center">Tokens</span>
                    <span className="text-center">Backlog</span>
                  </div>
                  <div className="divide-y">
                    {profiles.length === 0 ? (
                      <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                        No hay perfiles de ventas con IA configurados.
                      </div>
                    ) : (
                      profiles
                        .slice()
                        .sort((a, b) => b.interactions_last_7_days - a.interactions_last_7_days)
                        .map((profile) => (
                          <div key={profile.sales_profile_id} className="grid grid-cols-5 px-4 py-3 text-sm">
                            <div>
                              <p className="font-medium text-foreground">{profile.sales_profile_name}</p>
                              <p className="text-xs text-muted-foreground">{profile.slug}</p>
                            </div>
                            <div className="flex items-center justify-center">
                              <Badge variant={profile.is_ai_active ? 'secondary' : 'outline'}>
                                {profile.is_ai_active ? 'Activo' : 'Pausado'}
                              </Badge>
                            </div>
                            <div className="text-center font-medium">
                              {formatNumber(profile.interactions_last_7_days)}
                            </div>
                            <div className="text-center text-muted-foreground">
                              {formatNumber(profile.tokens_last_7_days)}
                            </div>
                            <div className="text-center">
                              <Badge variant={profile.pending_training_items > 0 ? 'destructive' : 'outline'}>
                                {profile.pending_training_items}
                              </Badge>
                            </div>
                          </div>
                        ))
                    )}
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-destructive">
                  <WarningCircle size={20} weight="duotone" />
                  <p className="font-semibold">Alertas de inventario predictivas</p>
                </div>
                {alerts.length === 0 ? (
                  <div className="rounded-lg border border-success/30 bg-success/5 px-4 py-3 text-sm text-success">
                    Sin alertas críticas. Los bots tienen inventario suficiente para operar.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {alerts.map((alert) => (
                      <Card key={alert.product_id} className="border-destructive/20">
                        <CardHeader className="pb-2">
                          <CardHeading className="text-base">{alert.product_name}</CardHeading>
                          <p className="text-xs text-muted-foreground">{alert.trend === 'increasing' ? 'Demanda en alza' : alert.trend === 'decreasing' ? 'Demanda en baja' : 'Estable'}</p>
                        </CardHeader>
                        <CardContent className="text-sm space-y-1">
                          <p><strong>Días hasta agotarse:</strong> {alert.days_until_stockout}</p>
                          <p><strong>Reabastecer:</strong> +{alert.restock_recommendation} unidades</p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
