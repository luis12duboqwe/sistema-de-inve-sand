import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Profile } from '@/lib/types'
import { CurrencyDollar, Bell, Gear, CheckCircle, XCircle } from '@phosphor-icons/react'

interface ProfileSettingsSummaryProps {
  profile: Profile
}

export function ProfileSettingsSummary({ profile }: ProfileSettingsSummaryProps) {
  const settings = profile.settings

  if (!settings) {
    return (
      <Card className="p-4 bg-muted/50">
        <div className="flex items-center gap-3">
          <Gear size={20} className="text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No se han configurado ajustes personalizados para este perfil
          </p>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <div className="flex items-center gap-2 mb-4">
        <Gear size={24} className="text-primary" weight="duotone" />
        <h3 className="font-semibold text-lg">Configuración Actual</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <CurrencyDollar size={16} className="text-muted-foreground" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Moneda</p>
              <p className="font-medium">{settings.currency}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="w-4 h-4" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Formato de precio</p>
              <p className="font-medium capitalize">{settings.priceFormat}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="w-4 h-4" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Impuestos automáticos</p>
              <div className="flex items-center gap-2">
                {settings.autoCalculateTax ? (
                  <>
                    <CheckCircle size={16} className="text-accent" weight="fill" />
                    <span className="font-medium">{settings.taxRate}%</span>
                  </>
                ) : (
                  <>
                    <XCircle size={16} className="text-muted-foreground" />
                    <span className="font-medium text-muted-foreground">Desactivado</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Bell size={16} className="text-muted-foreground" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Notificaciones</p>
              <div className="flex items-center gap-2">
                {settings.enableNotifications ? (
                  <>
                    <CheckCircle size={16} className="text-accent" weight="fill" />
                    <span className="font-medium">Activadas</span>
                  </>
                ) : (
                  <>
                    <XCircle size={16} className="text-muted-foreground" />
                    <span className="font-medium text-muted-foreground">Desactivadas</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="w-4 h-4" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Umbral de stock bajo</p>
              <p className="font-medium">{settings.lowStockThreshold} unidades</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="w-4 h-4" />
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Canal predeterminado</p>
              <Badge variant="outline" className="capitalize">{settings.defaultChannel}</Badge>
            </div>
          </div>
        </div>
      </div>

      {(settings.businessAddress || settings.businessPhone || settings.businessEmail) && (
        <>
          <div className="my-4 border-t" />
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Información del Negocio</p>
            {settings.businessAddress && (
              <p className="text-sm">{settings.businessAddress}</p>
            )}
            <div className="flex flex-wrap gap-4 text-sm">
              {settings.businessPhone && (
                <span className="text-muted-foreground">
                  Tel: <span className="text-foreground">{settings.businessPhone}</span>
                </span>
              )}
              {settings.businessEmail && (
                <span className="text-muted-foreground">
                  Email: <span className="text-foreground">{settings.businessEmail}</span>
                </span>
              )}
            </div>
          </div>
        </>
      )}
    </Card>
  )
}
