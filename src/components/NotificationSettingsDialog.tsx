import { useKV } from '@github/spark/hooks'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Bell, Warning, Check } from '@phosphor-icons/react'
import type { Profile } from '@/lib/types'

export interface NotificationSettings {
  enableLowStockAlerts: boolean
  enableOutOfStockAlerts: boolean
  enableDailyDigest: boolean
  digestTime: string
  soundEnabled: boolean
  notificationMethod: 'in-app' | 'email' | 'both'
  criticalOnly: boolean
}

interface NotificationSettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profiles: Profile[]
}

export function NotificationSettingsDialog({
  open,
  onOpenChange,
  profiles
}: NotificationSettingsDialogProps) {
  const [settings, setSettings] = useKV<NotificationSettings>('notification-settings', {
    enableLowStockAlerts: true,
    enableOutOfStockAlerts: true,
    enableDailyDigest: false,
    digestTime: '09:00',
    soundEnabled: false,
    notificationMethod: 'in-app',
    criticalOnly: false
  })

  const updateSetting = <K extends keyof NotificationSettings>(
    key: K,
    value: NotificationSettings[K]
  ) => {
    setSettings(current => ({
      ...(current ?? {
        enableLowStockAlerts: true,
        enableOutOfStockAlerts: true,
        enableDailyDigest: false,
        digestTime: '09:00',
        soundEnabled: false,
        notificationMethod: 'in-app',
        criticalOnly: false
      }),
      [key]: value
    }))
  }

  const getActiveProfilesCount = () => {
    return profiles.filter(p => p.active && p.settings?.enableNotifications).length
  }

  const getCriticalStockCount = () => {
    return profiles.reduce((count, profile) => {
      const threshold = profile.settings?.lowStockThreshold || 5
      return count + (threshold <= 3 ? 1 : 0)
    }, 0)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bell size={24} className="text-primary" weight="duotone" />
            Configuración de Notificaciones
          </DialogTitle>
          <DialogDescription>
            Configure cómo y cuándo recibir alertas sobre el inventario
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <Card className="p-4 bg-accent/20 border-accent">
            <div className="flex items-start gap-3">
              <Warning size={20} className="text-accent-foreground mt-0.5" weight="fill" />
              <div className="flex-1 space-y-1">
                <h4 className="text-sm font-semibold text-accent-foreground">
                  Estado de Alertas
                </h4>
                <div className="flex flex-wrap gap-2 text-xs">
                  <Badge variant="secondary">
                    {getActiveProfilesCount()} perfil{getActiveProfilesCount() !== 1 ? 'es' : ''} activo{getActiveProfilesCount() !== 1 ? 's' : ''}
                  </Badge>
                  {getCriticalStockCount() > 0 && (
                    <Badge variant="destructive">
                      {getCriticalStockCount()} con umbral crítico
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </Card>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Tipos de Alertas</h3>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="low-stock-alerts" className="text-sm font-medium">
                  Alertas de Stock Bajo
                </Label>
                <p className="text-xs text-muted-foreground">
                  Recibir notificaciones cuando el stock esté por debajo del umbral
                </p>
              </div>
              <Switch
                id="low-stock-alerts"
                checked={settings?.enableLowStockAlerts ?? true}
                onCheckedChange={(checked) => updateSetting('enableLowStockAlerts', checked)}
              />
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="out-of-stock-alerts" className="text-sm font-medium">
                  Alertas de Stock Agotado
                </Label>
                <p className="text-xs text-muted-foreground">
                  Notificar inmediatamente cuando un producto se agote
                </p>
              </div>
              <Switch
                id="out-of-stock-alerts"
                checked={settings?.enableOutOfStockAlerts ?? true}
                onCheckedChange={(checked) => updateSetting('enableOutOfStockAlerts', checked)}
              />
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="critical-only" className="text-sm font-medium">
                  Solo Alertas Críticas
                </Label>
                <p className="text-xs text-muted-foreground">
                  Mostrar únicamente productos con stock agotado o muy bajo
                </p>
              </div>
              <Switch
                id="critical-only"
                checked={settings?.criticalOnly ?? false}
                onCheckedChange={(checked) => updateSetting('criticalOnly', checked)}
              />
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Resumen Diario</h3>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="daily-digest" className="text-sm font-medium">
                  Resumen Diario
                </Label>
                <p className="text-xs text-muted-foreground">
                  Recibir un resumen de inventario cada día
                </p>
              </div>
              <Switch
                id="daily-digest"
                checked={settings?.enableDailyDigest ?? false}
                onCheckedChange={(checked) => updateSetting('enableDailyDigest', checked)}
              />
            </div>

            {settings?.enableDailyDigest && (
              <div className="space-y-2 pl-3">
                <Label htmlFor="digest-time" className="text-sm">
                  Hora del Resumen
                </Label>
                <Input
                  id="digest-time"
                  type="time"
                  value={settings?.digestTime ?? '09:00'}
                  onChange={(e) => updateSetting('digestTime', e.target.value)}
                  className="max-w-xs"
                />
              </div>
            )}
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Preferencias</h3>

            <div className="space-y-2">
              <Label htmlFor="notification-method" className="text-sm">
                Método de Notificación
              </Label>
              <Select
                value={settings?.notificationMethod ?? 'in-app'}
                onValueChange={(value: NotificationSettings['notificationMethod']) =>
                  updateSetting('notificationMethod', value)
                }
              >
                <SelectTrigger id="notification-method" className="max-w-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="in-app">Solo en la aplicación</SelectItem>
                  <SelectItem value="email">Solo por email</SelectItem>
                  <SelectItem value="both">Ambos métodos</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="sound-enabled" className="text-sm font-medium">
                  Sonido de Notificaciones
                </Label>
                <p className="text-xs text-muted-foreground">
                  Reproducir un sonido al recibir notificaciones
                </p>
              </div>
              <Switch
                id="sound-enabled"
                checked={settings?.soundEnabled ?? false}
                onCheckedChange={(checked) => updateSetting('soundEnabled', checked)}
              />
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Umbrales por Perfil</h3>
            <p className="text-xs text-muted-foreground">
              Configure el umbral de stock bajo para cada perfil en la sección de Perfiles
            </p>

            <div className="space-y-2">
              {profiles.filter(p => p.active).map(profile => (
                <div
                  key={profile.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="space-y-0.5">
                    <p className="text-sm font-medium">{profile.name}</p>
                    <div className="flex items-center gap-2">
                      {profile.settings?.enableNotifications ? (
                        <Badge variant="default" className="text-xs">
                          <Check size={12} className="mr-1" />
                          Activo
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs">
                          Desactivado
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        Umbral: {profile.settings?.lowStockThreshold || 5} unidades
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
