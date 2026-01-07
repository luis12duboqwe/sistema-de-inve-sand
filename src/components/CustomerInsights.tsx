import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Badge } from './ui/badge'
import { Textarea } from './ui/textarea'
import { Switch } from './ui/switch'
import { apiClient } from '../lib/apiClient'
import { Customer } from '../lib/types'
import { toast } from 'sonner'
import { Spinner, User, ShieldWarning, Chat, MagnifyingGlass } from '@phosphor-icons/react'

interface CustomerInsightsProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CustomerInsights({ open, onOpenChange }: CustomerInsightsProps) {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    if (open) {
      loadCustomers()
    }
  }, [open])

  const loadCustomers = async (searchTerm = '') => {
    setLoading(true)
    try {
      const data = await apiClient.getCustomers(searchTerm)
      setCustomers(data)
    } catch {
      toast.error('Error al cargar clientes')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadCustomers(search)
  }

  const handleUpdateStatus = async (updates: Partial<Customer>) => {
    if (!selectedCustomer) return
    setUpdating(true)
    try {
      await apiClient.updateCustomer(selectedCustomer.id, updates)
      
      // Actualizar estado local
      const updated = { ...selectedCustomer, ...updates }
      setSelectedCustomer(updated)
      setCustomers(prev => prev.map(c => c.id === updated.id ? updated : c))
      
      toast.success('Estado del cliente actualizado')
    } catch {
      toast.error('Error al actualizar cliente')
    } finally {
      setUpdating(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="h-5 w-5 text-blue-600" />
            Insights de Clientes & Gestión de Trolls
          </DialogTitle>
          <DialogDescription>
            Gestiona la reputación de tus clientes y detecta comportamientos abusivos.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-1 gap-6 overflow-hidden mt-4">
          {/* Lista y Búsqueda */}
          <div className="w-1/3 flex flex-col gap-4 border-r pr-4">
            <form onSubmit={handleSearch} className="flex gap-2">
              <Input
                placeholder="Buscar por teléfono o nombre..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <Button type="submit" size="icon" variant="secondary">
                <MagnifyingGlass className="h-4 w-4" />
              </Button>
            </form>

            <div className="flex-1 overflow-y-auto space-y-2">
              {loading ? (
                <div className="flex justify-center py-8">
                  <Spinner className="h-6 w-6 animate-spin text-gray-400" />
                </div>
              ) : customers.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-sm">
                  No se encontraron clientes.
                </div>
              ) : (
                customers.map((customer) => (
                  <div
                    key={customer.id}
                    onClick={() => setSelectedCustomer(customer)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedCustomer?.id === customer.id
                        ? 'bg-blue-50 border-blue-200'
                        : 'hover:bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-medium">{customer.phone_number}</span>
                      {customer.is_troll && (
                        <Badge variant="destructive" className="text-[10px]">TROLL</Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 truncate">{customer.name || 'Sin nombre'}</p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                      <Chat className="h-3 w-3" />
                      {customer.daily_message_count} msgs hoy
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Detalle del Cliente */}
          <div className="flex-1 overflow-y-auto">
            {selectedCustomer ? (
              <div className="space-y-8">
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-2xl font-bold">{selectedCustomer.name || 'Cliente Desconocido'}</h2>
                    <p className="text-gray-500 text-lg">{selectedCustomer.phone_number}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-gray-500">Reputación</div>
                    <div className={`text-2xl font-bold ${
                      selectedCustomer.reputation_score > 80 ? 'text-green-600' : 
                      selectedCustomer.reputation_score < 40 ? 'text-red-600' : 'text-yellow-600'
                    }`}>
                      {selectedCustomer.reputation_score}/100
                    </div>
                  </div>
                </div>

                {/* Panel de Control de Seguridad */}
                <div className="bg-red-50 border border-red-100 rounded-lg p-6 space-y-6">
                  <h3 className="font-semibold text-red-900 flex items-center gap-2">
                    <ShieldWarning className="h-5 w-5" />
                    Zona de Seguridad
                  </h3>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-red-900">Marcar como Troll</div>
                      <p className="text-sm text-red-700">
                        La IA dejará de responderle o le dará respuestas cortas.
                      </p>
                    </div>
                    <Switch
                      checked={selectedCustomer.is_troll}
                      onCheckedChange={(checked) => handleUpdateStatus({ is_troll: checked })}
                      disabled={updating}
                    />
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-red-200">
                    <div>
                      <div className="font-medium text-red-900">Bloquear Completamente</div>
                      <p className="text-sm text-red-700">
                        El sistema ignorará todos sus mensajes.
                      </p>
                    </div>
                    <Switch
                      checked={selectedCustomer.is_blocked}
                      onCheckedChange={(checked) => handleUpdateStatus({ is_blocked: checked })}
                      disabled={updating}
                    />
                  </div>
                </div>

                {/* Notas Internas */}
                <div className="space-y-2">
                  <h3 className="font-semibold">Notas Internas</h3>
                  <Textarea
                    value={selectedCustomer.notes || ''}
                    onChange={(e) => setSelectedCustomer({ ...selectedCustomer, notes: e.target.value })}
                    onBlur={(e) => handleUpdateStatus({ notes: e.target.value })}
                    placeholder="Escribe notas sobre este cliente (preferencias, incidentes, etc)..."
                    className="min-h-[100px]"
                  />
                </div>

                {/* Estadísticas */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-500">Mensajes Hoy</div>
                    <div className="text-xl font-semibold">{selectedCustomer.daily_message_count}</div>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-500">Última Interacción</div>
                    <div className="text-sm font-medium">
                      {selectedCustomer.last_interaction_at 
                        ? new Date(selectedCustomer.last_interaction_at).toLocaleString() 
                        : 'Nunca'}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <User className="h-16 w-16 mb-4 opacity-20" />
                <p className="text-lg">Selecciona un cliente para ver detalles</p>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
