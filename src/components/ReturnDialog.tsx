import { useState, useRef, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { calculateLuhnCheckDigit } from '@/lib/utils'
import type { OrderWithItems, CreateReturnRequest, ReturnItem } from '@/lib/types'

interface ReturnDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  order: OrderWithItems
  onSuccess: () => void
}

/** Normaliza un valor de scanner: completa IMEI de 14 dígitos con dígito Luhn. */
function normalizeImeiInput(raw: string): string {
  const digits = raw.replace(/\D/g, '')
  if (digits.length === 14) {
    return digits + calculateLuhnCheckDigit(digits)
  }
  return digits
}

export function ReturnDialog({ open, onOpenChange, order, onSuccess }: ReturnDialogProps) {
  const [selectedItems, setSelectedItems] = useState<Record<number, boolean>>({})
  const [quantities, setQuantities] = useState<Record<number, number>>({})
  const [conditions, setConditions] = useState<Record<number, 'nuevo' | 'defectuoso' | 'abierto'>>({})
  const [actions, setActions] = useState<Record<number, 'refund' | 'warranty_exchange' | 'store_credit'>>({})
  // IMEI del equipo defectuoso que entra (devuelta por el cliente)
  const [imeis, setImeis] = useState<Record<number, string>>({})
  // IMEI del equipo de reemplazo que sale (solo warranty_exchange)
  const [replacementImeis, setReplacementImeis] = useState<Record<number, string>>({})
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Refs para enfocar scanner inputs
  const defectiveImeiRefs = useRef<Record<number, HTMLInputElement | null>>({})
  const replacementImeiRefs = useRef<Record<number, HTMLInputElement | null>>({})

  const handleToggleItem = (itemId: number) => {
    setSelectedItems(prev => ({ ...prev, [itemId]: !prev[itemId] }))
    if (!quantities[itemId]) {
      setQuantities(prev => ({ ...prev, [itemId]: 1 }))
      setConditions(prev => ({ ...prev, [itemId]: 'defectuoso' }))
      setActions(prev => ({ ...prev, [itemId]: 'refund' }))
    }
  }

  const handleActionChange = (itemId: number, value: 'refund' | 'warranty_exchange' | 'store_credit') => {
    setActions(prev => ({ ...prev, [itemId]: value }))
    // Limpiar replacement_imei si se cambia de warranty_exchange a otra acción
    if (value !== 'warranty_exchange') {
      setReplacementImeis(prev => { const next = { ...prev }; delete next[itemId]; return next })
    }
    // Auto-set condición a 'defectuoso' para garantías
    if (value === 'warranty_exchange') {
      setConditions(prev => ({ ...prev, [itemId]: 'defectuoso' }))
    }
  }

  const handleImeiScan = useCallback((
    itemId: number,
    field: 'defective' | 'replacement',
    rawValue: string
  ) => {
    const normalized = normalizeImeiInput(rawValue)
    if (field === 'defective') {
      setImeis(prev => ({ ...prev, [itemId]: normalized }))
    } else {
      setReplacementImeis(prev => ({ ...prev, [itemId]: normalized }))
    }
  }, [])

  const handleSubmit = async () => {
    const itemsToReturn: ReturnItem[] = []

    for (const item of order.items) {
      if (!selectedItems[item.id]) continue

      const qty = quantities[item.id] || 1
      if (qty > item.cantidad) {
        toast.error(`Cantidad inválida para ${item.product?.nombre}`)
        return
      }

      const action = actions[item.id] || 'refund'
      const isWarrantyExchange = action === 'warranty_exchange'
      const isPhone = item.product?.categoria === 'celular'

      // Validar que se proporcionaron los IMEIs necesarios para garantías de celulares
      if (isWarrantyExchange && isPhone) {
        const defImei = imeis[item.id]?.trim()
        const replImei = replacementImeis[item.id]?.trim()

        if (!defImei) {
          toast.error(`Escanea el IMEI del equipo defectuoso para "${item.product?.nombre}"`)
          defectiveImeiRefs.current[item.id]?.focus()
          return
        }
        if (!replImei) {
          toast.error(`Escanea el IMEI del equipo de reemplazo para "${item.product?.nombre}"`)
          replacementImeiRefs.current[item.id]?.focus()
          return
        }
        if (defImei === replImei) {
          toast.error(`El IMEI defectuoso y el de reemplazo no pueden ser el mismo para "${item.product?.nombre}"`)
          return
        }
      }

      itemsToReturn.push({
        product_id: item.product_id,
        quantity: qty,
        condition: conditions[item.id] || 'defectuoso',
        action,
        imei: imeis[item.id]?.trim() || undefined,
        replacement_imei: isWarrantyExchange ? (replacementImeis[item.id]?.trim() || undefined) : undefined,
      })
    }

    if (itemsToReturn.length === 0) {
      toast.error('Selecciona al menos un producto para devolver')
      return
    }

    setIsSubmitting(true)
    try {
      const returnData: CreateReturnRequest = {
        order_id: order.id,
        reason,
        created_by: 'Usuario Actual',
        items: itemsToReturn,
      }

      await inventoryServiceInstance.createReturn(returnData)
      toast.success('Devolución procesada exitosamente')
      onSuccess()
      onOpenChange(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al procesar devolución')
    } finally {
      setIsSubmitting(false)
    }
  }

  const isPhone = (categoría?: string) => categoría === 'celular'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Procesar Devolución / Garantía — Orden #{order.id}</DialogTitle>
          <DialogDescription>
            Selecciona los productos a devolver y especifica la condición y acción. Para cambios
            por garantía en celulares, escanea ambos IMEIs (el defectuoso que entra y el de
            reemplazo que sale).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-4">
            <Label>Productos de la Orden</Label>
            {order.items.map(item => (
              <div key={item.id} className="border rounded-lg p-4 space-y-3 bg-card">
                <div className="flex items-start gap-3">
                  <Checkbox
                    checked={selectedItems[item.id] || false}
                    onCheckedChange={() => handleToggleItem(item.id)}
                    id={`item-${item.id}`}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Label htmlFor={`item-${item.id}`} className="font-medium cursor-pointer">
                        {item.product?.nombre}
                      </Label>
                      <span className="text-xs text-muted-foreground">
                        (Comprados: {item.cantidad})
                      </span>
                      {isPhone(item.product?.categoria) && (
                        <Badge variant="outline" className="text-xs">📱 Con IMEI</Badge>
                      )}
                    </div>

                    {selectedItems[item.id] && (
                      <div className="space-y-4 mt-3 pl-1">
                        {/* Fila 1: Cantidad + Condición + Acción */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Cantidad</Label>
                            <Input
                              type="number"
                              min="1"
                              max={item.cantidad}
                              value={quantities[item.id] || 1}
                              onChange={e =>
                                setQuantities(prev => ({
                                  ...prev,
                                  [item.id]: parseInt(e.target.value) || 1,
                                }))
                              }
                            />
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Condición</Label>
                            <Select
                              value={conditions[item.id] || 'defectuoso'}
                              onValueChange={(v: any) =>
                                setConditions(prev => ({ ...prev, [item.id]: v }))
                              }
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="nuevo">🟢 Nuevo (Sellado)</SelectItem>
                                <SelectItem value="abierto">🟡 Abierto (Buen estado)</SelectItem>
                                <SelectItem value="defectuoso">🔴 Defectuoso (Garantía)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs text-muted-foreground">Acción</Label>
                            <Select
                              value={actions[item.id] || 'refund'}
                              onValueChange={(v: any) => handleActionChange(item.id, v)}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="refund">💵 Reembolso</SelectItem>
                                <SelectItem value="warranty_exchange">🔄 Cambio por Garantía</SelectItem>
                                <SelectItem value="store_credit">🎟️ Crédito en Tienda</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        {/* IMEI section — solo para celulares */}
                        {isPhone(item.product?.categoria) && (
                          <>
                            {actions[item.id] === 'warranty_exchange' ? (
                              /* Cambio por garantía: dos IMEIs */
                              <div className="rounded-lg border border-dashed border-amber-300 bg-amber-50/60 dark:bg-amber-950/20 p-3 space-y-3">
                                <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wide">
                                  🔄 Cambio por Garantía — Registro de IMEIs
                                </p>

                                {/* IMEI del equipo defectuoso (entra) */}
                                <div className="space-y-1.5">
                                  <Label className="text-xs">
                                    📥 IMEI equipo defectuoso{' '}
                                    <span className="text-muted-foreground">(que entra al inventario)</span>
                                  </Label>
                                  <div className="flex gap-2">
                                    <Input
                                      ref={el => { defectiveImeiRefs.current[item.id] = el }}
                                      placeholder="Escanea o escribe el IMEI del equipo defectuoso"
                                      value={imeis[item.id] || ''}
                                      onChange={e =>
                                        handleImeiScan(item.id, 'defective', e.target.value)
                                      }
                                      onKeyDown={e => {
                                        if (e.key === 'Enter') {
                                          e.preventDefault()
                                          replacementImeiRefs.current[item.id]?.focus()
                                        }
                                      }}
                                      className={
                                        imeis[item.id]?.length === 15
                                          ? 'border-green-400 focus-visible:ring-green-400'
                                          : ''
                                      }
                                      maxLength={17}
                                    />
                                    <Button
                                      type="button"
                                      variant="outline"
                                      size="sm"
                                      className="shrink-0"
                                      onClick={() => defectiveImeiRefs.current[item.id]?.focus()}
                                    >
                                      📷
                                    </Button>
                                  </div>
                                  {imeis[item.id] && (
                                    <p className="text-xs text-muted-foreground">
                                      {imeis[item.id].length === 15
                                        ? '✅ IMEI válido (15 dígitos)'
                                        : `⚠️ ${imeis[item.id].length} dígitos — se esperan 15`}
                                    </p>
                                  )}
                                </div>

                                {/* IMEI del equipo de reemplazo (sale) */}
                                <div className="space-y-1.5">
                                  <Label className="text-xs">
                                    📤 IMEI equipo de reemplazo{' '}
                                    <span className="text-muted-foreground">(que sale al cliente)</span>
                                  </Label>
                                  <div className="flex gap-2">
                                    <Input
                                      ref={el => { replacementImeiRefs.current[item.id] = el }}
                                      placeholder="Escanea o escribe el IMEI del equipo nuevo"
                                      value={replacementImeis[item.id] || ''}
                                      onChange={e =>
                                        handleImeiScan(item.id, 'replacement', e.target.value)
                                      }
                                      className={
                                        replacementImeis[item.id]?.length === 15
                                          ? 'border-blue-400 focus-visible:ring-blue-400'
                                          : ''
                                      }
                                      maxLength={17}
                                    />
                                    <Button
                                      type="button"
                                      variant="outline"
                                      size="sm"
                                      className="shrink-0"
                                      onClick={() => replacementImeiRefs.current[item.id]?.focus()}
                                    >
                                      📷
                                    </Button>
                                  </div>
                                  {replacementImeis[item.id] && (
                                    <p className="text-xs text-muted-foreground">
                                      {replacementImeis[item.id].length === 15
                                        ? '✅ IMEI válido (15 dígitos)'
                                        : `⚠️ ${replacementImeis[item.id].length} dígitos — se esperan 15`}
                                    </p>
                                  )}
                                </div>

                                <p className="text-xs text-amber-600 dark:text-amber-400">
                                  ℹ️ Ambos IMEIs quedan registrados en el historial. El equipo
                                  defectuoso se marca como devuelto y el de reemplazo como vendido.
                                </p>
                              </div>
                            ) : (
                              /* Reembolso / crédito: solo un IMEI opcional */
                              <div className="space-y-1.5">
                                <Label className="text-xs text-muted-foreground">
                                  IMEI del equipo a devolver (opcional)
                                </Label>
                                <div className="flex gap-2">
                                  <Input
                                    ref={el => { defectiveImeiRefs.current[item.id] = el }}
                                    placeholder="Escanea o escribe el IMEI"
                                    value={imeis[item.id] || ''}
                                    onChange={e =>
                                      handleImeiScan(item.id, 'defective', e.target.value)
                                    }
                                    className={
                                      imeis[item.id]?.length === 15
                                        ? 'border-green-400 focus-visible:ring-green-400'
                                        : ''
                                    }
                                    maxLength={17}
                                  />
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="shrink-0"
                                    onClick={() => defectiveImeiRefs.current[item.id]?.focus()}
                                  >
                                    📷
                                  </Button>
                                </div>
                                {imeis[item.id] && (
                                  <p className="text-xs text-muted-foreground">
                                    {imeis[item.id].length === 15
                                      ? '✅ IMEI válido (15 dígitos)'
                                      : `⚠️ ${imeis[item.id].length} dígitos — se esperan 15`}
                                  </p>
                                )}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <Label>Motivo de la Devolución</Label>
            <Textarea
              placeholder="Explica por qué se realiza la devolución..."
              value={reason}
              onChange={e => setReason(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Procesando...' : 'Confirmar Devolución'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
