import { useState, useEffect, useCallback } from 'react'
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
import { toast } from 'sonner'
import type { Profile, Supplier } from '@/lib/types'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'

interface ManageSuppliersDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profile?: Profile
}

export function ManageSuppliersDialog({
  open,
  onOpenChange,
  profile
}: ManageSuppliersDialogProps) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null)
  
  // Form state
  const [nombre, setNombre] = useState('')
  const [contacto, setContacto] = useState('')
  const [telefono, setTelefono] = useState('')
  const [email, setEmail] = useState('')
  const [direccion, setDireccion] = useState('')
  const [notas, setNotas] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadSuppliers = useCallback(async () => {
    setLoading(true)
    try {
      const data = await inventoryServiceInstance.listSuppliers(false)
      setSuppliers(data)
    } catch (error) {
      console.error('Error loading suppliers:', error)
      toast.error('Error al cargar proveedores')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      loadSuppliers()
    }
  }, [open, loadSuppliers])

  const resetForm = () => {
    setNombre('')
    setContacto('')
    setTelefono('')
    setEmail('')
    setDireccion('')
    setNotas('')
    setEditingSupplier(null)
    setShowForm(false)
  }

  const handleEdit = (supplier: Supplier) => {
    setEditingSupplier(supplier)
    setNombre(supplier.nombre)
    setContacto(supplier.contacto || '')
    setTelefono(supplier.telefono || '')
    setEmail(supplier.email || '')
    setDireccion(supplier.direccion || '')
    setNotas(supplier.notas || '')
    setShowForm(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!nombre.trim()) {
      toast.error('El nombre del proveedor es requerido')
      return
    }

    setIsSubmitting(true)

    try {
      const supplierData = {
        nombre: nombre.trim(),
        contacto: contacto.trim() || undefined,
        telefono: telefono.trim() || undefined,
        email: email.trim() || undefined,
        direccion: direccion.trim() || undefined,
        notas: notas.trim() || undefined,
        activo: true
      }

      if (editingSupplier) {
        // Update
        await inventoryServiceInstance.updateSupplier(editingSupplier.id, supplierData)
        toast.success('Proveedor actualizado exitosamente')
      } else {
        // Create
        await inventoryServiceInstance.createSupplier({
          ...supplierData,
          profile_id: profile.id
        } as any)
        toast.success('Proveedor creado exitosamente')
      }

      await loadSuppliers()
      resetForm()
    } catch (error) {
      console.error('Error saving supplier:', error)
      toast.error(error instanceof Error ? error.message : 'Error al guardar proveedor')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (supplier: Supplier) => {
    if (!confirm(`¿Estás seguro de eliminar el proveedor "${supplier.nombre}"?`)) {
      return
    }

    try {
      await inventoryServiceInstance.deleteSupplier(supplier.id)

      toast.success('Proveedor eliminado exitosamente')
      await loadSuppliers()
    } catch (error) {
      console.error('Error deleting supplier:', error)
      toast.error('Error al eliminar proveedor')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Gestionar Proveedores {profile?.name ? `- ${profile.name}` : ''}</DialogTitle>
          <DialogDescription>
            Administra los proveedores para organizar reclamos y devoluciones
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {!showForm ? (
            <>
              <div className="flex justify-between items-center">
                <h3 className="font-medium">Proveedores ({suppliers.length})</h3>
                <Button onClick={() => setShowForm(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Nuevo Proveedor
                </Button>
              </div>

              {loading ? (
                <p className="text-muted-foreground text-center py-8">Cargando proveedores...</p>
              ) : suppliers.length === 0 ? (
                <Card className="p-8 text-center">
                  <p className="text-muted-foreground mb-4">No hay proveedores registrados</p>
                  <Button onClick={() => setShowForm(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Agregar Primer Proveedor
                  </Button>
                </Card>
              ) : (
                <div className="space-y-2">
                  {suppliers.map(supplier => (
                    <Card key={supplier.id} className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-medium">{supplier.nombre}</h4>
                            {supplier.activo && (
                              <Badge variant="outline" className="text-xs">Activo</Badge>
                            )}
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                            {supplier.contacto && (
                              <div>
                                <strong>Contacto:</strong> {supplier.contacto}
                              </div>
                            )}
                            {supplier.telefono && (
                              <div>
                                <strong>Teléfono:</strong> {supplier.telefono}
                              </div>
                            )}
                            {supplier.email && (
                              <div>
                                <strong>Email:</strong> {supplier.email}
                              </div>
                            )}
                            {supplier.direccion && (
                              <div className="col-span-2">
                                <strong>Dirección:</strong> {supplier.direccion}
                              </div>
                            )}
                          </div>
                          {supplier.notas && (
                            <p className="mt-2 text-sm text-muted-foreground italic">
                              {supplier.notas}
                            </p>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(supplier)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(supplier)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <h3 className="font-medium">
                {editingSupplier ? 'Editar Proveedor' : 'Nuevo Proveedor'}
              </h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="nombre">Nombre *</Label>
                  <Input
                    id="nombre"
                    value={nombre}
                    onChange={e => setNombre(e.target.value)}
                    placeholder="Nombre del proveedor"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="contacto">Persona de Contacto</Label>
                  <Input
                    id="contacto"
                    value={contacto}
                    onChange={e => setContacto(e.target.value)}
                    placeholder="Nombre del contacto"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="telefono">Teléfono</Label>
                  <Input
                    id="telefono"
                    value={telefono}
                    onChange={e => setTelefono(e.target.value)}
                    placeholder="+504 1234-5678"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="proveedor@example.com"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="direccion">Dirección</Label>
                <Input
                  id="direccion"
                  value={direccion}
                  onChange={e => setDireccion(e.target.value)}
                  placeholder="Dirección completa"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="notas">Notas</Label>
                <Textarea
                  id="notas"
                  value={notas}
                  onChange={e => setNotas(e.target.value)}
                  placeholder="Observaciones adicionales..."
                  rows={3}
                />
              </div>

              <div className="flex gap-2 justify-end">
                <Button type="button" variant="outline" onClick={resetForm}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting
                    ? 'Guardando...'
                    : editingSupplier
                    ? 'Actualizar'
                    : 'Crear Proveedor'}
                </Button>
              </div>
            </form>
          )}
        </div>

        {!showForm && (
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
