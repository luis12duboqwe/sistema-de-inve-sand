import { useState, useEffect, useCallback } from 'react'
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
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  CheckCircle,
  Clock,
  CurrencyDollar,
  LockKey,
  ShoppingCart,
  Warning,
  X,
} from '@phosphor-icons/react'
import { toast } from 'sonner'
import { apiClient } from '@/lib/apiClient'
import { motion, AnimatePresence } from 'framer-motion'
import type { Location } from '@/lib/types'

interface DailyCloseOrder {
  id: number
  customer_name: string
  customer_phone: string
  canal: string
  metodo_pago: string
  total: number
  estado: string
  source_location_id?: number
  source_location_name?: string
  created_at: string
  items_count: number
  items_summary: string
}

interface DailyCloseDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onValidated?: () => void
}

const CANAL_LABELS: Record<string, string> = {
  whatsapp: 'WhatsApp',
  facebook: 'Facebook',
  instagram: 'Instagram',
  tienda: 'Tienda',
}

const PAGO_LABELS: Record<string, string> = {
  efectivo: 'Efectivo',
  transferencia: 'Transferencia',
  tarjeta: 'Tarjeta',
  financiamiento: 'Financiamiento',
}

export function DailyCloseDialog({ open, onOpenChange, onValidated }: DailyCloseDialogProps) {
  const [pendingOrders, setPendingOrders] = useState<DailyCloseOrder[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState('all')
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [validationCode, setValidationCode] = useState('')
  const [notas, setNotas] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isValidating, setIsValidating] = useState(false)
  const [codeConfigured, setCodeConfigured] = useState<boolean | null>(null)
  const [showResult, setShowResult] = useState(false)
  const [resultData, setResultData] = useState<{
    validated_count: number
    total_ventas: number
    mensaje: string
  } | null>(null)

  const loadPendingOrders = useCallback(async () => {
    setIsLoading(true)
    try {
      const locationId = selectedLocationId === 'all' ? undefined : Number(selectedLocationId)
      const [ordersData, configData, locationsData] = await Promise.all([
        apiClient.getDailyClosePending(locationId),
        apiClient.getDailyCloseConfig(),
        apiClient.listLocations(true),
      ])
      setPendingOrders(ordersData)
      setLocations(locationsData)
      setSelectedIds(new Set(ordersData.map((o: DailyCloseOrder) => o.id)))
      setCodeConfigured(configData.configured)
    } catch {
      toast.error('Error al cargar las órdenes pendientes')
    } finally {
      setIsLoading(false)
    }
  }, [selectedLocationId])

  useEffect(() => {
    if (open) {
      loadPendingOrders()
      setValidationCode('')
      setNotas('')
      setShowResult(false)
      setResultData(null)
    }
  }, [open, loadPendingOrders])

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === pendingOrders.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(pendingOrders.map(o => o.id)))
    }
  }

  const totalSelected = pendingOrders
    .filter(o => selectedIds.has(o.id))
    .reduce((sum, o) => sum + o.total, 0)

  const totalPending = pendingOrders.reduce((sum, order) => sum + order.total, 0)
  const totalItemsPending = pendingOrders.reduce((sum, order) => sum + order.items_count, 0)
  const averageTicket = pendingOrders.length > 0 ? totalPending / pendingOrders.length : 0
  const oldestPendingOrder = pendingOrders[0]

  const paymentBreakdown = pendingOrders.reduce<Record<string, { count: number; total: number }>>((acc, order) => {
    const key = order.metodo_pago
    const current = acc[key] ?? { count: 0, total: 0 }
    current.count += 1
    current.total += order.total
    acc[key] = current
    return acc
  }, {})

  const handleValidate = async () => {
    if (!validationCode.trim()) {
      toast.error('Ingrese el código de validación')
      return
    }
    if (selectedIds.size === 0) {
      toast.error('Seleccione al menos una orden para validar')
      return
    }

    setIsValidating(true)
    try {
      const result = await apiClient.validateDailyClose({
        validation_code: validationCode,
        order_ids: Array.from(selectedIds),
        location_id: selectedLocationId === 'all' ? undefined : Number(selectedLocationId),
        notas: notas || undefined,
      })

      setResultData(result)
      setShowResult(true)
      onValidated?.()
      toast.success(`${result.validated_count} ventas validadas exitosamente`)
    } catch (err: any) {
      const msg = err?.message || 'Error al validar el cierre de día'
      if (msg.includes('incorrecto') || msg.includes('403')) {
        toast.error('Código de validación incorrecto', {
          description: 'Verifique el código configurado en Ajustes.',
        })
      } else if (msg.includes('no está configurado')) {
        toast.error('Código no configurado', {
          description: 'Configure el código de validación en Ajustes → Cierre de Día.',
        })
      } else {
        toast.error(msg)
      }
    } finally {
      setIsValidating(false)
    }
  }

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleString('es-HN', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <CheckCircle size={22} className="text-emerald-500" weight="fill" />
            Cierre de Día — Validar Ventas
          </DialogTitle>
          <DialogDescription>
            Revise las ventas completadas del día, ingrese el código de validación y confirme.
            Solo las ventas validadas quedan registradas como definitivas en el historial.
          </DialogDescription>
        </DialogHeader>

        <AnimatePresence mode="wait">
          {showResult && resultData ? (
            <motion.div
              key="result"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex-1 flex flex-col items-center justify-center gap-4 py-8 text-center"
            >
              <CheckCircle size={64} className="text-emerald-500" weight="fill" />
              <h3 className="text-xl font-semibold text-emerald-600">¡Cierre de día completado!</h3>
              <div className="grid grid-cols-2 gap-4 w-full max-w-xs">
                <div className="bg-muted rounded-lg p-3">
                  <p className="text-2xl font-bold">{resultData.validated_count}</p>
                  <p className="text-xs text-muted-foreground">Ventas validadas</p>
                </div>
                <div className="bg-muted rounded-lg p-3">
                  <p className="text-2xl font-bold text-emerald-600">
                    {resultData.total_ventas.toLocaleString('es-HN', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-muted-foreground">Total confirmado (Lps)</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground max-w-sm">{resultData.mensaje}</p>
              <Button onClick={() => onOpenChange(false)} className="mt-2">
                Cerrar
              </Button>
            </motion.div>
          ) : (
            <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex-1 flex flex-col gap-4 min-h-0">
              {/* Estado del código */}
              {codeConfigured === false && (
                <div className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
                  <Warning size={16} weight="fill" />
                  El código de validación no está configurado. Vaya a <strong>Ajustes → Cierre de Día</strong> para configurarlo.
                </div>
              )}

              <div className="grid gap-1.5">
                <Label htmlFor="daily-close-location" className="text-sm text-muted-foreground">
                  Ubicación
                </Label>
                <Select value={selectedLocationId} onValueChange={setSelectedLocationId}>
                  <SelectTrigger id="daily-close-location" className="w-full">
                    <SelectValue placeholder="Todas las ubicaciones accesibles" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas las ubicaciones accesibles</SelectItem>
                    {locations.map(location => (
                      <SelectItem key={location.id} value={String(location.id)}>
                        {location.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Lista de órdenes */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShoppingCart size={16} />
                  <span className="text-sm font-medium">
                    Órdenes completadas pendientes ({pendingOrders.length})
                  </span>
                </div>
                {pendingOrders.length > 0 && (
                  <Button variant="ghost" size="sm" onClick={toggleSelectAll}>
                    {selectedIds.size === pendingOrders.length ? 'Deseleccionar todo' : 'Seleccionar todo'}
                  </Button>
                )}
              </div>

              {pendingOrders.length > 0 && (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <div className="rounded-md border bg-muted/30 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Pendientes</p>
                    <p className="mt-1 text-xl font-semibold">{pendingOrders.length}</p>
                    <p className="text-xs text-muted-foreground">Ventas por validar</p>
                  </div>
                  <div className="rounded-md border bg-muted/30 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto total</p>
                    <p className="mt-1 text-xl font-semibold text-emerald-600">
                      Lps {totalPending.toLocaleString('es-HN', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-xs text-muted-foreground">Suma de órdenes pendientes</p>
                  </div>
                  <div className="rounded-md border bg-muted/30 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Items</p>
                    <p className="mt-1 text-xl font-semibold">{totalItemsPending}</p>
                    <p className="text-xs text-muted-foreground">Unidades registradas en total</p>
                  </div>
                  <div className="rounded-md border bg-muted/30 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Ticket promedio</p>
                    <p className="mt-1 text-xl font-semibold">
                      Lps {averageTicket.toLocaleString('es-HN', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {oldestPendingOrder ? `Más antigua: ${formatDate(oldestPendingOrder.created_at)}` : 'Sin órdenes'}
                    </p>
                  </div>
                </div>
              )}

              {pendingOrders.length > 0 && Object.keys(paymentBreakdown).length > 0 && (
                <div className="rounded-md border bg-background p-3">
                  <p className="text-sm font-medium">Desglose por método de pago</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {Object.entries(paymentBreakdown).map(([method, data]) => (
                      <span key={method} className="rounded-full border px-2 py-1">
                        {PAGO_LABELS[method] ?? method}: {data.count} venta(s) · Lps {data.total.toLocaleString('es-HN', { minimumFractionDigits: 2 })}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {isLoading ? (
                <div className="text-center text-muted-foreground py-8 text-sm">Cargando órdenes...</div>
              ) : pendingOrders.length === 0 ? (
                <div className="text-center text-muted-foreground py-8 text-sm">
                  <Clock size={32} className="mx-auto mb-2 opacity-40" />
                  No hay ventas completadas pendientes de validación.
                </div>
              ) : (
                <ScrollArea className="flex-1 border rounded-md max-h-52">
                  <div className="divide-y">
                    {pendingOrders.map(order => (
                      <div
                        key={order.id}
                        className={`flex items-start gap-3 p-3 cursor-pointer hover:bg-muted/50 transition-colors ${
                          selectedIds.has(order.id) ? 'bg-emerald-50 dark:bg-emerald-900/10' : ''
                        }`}
                        onClick={() => toggleSelect(order.id)}
                      >
                        <Checkbox
                          checked={selectedIds.has(order.id)}
                          onCheckedChange={() => toggleSelect(order.id)}
                          onClick={e => e.stopPropagation()}
                          className="mt-0.5"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <div className="min-w-0">
                              <span className="font-medium text-sm truncate block">
                                #{order.id} — {order.customer_name}
                              </span>
                              <span className="text-xs text-muted-foreground block truncate">
                                {order.customer_phone || 'Sin teléfono'}
                              </span>
                            </div>
                            <div className="text-right shrink-0">
                              <span className="font-semibold text-sm text-emerald-600 block">
                                Lps {order.total.toLocaleString('es-HN', { minimumFractionDigits: 2 })}
                              </span>
                              <Badge variant="outline" className="mt-1 text-[11px] px-1.5 py-0">
                                {order.estado}
                              </Badge>
                            </div>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {order.items_count} item(s) · {order.items_summary}
                          </p>
                          <div className="flex gap-1 mt-2 flex-wrap">
                            <Badge variant="secondary" className="text-xs px-1.5 py-0">
                              {CANAL_LABELS[order.canal] ?? order.canal}
                            </Badge>
                            <Badge variant="outline" className="text-xs px-1.5 py-0">
                              {PAGO_LABELS[order.metodo_pago] ?? order.metodo_pago}
                            </Badge>
                            {order.source_location_name && (
                              <Badge variant="outline" className="text-xs px-1.5 py-0">
                                {order.source_location_name}
                              </Badge>
                            )}
                            <Badge variant="outline" className="text-xs px-1.5 py-0">
                              {formatDate(order.created_at)}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}

              {/* Resumen de selección */}
              {selectedIds.size > 0 && (
                <div className="flex items-center justify-between rounded-md bg-emerald-50 dark:bg-emerald-900/20 px-3 py-2 text-sm">
                  <span className="text-muted-foreground">
                    {selectedIds.size} venta(s) seleccionada(s)
                  </span>
                  <span className="font-semibold text-emerald-600 flex items-center gap-1">
                    <CurrencyDollar size={14} weight="bold" />
                    Lps {totalSelected.toLocaleString('es-HN', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              )}

              {/* Código de validación */}
              <div className="grid gap-1.5">
                <Label htmlFor="val-code" className="flex items-center gap-1.5 text-sm">
                  <LockKey size={14} weight="bold" />
                  Código de validación (admin)
                </Label>
                <Input
                  id="val-code"
                  type="password"
                  placeholder="Ingrese el código de validación"
                  value={validationCode}
                  onChange={e => setValidationCode(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleValidate()}
                  autoComplete="off"
                />
              </div>

              {/* Notas opcionales */}
              <div className="grid gap-1.5">
                <Label htmlFor="val-notas" className="text-sm text-muted-foreground">
                  Notas del cierre (opcional)
                </Label>
                <Textarea
                  id="val-notas"
                  placeholder="Ej: Todo cuadra, se verificó cada venta..."
                  value={notas}
                  onChange={e => setNotas(e.target.value)}
                  rows={2}
                  className="resize-none"
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!showResult && (
          <DialogFooter className="gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isValidating}>
              <X size={16} className="mr-1" /> Cancelar
            </Button>
            <Button
              onClick={handleValidate}
              disabled={
                isValidating ||
                isLoading ||
                selectedIds.size === 0 ||
                !validationCode.trim() ||
                pendingOrders.length === 0
              }
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {isValidating ? (
                'Validando...'
              ) : (
                <>
                  <CheckCircle size={16} className="mr-1" weight="fill" />
                  Validar {selectedIds.size > 0 ? `${selectedIds.size} Venta(s)` : ''}
                </>
              )}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
