import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import type { ChannelHealthResponse } from '@/lib/types'
import { apiClient } from '@/lib/apiClient'

interface ChannelHealthDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ChannelHealthDialog({ open, onOpenChange }: ChannelHealthDialogProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ChannelHealthResponse | null>(null)

  const loadHealth = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getChannelsHealth()
      setResult(response)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error desconocido'
      toast.error(`No se pudo obtener diagnóstico de canales: ${message}`)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!open) return
    loadHealth()
  }, [open])

  const renderChannel = (name: string, ready: boolean, missing: string[]) => (
    <div className="border rounded-md p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="font-medium capitalize">{name}</p>
        <Badge variant={ready ? 'secondary' : 'destructive'}>{ready ? 'Listo' : 'Pendiente'}</Badge>
      </div>
      {!ready && missing.length > 0 && (
        <p className="text-xs text-muted-foreground">Faltan: {missing.join(', ')}</p>
      )}
    </div>
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Diagnóstico de Canales</DialogTitle>
          <DialogDescription>
            Estado de configuración para respuestas automáticas por WhatsApp, Messenger e Instagram.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Estado global:</span>
              <Badge variant={result?.ready ? 'secondary' : 'destructive'}>
                {result?.ready ? 'Ready' : 'Incompleto'}
              </Badge>
            </div>
            <Button variant="outline" onClick={loadHealth} disabled={isLoading}>
              {isLoading ? 'Actualizando...' : 'Actualizar'}
            </Button>
          </div>

          {result && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="border rounded-md p-3 space-y-2">
                  <p className="font-medium">Requisitos globales</p>
                  <p className="text-sm">Verify token: {result.global.has_verify_token ? '✅' : '❌'}</p>
                  <p className="text-sm">Perfil IA por defecto: {result.global.has_default_sales_profile ? '✅' : '❌'}</p>
                  <p className="text-sm">Firma webhook: {result.global.signature_validation_enabled ? '✅' : '⚠️ opcional'}</p>
                  <p className="text-sm">TTL deduplicación: {result.global.message_ttl_seconds}s</p>
                </div>

                <div className="border rounded-md p-3 space-y-2">
                  <p className="font-medium">Pendientes globales</p>
                  {result.global.missing.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Sin pendientes globales</p>
                  ) : (
                    <p className="text-sm text-muted-foreground">{result.global.missing.join(', ')}</p>
                  )}
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {renderChannel('whatsapp', result.channels.whatsapp.ready, result.channels.whatsapp.missing)}
                {renderChannel('messenger', result.channels.messenger.ready, result.channels.messenger.missing)}
                {renderChannel('instagram', result.channels.instagram.ready, result.channels.instagram.missing)}
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
