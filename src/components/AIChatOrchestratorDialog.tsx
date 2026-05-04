import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { SalesProfile, Location } from '@/lib/types'
import { sendChatMessage, sendChatMessageAndCreateOrder } from '@/lib/chatOrchestrator'

interface AIChatOrchestratorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  salesProfiles: SalesProfile[]
  locations: Location[]
}

export function AIChatOrchestratorDialog({
  open,
  onOpenChange,
  salesProfiles,
  locations,
}: AIChatOrchestratorDialogProps) {
  const [salesProfileSlug, setSalesProfileSlug] = useState('')
  const [sourceLocationId, setSourceLocationId] = useState<number | null>(null)
  const [customerPhone, setCustomerPhone] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [messageContent, setMessageContent] = useState('')

  const [productQuery, setProductQuery] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [imei, setImei] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento'>('efectivo')

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [lastReply, setLastReply] = useState('')
  const [lastOrderId, setLastOrderId] = useState<number | null>(null)

  useEffect(() => {
    if (!open) return
    if (!salesProfileSlug && salesProfiles.length > 0) {
      const profile = salesProfiles.find(sp => sp.active) || salesProfiles[0]
      setSalesProfileSlug(profile?.slug || '')
    }
    if (!sourceLocationId && locations.length > 0) {
      const location = locations.find(l => l.activo) || locations[0]
      setSourceLocationId(location?.id || null)
    }
  }, [open, salesProfileSlug, sourceLocationId, salesProfiles, locations])

  const validateBase = (): boolean => {
    if (!salesProfileSlug) {
      toast.error('Selecciona un perfil de ventas')
      return false
    }
    if (!customerPhone.trim()) {
      toast.error('Ingresa teléfono del cliente')
      return false
    }
    if (!messageContent.trim()) {
      toast.error('Ingresa el mensaje del cliente')
      return false
    }
    return true
  }

  const handleReplyOnly = async () => {
    if (!validateBase()) return

    setIsSubmitting(true)
    try {
      const result = await sendChatMessage({
        salesProfileSlug,
        customerPhone,
        customerName,
        messageContent,
      })

      setLastReply(result.reply)
      setLastOrderId(null)
      toast.success('Respuesta IA generada')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error desconocido'
      toast.error(`No se pudo generar respuesta: ${message}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReplyAndCreateOrder = async () => {
    if (!validateBase()) return
    if (!sourceLocationId) {
      toast.error('Selecciona ubicación de origen')
      return
    }
    if (!productQuery.trim()) {
      toast.error('Ingresa producto para la orden (product_query)')
      return
    }
    if (quantity < 1) {
      toast.error('Cantidad inválida')
      return
    }

    setIsSubmitting(true)
    try {
      const result = await sendChatMessageAndCreateOrder(
        {
          salesProfileSlug,
          customerPhone,
          customerName,
          messageContent,
        },
        {
          sourceLocationId,
          metodoPago: paymentMethod,
          items: [
            {
              product_query: productQuery,
              cantidad: quantity,
              imeis: imei.trim() ? [imei.trim()] : undefined,
            },
          ],
          autoLinkInteraction: true,
        }
      )

      setLastReply(result.reply)
      setLastOrderId(result.order?.order_id ?? null)

      if (result.order?.order_id) {
        toast.success(`Orden creada: #${result.order.order_id}`)
      } else {
        toast.warning('Respuesta generada, pero no se creó orden')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error desconocido'
      toast.error(`No se pudo completar flujo: ${message}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Chat IA Operativo</DialogTitle>
          <DialogDescription>
            Flujo unificado sin n8n: responder mensaje y opcionalmente crear orden en una sola operación.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Perfil de ventas</Label>
              <Select value={salesProfileSlug} onValueChange={setSalesProfileSlug}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar perfil" />
                </SelectTrigger>
                <SelectContent>
                  {salesProfiles.map(profile => (
                    <SelectItem key={profile.id} value={profile.slug}>
                      {profile.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Ubicación origen (orden)</Label>
              <Select
                value={sourceLocationId ? String(sourceLocationId) : ''}
                onValueChange={(value) => setSourceLocationId(Number(value))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar ubicación" />
                </SelectTrigger>
                <SelectContent>
                  {locations.map(location => (
                    <SelectItem key={location.id} value={String(location.id)}>
                      {location.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Teléfono cliente</Label>
              <Input value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value)} placeholder="50499998888" />
            </div>
            <div className="space-y-1.5">
              <Label>Nombre cliente</Label>
              <Input value={customerName} onChange={(e) => setCustomerName(e.target.value)} placeholder="Cliente Demo" />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Mensaje del cliente</Label>
            <Textarea value={messageContent} onChange={(e) => setMessageContent(e.target.value)} rows={3} placeholder="Hola, quiero un iPhone..." />
          </div>

          <div className="border rounded-md p-3 space-y-3">
            <p className="text-sm font-medium">Datos para crear orden (opcional en botón de cierre)</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="space-y-1.5 md:col-span-2">
                <Label>Producto (query)</Label>
                <Input value={productQuery} onChange={(e) => setProductQuery(e.target.value)} placeholder="iPhone 13" />
              </div>
              <div className="space-y-1.5">
                <Label>Cantidad</Label>
                <Input
                  type="number"
                  min={1}
                  value={String(quantity)}
                  onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>IMEI (si aplica)</Label>
                <Input value={imei} onChange={(e) => setImei(e.target.value)} placeholder="356938035643809" />
              </div>
              <div className="space-y-1.5">
                <Label>Método de pago</Label>
                <Select value={paymentMethod} onValueChange={(value: 'efectivo' | 'transferencia' | 'tarjeta' | 'financiamiento') => setPaymentMethod(value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="efectivo">Efectivo</SelectItem>
                    <SelectItem value="transferencia">Transferencia</SelectItem>
                    <SelectItem value="tarjeta">Tarjeta</SelectItem>
                    <SelectItem value="financiamiento">Financiamiento</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {(lastReply || lastOrderId) && (
            <div className="border rounded-md p-3 space-y-2 bg-muted/40">
              {lastReply && <p className="text-sm"><span className="font-medium">Respuesta IA:</span> {lastReply}</p>}
              {lastOrderId && <p className="text-sm"><span className="font-medium">Orden creada:</span> #{lastOrderId}</p>}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={handleReplyOnly} disabled={isSubmitting}>
              Responder
            </Button>
            <Button onClick={handleReplyAndCreateOrder} disabled={isSubmitting}>
              Responder + Crear orden
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
