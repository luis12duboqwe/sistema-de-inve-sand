import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { Trash, Plus } from '@phosphor-icons/react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { TradeInPolicy } from '@/lib/types'
import { validateTradeInPolicy, type TradeInPolicyDraft } from '@/lib/validation/tradeInPolicySchema'

interface TradeInPoliciesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TradeInPoliciesDialog({ open, onOpenChange }: TradeInPoliciesDialogProps) {
  const [policies, setPolicies] = useState<TradeInPolicy[]>([])
  
  // Form State
  const [newPolicy, setNewPolicy] = useState<TradeInPolicyDraft>({
    rule_type: 'model_rejection',
    pattern: '',
    action: 'reject',
    reason: ''
  })
  type PolicyField = 'rule_type' | 'pattern' | 'action' | 'reason'
  const [formErrors, setFormErrors] = useState<Partial<Record<PolicyField, string>>>({})

  const clearFieldError = (field: PolicyField) => {
    setFormErrors(prev => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  const loadPolicies = async () => {
    try {
      const data = await inventoryServiceInstance.getTradeInPolicies()
      setPolicies(data)
    } catch (error) {
      console.error(error)
      toast.error('Error al cargar políticas')
    }
  }

  useEffect(() => {
    if (open) {
      loadPolicies()
    }
  }, [open])

  const handleCreate = async () => {
    const validation = validateTradeInPolicy(newPolicy)
    if (!validation.ok) {
      const mapped: Partial<Record<PolicyField, string>> = {}
      validation.issues.forEach(issue => {
        if (issue.field && ['rule_type', 'pattern', 'action', 'reason'].includes(issue.field)) {
          mapped[issue.field as PolicyField] = issue.message
        }
      })
      setFormErrors(mapped)
      toast.error(validation.issues[0]?.message ?? 'Revisa la información de la política')
      return
    }

    try {
      await inventoryServiceInstance.createTradeInPolicy({
        ...newPolicy,
        is_active: true
      } as any)
      
      toast.success('Política creada exitosamente')
      setNewPolicy({
        rule_type: 'model_rejection',
        pattern: '',
        action: 'reject',
        reason: ''
      })
      setFormErrors({})
      loadPolicies()
    } catch (error) {
      console.error(error)
      toast.error('Error al crear política')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar esta regla?')) return
    
    try {
      await inventoryServiceInstance.deleteTradeInPolicy(id)
      toast.success('Política eliminada')
      loadPolicies()
    } catch (error) {
      console.error(error)
      toast.error('Error al eliminar política')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px]">
        <DialogHeader>
          <DialogTitle>Configuración de Políticas de Retoma (IA)</DialogTitle>
          <DialogDescription>
            Defina qué marcas o modelos acepta o rechaza el Bot automáticamente.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2 items-end border p-4 rounded-md bg-slate-50 md:grid-cols-5">
            <div className="space-y-2">
              <Label>Tipo de Regla</Label>
              <Select 
                value={newPolicy.rule_type} 
                onValueChange={v => {
                  setNewPolicy({...newPolicy, rule_type: v})
                  clearFieldError('rule_type')
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="model_rejection">Rechazar Modelo</SelectItem>
                  <SelectItem value="brand_rejection">Rechazar Marca</SelectItem>
                  <SelectItem value="condition_rejection">Rechazar Condición</SelectItem>
                </SelectContent>
              </Select>
              {formErrors.rule_type && (
                <p className="text-xs text-red-600">{formErrors.rule_type}</p>
              )}
            </div>
            
            <div className="space-y-2">
              <Label>Patrón (ej. "Xiaomi", "iPhone 7")</Label>
              <Input 
                value={newPolicy.pattern}
                onChange={e => {
                  setNewPolicy({...newPolicy, pattern: e.target.value})
                  clearFieldError('pattern')
                }}
                placeholder="Texto a buscar..."
              />
              {formErrors.pattern && (
                <p className="text-xs text-red-600">{formErrors.pattern}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Acción al Coincidir</Label>
              <Select
                value={newPolicy.action}
                onValueChange={value => {
                  setNewPolicy({ ...newPolicy, action: value })
                  clearFieldError('action')
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="reject">Rechazar automático</SelectItem>
                  <SelectItem value="review">Marcar para revisión</SelectItem>
                  <SelectItem value="allow">Permitir (marca blanca)</SelectItem>
                </SelectContent>
              </Select>
              {formErrors.action && (
                <p className="text-xs text-red-600">{formErrors.action}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Razón (Opcional)</Label>
              <Input 
                value={newPolicy.reason}
                onChange={e => {
                  setNewPolicy({...newPolicy, reason: e.target.value})
                  clearFieldError('reason')
                }}
                placeholder="Por qué se rechaza..."
              />
              {formErrors.reason && (
                <p className="text-xs text-red-600">{formErrors.reason}</p>
              )}
            </div>

            <Button onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Agregar Regla
            </Button>
          </div>

          <div className="border rounded-md max-h-[400px] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Patrón</TableHead>
                  <TableHead>Acción</TableHead>
                  <TableHead>Razón</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      No hay reglas definidas. Se usarán las reglas por defecto (Solo iPhone/Samsung).
                    </TableCell>
                  </TableRow>
                ) : (
                  policies.map((policy) => (
                    <TableRow key={policy.id}>
                      <TableCell>
                        <Badge variant="outline">{policy.rule_type}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{policy.pattern}</TableCell>
                      <TableCell>
                        <Badge variant={policy.action === 'reject' ? 'destructive' : 'default'}>
                          {policy.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {policy.reason || '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => handleDelete(policy.id)}
                        >
                          <Trash className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
