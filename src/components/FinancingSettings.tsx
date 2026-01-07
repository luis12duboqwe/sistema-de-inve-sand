import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { Bank } from '@/lib/types'
import { toast } from 'sonner'
import { Plus, Trash2, Edit, Save, X } from 'lucide-react'

export function FinancingSettings() {
  const [banks, setBanks] = useState<Bank[]>([])
  const [editingBank, setEditingBank] = useState<Bank | null>(null)
  const [newBankName, setNewBankName] = useState('')
  const [newBankRate, setNewBankRate] = useState('0')

  // State for adding new option
  const [newOptionMonths, setNewOptionMonths] = useState('')
  const [newOptionRate, setNewOptionRate] = useState('')

  useEffect(() => {
    loadBanks()
  }, [])

  const loadBanks = async () => {
    try {
      const data = await inventoryServiceInstance.getBanks(false) // Get all banks, active and inactive
      setBanks(data)
    } catch (error) {
      console.error(error)
      toast.error('Error al cargar bancos')
    }
  }

  const handleCreateBank = async () => {
    if (!newBankName.trim()) return
    try {
      await inventoryServiceInstance.createBank({
        name: newBankName,
        active: true,
        normal_card_rate: parseFloat(newBankRate) / 100,
        financing_options: []
      })
      toast.success('Banco creado')
      setNewBankName('')
      setNewBankRate('0')
      loadBanks()
    } catch (error) {
      console.error(error)
      toast.error('Error al crear banco')
    }
  }

  const handleUpdateBank = async (bank: Bank) => {
    try {
      await inventoryServiceInstance.updateBank(bank.id, {
        name: bank.name,
        active: bank.active,
        normal_card_rate: bank.normal_card_rate
      })
      toast.success('Banco actualizado')
      setEditingBank(null)
      loadBanks()
    } catch (error) {
      console.error(error)
      toast.error('Error al actualizar banco')
    }
  }

  const handleAddOption = async (bankId: number) => {
    if (!newOptionMonths || !newOptionRate) return
    try {
      await inventoryServiceInstance.createFinancingOption(bankId, {
        months: parseInt(newOptionMonths),
        rate: parseFloat(newOptionRate) / 100,
        active: true
      })
      toast.success('Opción agregada')
      setNewOptionMonths('')
      setNewOptionRate('')
      loadBanks()
    } catch (error) {
      console.error(error)
      toast.error('Error al agregar opción')
    }
  }

  const handleDeleteOption = async (optionId: number) => {
    if (!confirm('¿Estás seguro de eliminar esta opción?')) return
    try {
      await inventoryServiceInstance.deleteFinancingOption(optionId)
      toast.success('Opción eliminada')
      loadBanks()
    } catch (error) {
      console.error(error)
      toast.error('Error al eliminar opción')
    }
  }

  return (
    <div className="space-y-6">
      {/* Add New Bank Section */}
      <div className="flex items-end gap-4 p-4 border rounded-lg bg-muted/20">
        <div className="space-y-2 flex-1">
          <Label>Nuevo Banco</Label>
          <Input 
            placeholder="Nombre del Banco" 
            value={newBankName}
            onChange={(e) => setNewBankName(e.target.value)}
          />
        </div>
        <div className="space-y-2 w-32">
          <Label>Tasa Normal %</Label>
          <Input 
            type="number" 
            placeholder="0" 
            value={newBankRate}
            onChange={(e) => setNewBankRate(e.target.value)}
          />
        </div>
        <Button onClick={handleCreateBank} disabled={!newBankName}>
          <Plus className="h-4 w-4 mr-2" /> Agregar
        </Button>
      </div>

      {/* Banks List */}
      <div className="space-y-4">
        {banks.map((bank) => (
          <div key={bank.id} className="border rounded-lg p-4 space-y-4">
            <div className="flex items-center justify-between">
              {editingBank?.id === bank.id ? (
                <div className="flex items-center gap-4 flex-1">
                  <Input 
                    value={editingBank.name} 
                    onChange={(e) => setEditingBank({...editingBank, name: e.target.value})}
                  />
                  <div className="flex items-center gap-2">
                    <Label>Tasa Normal %:</Label>
                    <Input 
                      type="number"
                      className="w-24"
                      value={(editingBank.normal_card_rate * 100).toString()} 
                      onChange={(e) => setEditingBank({
                        ...editingBank, 
                        normal_card_rate: parseFloat(e.target.value) / 100
                      })}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Label>Activo:</Label>
                    <Switch 
                      checked={editingBank.active}
                      onCheckedChange={(checked) => setEditingBank({...editingBank, active: checked})}
                    />
                  </div>
                  <Button size="sm" onClick={() => handleUpdateBank(editingBank)}>
                    <Save className="h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditingBank(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-4">
                    <h3 className="text-lg font-semibold">{bank.name}</h3>
                    <span className={`text-xs px-2 py-1 rounded-full ${bank.active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {bank.active ? 'Activo' : 'Inactivo'}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      Tasa Normal: {(bank.normal_card_rate * 100).toFixed(2)}%
                    </span>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => setEditingBank(bank)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>

            {/* Financing Options Table */}
            <div className="pl-4 border-l-2 border-muted">
              <h4 className="text-sm font-medium mb-2">Opciones de Extrafinanciamiento</h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Meses</TableHead>
                    <TableHead>Tasa (%)</TableHead>
                    <TableHead className="w-[100px]">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bank.financing_options.map((opt) => (
                    <TableRow key={opt.id}>
                      <TableCell>{opt.months} meses</TableCell>
                      <TableCell>{(opt.rate * 100).toFixed(2)}%</TableCell>
                      <TableCell>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-red-500 hover:text-red-700"
                          onClick={() => handleDeleteOption(opt.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {/* Add Option Row */}
                  <TableRow>
                    <TableCell>
                      <Input 
                        type="number" 
                        placeholder="Meses" 
                        className="w-24"
                        value={newOptionMonths}
                        onChange={(e) => setNewOptionMonths(e.target.value)}
                      />
                    </TableCell>
                    <TableCell>
                      <Input 
                        type="number" 
                        placeholder="%" 
                        className="w-24"
                        value={newOptionRate}
                        onChange={(e) => setNewOptionRate(e.target.value)}
                      />
                    </TableCell>
                    <TableCell>
                      <Button 
                        size="sm" 
                        variant="secondary"
                        onClick={() => handleAddOption(bank.id)}
                        disabled={!newOptionMonths || !newOptionRate}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
