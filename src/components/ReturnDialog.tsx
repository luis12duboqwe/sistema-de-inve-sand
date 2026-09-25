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
  const [imeis, setImeis] = useState<Record<number, string>>({})
  const [replacementImeis, setReplacementImeis] = useState<Record<number, string>>({})
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const defectiveImeiRefs = useRef<Record<number, HTMLInputElement | null>>({})
  const replacementImeiRefs = useRef<Record<number, HTMLInputElement | null>>({})

  const handleToggleItem = (itemId: number) => {
    setSelectedItems(prev => ({ ...prev, [itemId]: !prev[itemId] }))
    if (!quantities[itemId]) {
      setQuantities(prev => ({ ...prev, [itemId]: 1 }))
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

      const isPhone = item.product?.categoria === 'celular'

      if (isPhone) {
        const defectiveImei = imeis[item.id]?.trim()
        const replacementImei = replacementImeis[item.id]?.trim()

        if (!defectiveImei) {
          toast.error(`Escanea el IMEI del equipo defectuoso para "${item.product?.nombre}"`)
          defectiveImeiRefs.current[item.id]?.focus()
          return
        }
        if (!replacementImei) {
          toast.error(`Escanea el IMEI del equipo de reemplazo para "${item.product?.nombre}"`)
          replacementImeiRefs.current[item.id]?.focus()
          return
        }
        if (defectiveImei === replacementImei) {
          toast.error(`El IMEI defectuoso y el de reemplazo no pueden ser el mismo para "${item.product?.nombre}"`)
          return
        }
      }

      itemsToReturn.push({
        product_id: item.product_id,
        quantity: qty,
        condition: conditions[item.id] || 'defectuoso',
        action: 'warranty_exchange',
        imei: imeis[item.id]?.trim() || undefined,
        replacement_imei: isPhone ? (replacementImeis[item.id]?.trim() || undefined) : undefined,
      })
    }

    if (itemsToReturn.length === 0) {
      toast.error('Selecciona al menos un producto para procesar la garantía')
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
      toast.success('Cambio por garantía procesado exitosamente')
      onSuccess()
      onOpenChange(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al procesar la garantía')
    } finally {
      setIsSubmitting(false)
    }
  }

  const isPhone = (category?: string) => category === 'celular'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Procesar Cambio / Garantía — Orden #{order.id}</DialogTitle>
          <DialogDescription>
            Este flujo solo permite cambio por garantía. No se realizan devoluciones de dinero ni
            crédito en tienda. Para celulares, registra el IMEI defectuoso que entra y el IMEI del
            equipo de reemplazo que sale.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
            Política comercial: venta final sin reembolso. La atención posterior a la venta se
            procesa mediante cambio o garantía.
          </div>

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
                        <Badge variant="outline" className="text-xs">Con IMEI</Badge>
                      )}
                    </div>

                    {selectedItems[item.id] && (
                      <div className="space-y-4 mt-3 pl-1">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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
                              onValueChange={(value: 'nuevo' | 'defectuoso' | 'abierto') =>
                                setConditions(prev => ({ ...prev, [item.id]: value }))
                              }
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="nuevo">Nuevo / Sellado</SelectItem>
                                <SelectItem value="abierto">Abierto / Buen estado</SelectItem>
                                <SelectItem value="defectuoso">Defectuoso / Garantía</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div className="rounded-md border px-3 py-2 text-sm">
                          Acción: <strong>Cambio por garantía</strong>
                        </div>

                        {isPhone(item.product?.categoria) && (
                          <div className="rounded-lg border border-dashed p-3 space-y-3">
                            <p className="text-xs font-semibold uppercase tracking-wide">
                              Registro de IMEIs del cambio
                            </p>

                            <div className="space-y-1.5">
                              <Label className="text-xs">
                                IMEI equipo defectuoso{' '}
                                <span className="text-muted-foreground">(entra)</span>
                              </Label>
                              <div className="flex gap-2">
                                <Input
                                  ref={el => { defectiveImeiRefs.current[item.id] = el }}
                                  placeholder="Escanea o escribe el IMEI del equipo defectuoso"
                                  value={imeis[item.id] || ''}
                                  onChange={e => handleImeiScan(item.id, 'defective', e.target.value)}
                                  onKeyDown={e => {
                                    if (e.key === 'Enter') {
                                      e.preventDefault()
                                      replacementImeiRefs.current[item.id]?.focus()
                                    }
                                  }}
                                  maxLength={17}
                                />
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className="shrink-0"
                                  onClick={() => defectiveImeiRefs.current[item.id]?.focus()}
                                >
                                  Escanear
                                </Button>
                              </div>
                              {imeis[item.id] && (
                                <p className="text-xs text-muted-foreground">
                                  {imeis[item.id].length === 15
                                    ? 'IMEI válido (15 dígitos)'
                                    : `${imeis[item.id].length} dígitos — se esperan 15`}
                                </p>
                              )}
                            </div>

                            <div className="space-y-1.5">
                              <Label className="text-xs">
                                IMEI equipo de reemplazo{' '}
                                <span className="text-muted-foreground">(sale al cliente)</span>
                              </Label>
                              <div className="flex gap-2">
                                <Input
                                  ref={el => { replacementImeiRefs.current[item.id] = el }}
                                  placeholder="Escanea o escribe el IMEI del equipo de reemplazo"
                                  value={replacementImeis[item.id] || ''}
                                  onChange={e => handleImeiScan(item.id, 'replacement', e.target.value)}
                                  maxLength={17}
                                />
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className="shrink-0"
                                  onClick={() => replacementImeiRefs.current[item.id]?.focus()}
                                >
                                  Escanear
                                </Button>
                              </div>
                              {replacementImeis[item.id] && (
                                <p className="text-xs text-muted-foreground">
                                  {replacementImeis[item.id].length === 15
                                    ? 'IMEI válido (15 dígitos)'
                                    : `${replacementImeis[item.id].length} dígitos — se esperan 15`}
                                </p>
                              )}
                            </div>

                            <p className="text-xs text-muted-foreground">
                              Ambos IMEIs quedan en el historial: el defectuoso entra y el reemplazo
                              sale asociado a esta garantía.
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <Label>Motivo del Cambio / Garantía</Label>
            <Textarea
              placeholder="Describe la falla o el motivo del cambio..."
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
            {isSubmitting ? 'Procesando...' : 'Confirmar Cambio / Garantía'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
