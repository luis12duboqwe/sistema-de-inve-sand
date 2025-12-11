import { useState, useEffect } from 'react'
import { Building, MapPin, Phone, Plus, Pencil, Trash, Package } from '@phosphor-icons/react'
import { toast } from 'sonner'
import { Location } from '@/lib/types'
import { Button } from './ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { Badge } from './ui/badge'
import { useKV } from '@/hooks/use-kv'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'

export function LocationsList() {
  const [useAPI] = useKV<boolean>('settings_use_api', false)
  const [apiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingLocation, setEditingLocation] = useState<Location | null>(null)
  const [filterTipo, setFilterTipo] = useState<string>('all')

  // Formulario
  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState<'tienda' | 'bodega' | 'oficina'>('tienda')
  const [direccion, setDireccion] = useState('')
  const [telefono, setTelefono] = useState('')

  useEffect(() => {
    loadLocations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useAPI, apiUrl])

  const loadLocations = async () => {
    try {
      const data = await inventoryServiceInstance.getLocations()
      console.log('✅ Ubicaciones cargadas:', data)
      setLocations(data || [])
    } catch (error) {
      console.error('❌ Error al cargar ubicaciones:', error)
      setLocations([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!nombre.trim()) {
      toast.error('El nombre es requerido')
      return
    }

    try {
      const newLocation = await inventoryServiceInstance.createLocation({
        nombre: nombre.trim(),
        tipo,
        direccion: direccion.trim() || undefined,
        telefono: telefono.trim() || undefined,
        activo: true,
      } as any)

      console.log('✅ Ubicación creada:', newLocation)
      
      toast.success('✅ Ubicación creada exitosamente')
      setIsCreateOpen(false)
      resetForm()
      
      // Recargar la lista
      await loadLocations()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error desconocido'
      toast.error(`❌ Error al crear ubicación: ${message}`)
      console.error(error)
    }
  }

  const handleUpdate = async () => {
    if (!editingLocation || !nombre.trim()) {
      toast.error('El nombre es requerido')
      return
    }

    try {
      await inventoryServiceInstance.updateLocation(editingLocation.id, {
        nombre: nombre.trim(),
        tipo,
        direccion: direccion.trim() || undefined,
        telefono: telefono.trim() || undefined,
        activo: editingLocation.activo,
      })

      toast.success('Ubicación actualizada exitosamente')
      setEditingLocation(null)
      resetForm()
      loadLocations()
    } catch (error) {
      toast.error('Error al actualizar ubicación')
      console.error(error)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar esta ubicación? Esta acción no se puede deshacer.')) {
      return
    }

    try {
      await inventoryServiceInstance.deleteLocation(id)

      toast.success('✅ Ubicación eliminada exitosamente')
      await loadLocations()
    } catch (error: any) {
      // Extraer mensaje de error del backend
      const errorMessage = error.message || 'Error al eliminar ubicación'
      
      // Si el error menciona stock, mostrar mensaje más específico
      if (errorMessage.includes('stock')) {
        toast.error('⚠️ No se puede eliminar: Esta ubicación tiene productos con stock asignado. Primero transfiere o elimina el stock.', {
          duration: 5000
        })
      } else if (errorMessage.includes('órdenes') || errorMessage.includes('orders')) {
        toast.error('⚠️ No se puede eliminar: Esta ubicación tiene órdenes asociadas.', {
          duration: 5000
        })
      } else {
        toast.error(`❌ ${errorMessage}`)
      }
      
      console.error('Error al eliminar ubicación:', error)
    }
  }

  const handleToggleActive = async (location: Location) => {
    try {
      await inventoryServiceInstance.updateLocation(location.id, { activo: !location.activo })

      toast.success(`Ubicación ${!location.activo ? 'activada' : 'desactivada'}`)
      loadLocations()
    } catch (error) {
      toast.error('Error al cambiar estado')
      console.error(error)
    }
  }

  const resetForm = () => {
    setNombre('')
    setTipo('tienda')
    setDireccion('')
    setTelefono('')
  }

  const openEdit = (location: Location) => {
    setEditingLocation(location)
    setNombre(location.nombre)
    setTipo(location.tipo)
    setDireccion(location.direccion || '')
    setTelefono(location.telefono || '')
  }

  const filteredLocations = locations.filter((loc) => {
    if (filterTipo === 'all') return true
    return loc.tipo === filterTipo
  })

  const getTipoIcon = (tipo: string) => {
    switch (tipo) {
      case 'tienda':
        return <Building className="w-5 h-5" />
      case 'bodega':
        return <Package className="w-5 h-5" />
      case 'oficina':
        return <MapPin className="w-5 h-5" />
      default:
        return <Building className="w-5 h-5" />
    }
  }

  const getTipoColor = (tipo: string) => {
    switch (tipo) {
      case 'tienda':
        return 'bg-blue-100 text-blue-800'
      case 'bodega':
        return 'bg-amber-100 text-amber-800'
      case 'oficina':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return <div className="p-8 text-center">Cargando ubicaciones...</div>
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Ubicaciones</h1>
          <p className="text-gray-600 mt-1">Gestiona tus tiendas, bodegas y oficinas</p>
          {!useAPI && (
            <p className="text-sm text-blue-600 mt-2">
              💾 Modo Local: Los datos se guardan en tu navegador
            </p>
          )}
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="w-4 h-4 mr-2" />
              Nueva Ubicación
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Crear Nueva Ubicación</DialogTitle>
              <DialogDescription>
                Agrega una nueva ubicación física para gestionar tu inventario
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="nombre">Nombre *</Label>
                <Input
                  id="nombre"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="Tienda Centro"
                />
              </div>
              <div>
                <Label htmlFor="tipo">Tipo *</Label>
                <Select value={tipo} onValueChange={(v: any) => setTipo(v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tienda">Tienda</SelectItem>
                    <SelectItem value="bodega">Bodega</SelectItem>
                    <SelectItem value="oficina">Oficina</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="direccion">Dirección</Label>
                <Input
                  id="direccion"
                  value={direccion}
                  onChange={(e) => setDireccion(e.target.value)}
                  placeholder="Av. Principal 123"
                />
              </div>
              <div>
                <Label htmlFor="telefono">Teléfono</Label>
                <Input
                  id="telefono"
                  value={telefono}
                  onChange={(e) => setTelefono(e.target.value)}
                  placeholder="+1234567890"
                />
              </div>
              <Button onClick={handleCreate} className="w-full">
                Crear Ubicación
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filtros */}
      <div className="mb-6">
        <Select value={filterTipo} onValueChange={setFilterTipo}>
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Filtrar por tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las ubicaciones</SelectItem>
            <SelectItem value="tienda">Solo Tiendas</SelectItem>
            <SelectItem value="bodega">Solo Bodegas</SelectItem>
            <SelectItem value="oficina">Solo Oficinas</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Grid de ubicaciones */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredLocations.map((location) => (
          <div
            key={location.id}
            className={`border rounded-lg p-6 space-y-4 ${
              !location.activo ? 'opacity-50 bg-gray-50' : 'bg-white'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${getTipoColor(location.tipo)}`}>
                  {getTipoIcon(location.tipo)}
                </div>
                <div>
                  <h3 className="font-semibold text-lg">{location.nombre}</h3>
                  <Badge variant="outline" className="mt-1">
                    {location.tipo.charAt(0).toUpperCase() + location.tipo.slice(1)}
                  </Badge>
                </div>
              </div>
            </div>

            {location.direccion && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <MapPin className="w-4 h-4" />
                <span>{location.direccion}</span>
              </div>
            )}

            {location.telefono && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Phone className="w-4 h-4" />
                <span>{location.telefono}</span>
              </div>
            )}

            <div className="flex gap-2 pt-4 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => openEdit(location)}
              >
                <Pencil className="w-4 h-4 mr-1" />
                Editar
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleToggleActive(location)}
              >
                {location.activo ? 'Desactivar' : 'Activar'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDelete(location.id)}
                className="text-red-600 hover:text-red-700"
              >
                <Trash className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      {filteredLocations.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No hay ubicaciones registradas. Crea la primera ubicación.
        </div>
      )}

      {/* Diálogo de edición */}
      <Dialog open={!!editingLocation} onOpenChange={(open) => !open && setEditingLocation(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Ubicación</DialogTitle>
            <DialogDescription>
              Modifica los detalles de esta ubicación
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="edit-nombre">Nombre *</Label>
              <Input
                id="edit-nombre"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="edit-tipo">Tipo *</Label>
              <Select value={tipo} onValueChange={(v: any) => setTipo(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tienda">Tienda</SelectItem>
                  <SelectItem value="bodega">Bodega</SelectItem>
                  <SelectItem value="oficina">Oficina</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="edit-direccion">Dirección</Label>
              <Input
                id="edit-direccion"
                value={direccion}
                onChange={(e) => setDireccion(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="edit-telefono">Teléfono</Label>
              <Input
                id="edit-telefono"
                value={telefono}
                onChange={(e) => setTelefono(e.target.value)}
              />
            </div>
            <Button onClick={handleUpdate} className="w-full">
              Actualizar Ubicación
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
