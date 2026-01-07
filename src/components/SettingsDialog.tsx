import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { useKV } from '@/hooks/use-kv'
import { Database, CloudArrowUp, CloudSlash, Bell, ArrowsClockwise, Trash, Users, WarningOctagon } from '@phosphor-icons/react'
import { apiClient } from '@/lib/apiClient'
import { clearAllData } from '@/lib/dataInitializer'
import { syncService } from '@/lib/syncService'
import { toast } from 'sonner'
import { ManageUsersDialog } from '@/components/ManageUsersDialog'

type SyncProgressState = {
  status: 'idle' | 'processing' | 'success' | 'error'
  processed: number
  total: number
  lastEntity?: string
  lastAction?: string
  lastError?: string
}

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onOpenNotificationSettings?: () => void
  onOpenSyncSettings?: () => void
}

export function SettingsDialog({ open, onOpenChange, onOpenNotificationSettings, onOpenSyncSettings }: SettingsDialogProps) {
  const [apiUrl, setApiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')
  const [useApi, setUseApi] = useKV<boolean>('settings_use_api', false)
  const [pendingSyncFlag] = useKV<boolean>('settings_pending_sync', false)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [localApiUrl, setLocalApiUrl] = useState('')
  const [showManageUsers, setShowManageUsers] = useState(false)
  const [currentUser, setCurrentUser] = useState<any>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncProgress, setSyncProgress] = useState<SyncProgressState>({ status: 'idle', processed: 0, total: 0 })

  useEffect(() => {
    if (apiUrl) {
      setLocalApiUrl(apiUrl)
    }
    const userStr = localStorage.getItem('auth_user')
    if (userStr) {
      try {
        setCurrentUser(JSON.parse(userStr))
      } catch (err) {
        console.error('Error parseando usuario de auth_user', err)
      }
    }
  }, [apiUrl])

  useEffect(() => {
    if (!pendingSyncFlag && !isSyncing) {
      setSyncProgress({ status: 'idle', processed: 0, total: 0 })
    }
  }, [pendingSyncFlag, isSyncing])

  const syncProgressPercent = syncProgress.total > 0
    ? Math.min(100, Math.round((syncProgress.processed / syncProgress.total) * 100))
    : isSyncing
      ? 5
      : 0

  const syncProgressLabel = syncProgress.total > 0
    ? `${syncProgress.processed} / ${syncProgress.total} eventos`
    : isSyncing
      ? 'Preparando sincronización...'
      : 'Sin eventos pendientes'

  const showSyncProgress = isSyncing || syncProgress.status !== 'idle'

  const testConnection = async () => {
    setIsTestingConnection(true)
    setConnectionStatus('idle')
    
    try {
      const response = await fetch(`${localApiUrl}/health`)
      if (response.ok) {
        setConnectionStatus('success')
        toast.success('Conexión exitosa con el backend')
      } else {
        throw new Error('Connection failed')
      }
    } catch {
      setConnectionStatus('error')
      toast.error('No se pudo conectar con el backend')
    } finally {
      setIsTestingConnection(false)
    }
  }

  const handleSave = () => {
    const urlChanged = localApiUrl !== apiUrl
    setApiUrl(localApiUrl)
    toast.success('Configuración guardada')
    
    if (urlChanged || useApi) {
      toast.info('Recarga la página para aplicar los cambios')
    }
    
    onOpenChange(false)
  }

  const handleInitializeBackend = async () => {
    try {
      await apiClient.initializeData()
      toast.success('Base de datos inicializada con datos de prueba')
    } catch {
      toast.error('Error al inicializar base de datos')
    }
  }

  const handleSyncLocalToRemote = async () => {
    if (!useApi) {
      toast.error('Debe activar el modo API primero')
      return
    }
    if (isSyncing) {
      return
    }

    setIsSyncing(true)
    setSyncProgress({ status: 'processing', processed: 0, total: 0 })

    const toastId = toast.loading('Sincronizando datos locales a la nube...')
    try {
      const result = await syncService.syncLocalToRemote({
        onProgress: event => {
          setSyncProgress({
            status: event.status,
            processed: event.processed,
            total: event.total,
            lastEntity: event.event.entity,
            lastAction: event.event.action,
            lastError: event.error
          })
        }
      })

      if (result.total === 0) {
        setSyncProgress({ status: 'success', processed: 0, total: 0 })
        toast.success('No hay eventos pendientes por sincronizar.')
        return
      }

      const remainingEvents = result.pendingEvents ?? 0
      const pendingAfterSync = remainingEvents || result.failed

      setSyncProgress(prev => ({
        ...prev,
        status: result.failed > 0 ? 'error' : 'success',
        processed: result.total,
        total: result.total,
        lastError:
          result.failed > 0
            ? `Quedan ${pendingAfterSync} evento(s) pendientes por sincronizar. Revisa el historial para más detalles.`
            : undefined
      }))

      const baseSummary = `Sincronización completada: ${result.synced}/${result.total} eventos`
      const snapshotSummary = result.snapshot
        ? `Datos actualizados (${result.snapshot.products} productos, ${result.snapshot.orders} órdenes, ${result.snapshot.stockEntries} existencias).`
        : 'Sincronización finalizada.'

      if (result.failed > 0) {
        toast.warning(`${baseSummary}. ${result.failed} evento(s) con error. Quedan ${pendingAfterSync} pendientes.`)
      } else if (remainingEvents > 0) {
        toast.info(`${baseSummary}. Hay ${remainingEvents} evento(s) nuevos pendientes de sincronizar.`)
      } else {
        toast.success(`${baseSummary}. ${snapshotSummary}`)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error durante la sincronización'
      setSyncProgress(prev => ({
        ...prev,
        status: 'error',
        lastError: message
      }))
      toast.error(message)
      console.error(error)
    } finally {
      toast.dismiss(toastId)
      setIsSyncing(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Configuración del Sistema</DialogTitle>
          <DialogDescription>
            Configura la conexión con el backend FastAPI
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div className="rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-sm font-medium">
                  Sincronización Multi-Dispositivo
                </Label>
                <p className="text-xs text-muted-foreground">
                  Configurar sincronización en tiempo real
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onOpenChange(false)
                  onOpenSyncSettings?.()
                }}
              >
                <ArrowsClockwise size={16} className="mr-2" />
                Configurar
              </Button>
            </div>
          </div>

          <div className="rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-sm font-medium">
                  Notificaciones y Alertas
                </Label>
                <p className="text-xs text-muted-foreground">
                  Configurar alertas de stock bajo y notificaciones
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onOpenChange(false)
                  onOpenNotificationSettings?.()
                }}
              >
                <Bell size={16} className="mr-2" />
                Configurar
              </Button>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Label htmlFor="use-api" className="text-sm font-medium">
                  Usar Backend API
                </Label>
                {useApi ? (
                  <Badge variant="default" className="gap-1">
                    <CloudArrowUp size={14} />
                    API
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="gap-1">
                    <Database size={14} />
                    Local
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {useApi 
                  ? 'Conectado al backend FastAPI'
                  : 'Usando almacenamiento local del navegador'
                }
              </p>
            </div>
            <Switch
              id="use-api"
              checked={useApi}
              onCheckedChange={(checked) => {
                setUseApi(checked)
                if (checked) {
                  toast.info('Recarga la página para conectar con el backend')
                } else {
                  toast.info('Recarga la página para usar almacenamiento local')
                }
              }}
            />
          </div>

          {useApi && (
            <>
              <div className="space-y-2">
                <Label htmlFor="api-url">URL del Backend</Label>
                <Input
                  id="api-url"
                  value={localApiUrl}
                  onChange={(e) => setLocalApiUrl(e.target.value)}
                  placeholder="http://localhost:8000/api"
                />
                <p className="text-xs text-muted-foreground">
                  URL base de la API FastAPI
                </p>
              </div>

              {currentUser?.is_superuser && (
                <div className="rounded-lg border p-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-sm font-medium">
                        Gestión de Usuarios
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Administrar usuarios y roles del sistema
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => setShowManageUsers(true)}>
                      <Users className="mr-2 h-4 w-4" />
                      Gestionar
                    </Button>
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  onClick={testConnection}
                  variant="outline"
                  className="flex-1"
                  disabled={isTestingConnection}
                >
                  {isTestingConnection ? 'Probando...' : 'Probar Conexión'}
                </Button>
                
                {connectionStatus === 'success' && (
                  <div className="flex items-center px-3 rounded-md bg-accent text-accent-foreground">
                    <CloudArrowUp size={20} />
                  </div>
                )}
                
                {connectionStatus === 'error' && (
                  <div className="flex items-center px-3 rounded-md bg-destructive text-destructive-foreground">
                    <CloudSlash size={20} />
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-dashed p-4 space-y-3">
                <div>
                  <p className="text-sm font-medium mb-1">Inicializar Backend</p>
                  <p className="text-xs text-muted-foreground mb-3">
                    Carga datos de prueba en el backend (perfiles y productos de ejemplo)
                  </p>
                </div>
                <Button
                  onClick={handleInitializeBackend}
                  variant="secondary"
                  className="w-full"
                  size="sm"
                >
                  Cargar Datos de Prueba
                </Button>
              </div>

              <div className="rounded-lg border border-dashed p-4 space-y-3">
                <div>
                  <p className="text-sm font-medium mb-1">Sincronización</p>
                  <p className="text-xs text-muted-foreground mb-3">
                    Sube tus datos locales (productos, ubicaciones) al servidor.
                  </p>
                </div>
                <Button
                  onClick={handleSyncLocalToRemote}
                  variant="secondary"
                  className="w-full"
                  size="sm"
                  disabled={isSyncing}
                >
                  <ArrowsClockwise className={`mr-2 h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
                  {isSyncing ? 'Sincronizando...' : 'Sincronizar Local -&gt; Nube'}
                </Button>

                {showSyncProgress && (
                  <div className="space-y-2 rounded-md border border-primary/30 bg-primary/5 p-3 text-xs">
                    <div className="flex items-center justify-between font-medium">
                      <span>{syncProgressLabel}</span>
                      <span>{syncProgressPercent}%</span>
                    </div>
                    <Progress value={syncProgressPercent} />
                    {syncProgress.lastEntity && (
                      <p className="text-muted-foreground">
                        Último evento: {syncProgress.lastEntity} · {syncProgress.lastAction}
                      </p>
                    )}
                    {syncProgress.status === 'error' && syncProgress.lastError && (
                      <p className="text-destructive">{syncProgress.lastError}</p>
                    )}
                  </div>
                )}

                {pendingSyncFlag && !isSyncing && (
                  <div className="flex items-center gap-2 rounded-md border border-amber-400/40 bg-amber-50/80 p-3 text-xs text-amber-700">
                    <WarningOctagon size={14} />
                    <span>Hay eventos pendientes por sincronizar. Reintenta cuando estés listo.</span>
                  </div>
                )}
              </div>
            </>
          )}

          <div className="rounded-lg border border-destructive/50 p-4 space-y-3 bg-destructive/5">
            <div>
              <p className="text-sm font-medium mb-1 text-destructive flex items-center gap-2">
                <Trash size={16} />
                Zona de Peligro
              </p>
              <p className="text-xs text-muted-foreground mb-3">
                Elimina todos los datos locales (productos, órdenes, perfiles) y reinicia la aplicación.
              </p>
            </div>
            <Button
              onClick={async () => {
                if (confirm('¿Estás seguro? Esto borrará TODOS los datos locales y no se puede deshacer.')) {
                  await clearAllData()
                  window.location.reload()
                }
              }}
              variant="destructive"
              className="w-full"
              size="sm"
            >
              Borrar Datos Locales y Reiniciar
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSave}>
            Guardar
          </Button>
        </DialogFooter>
      </DialogContent>

      <ManageUsersDialog 
        open={showManageUsers} 
        onOpenChange={setShowManageUsers} 
      />
    </Dialog>
  )
}
