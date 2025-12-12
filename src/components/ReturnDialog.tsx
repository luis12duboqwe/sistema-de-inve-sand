import { useState } from 'react'
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
import { toast } from 'sonner'
import { apiClient } from '@/lib/apiClient'
import type { OrderWithItems, CreateReturnRequest, ReturnItem } from '@/lib/types'

interface ReturnDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  order: OrderWithItems
  onSuccess: () => void
}

export function ReturnDialog({ open, onOpenChange, order, onSuccess }: ReturnDialogProps) {
  const [selectedItems, setSelectedItems] = useState<Record<number, boolean>>({})
  const [quantities, setQuantities] = useState<Record<number, number>>({})
  const [conditions, setConditions] = useState<Record<number, 'nuevo' | 'defectuoso' | 'abierto'>>({})
  const [actions, setActions] = useState<Record<number, 'refund' | 'warranty_exchange' | 'store_credit'>>({})
  const [imeis, setImeis] = useState<Record<number, string>>({})
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleToggleItem = (itemId: number) => {
    setSelectedItems(prev => ({ ...prev, [itemId]: !prev[itemId] }))
    if (!quantities[itemId]) {
      setQuantities(prev => ({ ...prev, [itemId]: 1 }))
      setConditions(prev => ({ ...prev, [itemId]: 'nuevo' }))
      setActions(prev => ({ ...prev, [itemId]: 'refund' }))
    }
  }

  const handleSubmit = async () => {
    const itemsToReturn: ReturnItem[] = []
    
    for (const item of order.items) {
      if (selectedItems[item.id]) {
        const qty = quantities[item.id] || 1
        if (qty > item.cantidad) {
          toast.error(`Cantidad inválida para ${item.product?.nombre}`)
          return
        }
        
        itemsToReturn.push({
          product_id: item.product_id,
          quantity: qty,
          condition: conditions[item.id] || 'nuevo',
          action: actions[item.id] || 'refund',
          imei: imeis[item.id] || undefined
        })
      }
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
        created_by: 'Usuario Actual', // Idealmente obtener del contexto de auth
        items: itemsToReturn
      }

      await apiClient.createReturn(returnData)
      toast.success('Devolución procesada exitosamente')
      onSuccess()
      onOpenChange(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al procesar devolución')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Procesar Devolución / Garantía - Orden #{order.id}</DialogTitle>
          <DialogDescription>
            Selecciona los productos a devolver y especifica la condición y acción a tomar.
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
                    <Label htmlFor={`item-${item.id}`} className="font-medium cursor-pointer">
                      {item.product?.nombre} (Comprados: {item.cantidad})
                    </Label>
                    
                    {selectedItems[item.id] && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3 pl-1">
                        <div className="space-y-2">
                          <Label className="text-xs">Cantidad a Devolver</Label>
                          <Input 
                            type="number" 
                            min="1" 
                            max={item.cantidad}
                            value={quantities[item.id] || 1}
                            onChange={e => setQuantities(prev => ({ ...prev, [item.id]: parseInt(e.target.value) }))}
                          />
                        </div>

                        <div className="space-y-2">
                          <Label className="text-xs">Condición</Label>
                          <Select 
                            value={conditions[item.id] || 'nuevo'} 
                            onValueChange={(v: any) => setConditions(prev => ({ ...prev, [item.id]: v }))}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="nuevo">Nuevo (Sellado)</SelectItem>
                              <SelectItem value="abierto">Abierto (Buen estado)</SelectItem>
                              <SelectItem value="defectuoso">Defectuoso (Garantía)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label className="text-xs">Acción</Label>
                          <Select 
                            value={actions[item.id] || 'refund'} 
                            onValueChange={(v: any) => setActions(prev => ({ ...prev, [item.id]: v }))}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="refund">Reembolso (Devolver dinero)</SelectItem>
                              <SelectItem value="warranty_exchange">Cambio por Garantía</SelectItem>
                              <SelectItem value="store_credit">Crédito en Tienda</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {item.product?.categoria === 'celular' && (
                          <div className="space-y-2">
                            <Label className="text-xs">IMEI (Opcional)</Label>
                            <Input 
                              placeholder="Escanear IMEI"
                              value={imeis[item.id] || ''}
                              onChange={e => setImeis(prev => ({ ...prev, [item.id]: e.target.value }))}
                            />
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
            <Label>Motivo de la Devolución</Label>
            <Textarea 
              placeholder="Explica por qué se realiza la devolución..."
              value={reason}
              onChange={e => setReason(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Procesando...' : 'Confirmar Devolución'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
