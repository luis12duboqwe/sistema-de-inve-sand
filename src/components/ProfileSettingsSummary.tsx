import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Profile } from '@/lib/types'
import { CurrencyDollar, Bell, Gear, CheckCircle, XCircle, Storefront, Phone, EnvelopeSimple, MapPin } from '@phosphor-icons/react'
import { formatPrice } from '@/lib/priceFormatter'

interface ProfileSettingsSummaryProps {
  profile: Profile
}

export function ProfileSettingsSummary({ profile }: ProfileSettingsSummaryProps) {
  const settings = profile.settings

  if (!settings) {
    return (
      <Card className="p-6 bg-muted/30 border-dashed">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="p-4 bg-muted rounded-full">
            <Gear size={32} className="text-muted-foreground" />
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">
              Sin Configuración Personalizada
            </p>
            <p className="text-sm text-muted-foreground">
              Este perfil está usando la configuración predeterminada del sistema
            </p>
          </div>
          <Badge variant="outline" className="mt-2">
            Click en "Configuración" para personalizar
          </Badge>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-6">
          <Gear size={24} className="text-primary" weight="duotone" />
          <h3 className="font-semibold text-lg">Configuración Actual</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                <CurrencyDollar size={14} />
                Moneda y Formato
              </p>
              <p className="font-semibold text-lg">{settings.currency}</p>
              <p className="text-sm text-muted-foreground">
                Ejemplo: {formatPrice(12345.67, settings)}
              </p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground mb-1">Impuestos</p>
              <div className="flex items-center gap-2">
                {settings.autoCalculateTax ? (
                  <>
                    <CheckCircle size={18} className="text-accent" weight="fill" />
                    <div>
                      <p className="font-medium">{settings.taxRate}% Automático</p>
                      <p className="text-xs text-muted-foreground">
                        Calculado en cada orden
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <XCircle size={18} className="text-muted-foreground" />
                    <span className="font-medium text-muted-foreground">Desactivado</span>
                  </>
                )}
              </div>
            </div>

            <div>
              <p className="text-xs text-muted-foreground mb-1">Umbral de Stock Bajo</p>
              <p className="font-semibold">{settings.lowStockThreshold} unidades</p>
              <p className="text-xs text-muted-foreground">
                Alertas cuando stock {'<'} {settings.lowStockThreshold}
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                <Bell size={14} />
                Notificaciones
              </p>
              <div className="flex items-center gap-2">
                {settings.enableNotifications ? (
                  <>
                    <CheckCircle size={18} className="text-accent" weight="fill" />
                    <span className="font-medium">Activadas</span>
                  </>
                ) : (
                  <>
                    <XCircle size={18} className="text-muted-foreground" />
                    <span className="font-medium text-muted-foreground">Desactivadas</span>
                  </>
                )}
              </div>
            </div>

            <div>
              <p className="text-xs text-muted-foreground mb-1">Método de Pago Predeterminado</p>
              <Badge variant="outline" className="capitalize text-sm">
                {settings.defaultPaymentMethod}
              </Badge>
            </div>

            <div>
              <p className="text-xs text-muted-foreground mb-1">Canal de Venta Predeterminado</p>
              <Badge variant="outline" className="capitalize text-sm">
                {settings.defaultChannel}
              </Badge>
            </div>
          </div>
        </div>
      </Card>

      {(settings.businessAddress || settings.businessPhone || settings.businessEmail) && (
        <Card className="p-6 bg-accent/5 border-accent/20">
          <div className="flex items-center gap-2 mb-4">
            <Storefront size={20} className="text-accent" weight="duotone" />
            <h4 className="font-semibold">Información del Negocio</h4>
          </div>
          <div className="space-y-3">
            {settings.businessAddress && (
              <div className="flex items-start gap-3">
                <MapPin size={16} className="text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-xs text-muted-foreground">Dirección</p>
                  <p className="text-sm font-medium">{settings.businessAddress}</p>
                </div>
              </div>
            )}
            {settings.businessPhone && (
              <div className="flex items-start gap-3">
                <Phone size={16} className="text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-xs text-muted-foreground">Teléfono</p>
                  <p className="text-sm font-medium">{settings.businessPhone}</p>
                </div>
              </div>
            )}
            {settings.businessEmail && (
              <div className="flex items-start gap-3">
                <EnvelopeSimple size={16} className="text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-xs text-muted-foreground">Email</p>
                  <p className="text-sm font-medium">{settings.businessEmail}</p>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
