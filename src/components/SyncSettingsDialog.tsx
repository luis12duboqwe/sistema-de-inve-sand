import { useState } from 'react'
import { useKV } from '@github/spark/hooks'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ArrowsClockwise, Bell, DeviceMobile } from '@phosphor-icons/react'
import { toast } from 'sonner'

interface SyncSettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SyncSettingsDialog({ open, onOpenChange }: SyncSettingsDialogProps) {
  const [syncEnabled, setSyncEnabled] = useKV<boolean>('sync-settings-enabled', true)
  const [notifyOnSync, setNotifyOnSync] = useKV<boolean>('sync-settings-notify', true)
  const [syncInterval, setSyncInterval] = useKV<number>('sync-settings-interval', 2000)
  const [autoResolveConflicts, setAutoResolveConflicts] = useKV<boolean>('sync-settings-auto-resolve', true)

  const handleClearSyncData = async () => {
    const confirmed = window.confirm('¿Estás seguro de que deseas limpiar los datos de sincronización? Esto no eliminará tus datos, solo reiniciará el estado de sincronización.')
    
    if (confirmed) {
      localStorage.removeItem('stellar-device-id')
      toast.success('Datos de sincronización limpiados')
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowsClockwise size={24} weight="duotone" />
            Configuración de Sincronización
          </DialogTitle>
          <DialogDescription>
            Configura cómo se sincronizan tus datos entre dispositivos
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base flex items-center gap-2">
                <DeviceMobile size={18} />
                Sincronización Habilitada
              </Label>
              <p className="text-sm text-muted-foreground">
                Sincroniza automáticamente datos entre dispositivos
              </p>
            </div>
            <Switch
              checked={syncEnabled ?? true}
              onCheckedChange={(checked) => setSyncEnabled(checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base flex items-center gap-2">
                <Bell size={18} />
                Notificaciones de Sincronización
              </Label>
              <p className="text-sm text-muted-foreground">
                Muestra alertas cuando se detectan cambios
              </p>
            </div>
            <Switch
              checked={notifyOnSync ?? true}
              onCheckedChange={(checked) => setNotifyOnSync(checked)}
              disabled={!syncEnabled}
            />
          </div>

          <div className="space-y-2">
            <Label>Intervalo de Verificación</Label>
            <Select 
              value={String(syncInterval ?? 2000)} 
              onValueChange={(value) => setSyncInterval(Number(value))}
              disabled={!syncEnabled}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1000">1 segundo (más rápido)</SelectItem>
                <SelectItem value="2000">2 segundos (recomendado)</SelectItem>
                <SelectItem value="5000">5 segundos (equilibrado)</SelectItem>
                <SelectItem value="10000">10 segundos (eficiente)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Frecuencia con la que se verifican cambios de otros dispositivos
            </p>
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base">Resolver Conflictos Automáticamente</Label>
              <p className="text-sm text-muted-foreground">
                Usa el cambio más reciente en caso de conflicto
              </p>
            </div>
            <Switch
              checked={autoResolveConflicts ?? true}
              onCheckedChange={(checked) => setAutoResolveConflicts(checked)}
              disabled={!syncEnabled}
            />
          </div>

          <div className="pt-4 border-t">
            <Button
              variant="outline"
              onClick={handleClearSyncData}
              className="w-full"
            >
              Limpiar Datos de Sincronización
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
