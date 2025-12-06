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
import { useKV } from '@github/spark/hooks'
import { Database, CloudArrowUp, CloudSlash, Bell, ArrowsClockwise } from '@phosphor-icons/react'
import { apiClient } from '@/lib/apiClient'
import { toast } from 'sonner'

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onOpenNotificationSettings?: () => void
  onOpenSyncSettings?: () => void
}

export function SettingsDialog({ open, onOpenChange, onOpenNotificationSettings, onOpenSyncSettings }: SettingsDialogProps) {
  const [apiUrl, setApiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')
  const [useApi, setUseApi] = useKV<boolean>('settings_use_api', false)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [localApiUrl, setLocalApiUrl] = useState('')

  useEffect(() => {
    if (apiUrl) {
      setLocalApiUrl(apiUrl)
    }
  }, [apiUrl])

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
            </>
          )}
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
    </Dialog>
  )
}
