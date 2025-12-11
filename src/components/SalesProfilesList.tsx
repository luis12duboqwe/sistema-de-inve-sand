import { useState, useEffect } from 'react'
import { Robot, User, Cpu, Plus, Pencil, Trash, WhatsappLogo, FacebookLogo, InstagramLogo } from '@phosphor-icons/react'
import { toast } from 'sonner'
import { SalesProfile } from '@/lib/types'
import { Button } from './ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { Badge } from './ui/badge'
import { Checkbox } from './ui/checkbox'
import { useKV } from '@/hooks/use-kv'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'

export function SalesProfilesList() {
  const [useAPI] = useKV<boolean>('settings_use_api', false)
  const [apiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')
  const [profiles, setProfiles] = useState<SalesProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingProfile, setEditingProfile] = useState<SalesProfile | null>(null)
  const [filterTipo, setFilterTipo] = useState<string>('all')

  // Formulario
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [tipo, setTipo] = useState<'bot_ia' | 'vendedor_humano' | 'sistema_automatico'>('bot_ia')
  const [canales, setCanales] = useState<('whatsapp' | 'facebook' | 'instagram')[]>([])

  useEffect(() => {
    loadProfiles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useAPI, apiUrl])

  const loadProfiles = async () => {
    try {
      const data = await inventoryServiceInstance.getSalesProfiles()
      setProfiles(data)
    } catch (error) {
      toast.error('Error al cargar perfiles de venta')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error('El nombre es requerido')
      return
    }

    if (canales.length === 0) {
      toast.error('Selecciona al menos un canal')
      return
    }

    try {
      const normalizedSlug = (slug || name)
        .trim()
        .toLowerCase()
        .replace(/\s+/g, '-')

      await inventoryServiceInstance.createSalesProfile({
        name: name.trim(),
        slug: normalizedSlug,
        tipo,
        canales,
        active: true,
      } as any)

      toast.success('Perfil de venta creado exitosamente')
      setIsCreateOpen(false)
      resetForm()
      loadProfiles()
    } catch (error) {
      toast.error('Error al crear perfil')
      console.error(error)
    }
  }

  const handleUpdate = async () => {
    if (!editingProfile || !name.trim()) {
      toast.error('El nombre es requerido')
      return
    }

    if (canales.length === 0) {
      toast.error('Selecciona al menos un canal')
      return
    }

    try {
      const normalizedSlug = (slug || editingProfile.slug || name)
        .trim()
        .toLowerCase()
        .replace(/\s+/g, '-')

      await inventoryServiceInstance.updateSalesProfile(editingProfile.id, {
        name: name.trim(),
        slug: normalizedSlug,
        tipo,
        canales,
        active: editingProfile.active,
      })

      toast.success('Perfil actualizado exitosamente')
      setEditingProfile(null)
      resetForm()
      loadProfiles()
    } catch (error) {
      toast.error('Error al actualizar perfil')
      console.error(error)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este perfil de venta? Esta acción no se puede deshacer.')) {
      return
    }

    try {
      await inventoryServiceInstance.deleteSalesProfile(id)

      toast.success('Perfil eliminado exitosamente')
      loadProfiles()
    } catch (error: any) {
      toast.error(error.message || 'Error al eliminar perfil')
      console.error(error)
    }
  }

  const handleToggleActive = async (profile: SalesProfile) => {
    try {
      await inventoryServiceInstance.updateSalesProfile(profile.id, { active: !profile.active })

      toast.success(`Perfil ${!profile.active ? 'activado' : 'desactivado'}`)
      loadProfiles()
    } catch (error) {
      toast.error('Error al cambiar estado')
      console.error(error)
    }
  }

  const resetForm = () => {
    setName('')
    setSlug('')
    setTipo('bot_ia')
    setCanales([])
  }

  const openEdit = (profile: SalesProfile) => {
    setEditingProfile(profile)
    setName(profile.name)
    setSlug(profile.slug)
    setTipo(profile.tipo)
    setCanales(profile.canales)
  }

  const toggleCanal = (canal: 'whatsapp' | 'facebook' | 'instagram') => {
    setCanales((prev) =>
      prev.includes(canal) ? prev.filter((c) => c !== canal) : [...prev, canal]
    )
  }

  const filteredProfiles = profiles.filter((prof) => {
    if (filterTipo === 'all') return true
    return prof.tipo === filterTipo
  })

  const getTipoIcon = (tipo: string) => {
    switch (tipo) {
      case 'bot_ia':
        return <Robot className="w-5 h-5" />
      case 'vendedor_humano':
        return <User className="w-5 h-5" />
      case 'sistema_automatico':
        return <Cpu className="w-5 h-5" />
      default:
        return <Robot className="w-5 h-5" />
    }
  }

  const getTipoColor = (tipo: string) => {
    switch (tipo) {
      case 'bot_ia':
        return 'bg-purple-100 text-purple-800'
      case 'vendedor_humano':
        return 'bg-green-100 text-green-800'
      case 'sistema_automatico':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getTipoLabel = (tipo: string) => {
    switch (tipo) {
      case 'bot_ia':
        return 'Bot IA'
      case 'vendedor_humano':
        return 'Vendedor Humano'
      case 'sistema_automatico':
        return 'Sistema Automático'
      default:
        return tipo
    }
  }

  const getCanalesIcons = (canales: string[]) => {
    return canales.map((canal) => {
      switch (canal) {
        case 'whatsapp':
          return <WhatsappLogo key={canal} className="w-5 h-5 text-green-600" />
        case 'facebook':
          return <FacebookLogo key={canal} className="w-5 h-5 text-blue-600" />
        case 'instagram':
          return <InstagramLogo key={canal} className="w-5 h-5 text-pink-600" />
        default:
          return null
      }
    })
  }

  if (loading) {
    return <div className="p-8 text-center">Cargando perfiles de venta...</div>
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Perfiles de Venta</h1>
          <p className="text-gray-600 mt-1">Gestiona tus bots, vendedores y sistemas de venta</p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Perfil
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Crear Nuevo Perfil de Venta</DialogTitle>
              <DialogDescription>
                Crea un bot, vendedor o sistema para gestionar ventas en diferentes canales
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="nombre">Nombre *</Label>
                <Input
                  id="nombre"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ej: Bot WhatsApp" 
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="slug">Slug *</Label>
                <Input
                  id="slug"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  placeholder="bot-whatsapp"
                />
              </div>
              <div>
                <Label htmlFor="tipo">Tipo *</Label>
                <Select value={tipo} onValueChange={(v: any) => setTipo(v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bot_ia">Bot IA</SelectItem>
                    <SelectItem value="vendedor_humano">Vendedor Humano</SelectItem>
                    <SelectItem value="sistema_automatico">Sistema Automático</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Canales de Venta *</Label>
                <div className="space-y-2 mt-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="whatsapp"
                      checked={canales.includes('whatsapp')}
                      onCheckedChange={() => toggleCanal('whatsapp')}
                    />
                    <label htmlFor="whatsapp" className="flex items-center gap-2 cursor-pointer">
                      <WhatsappLogo className="w-5 h-5 text-green-600" />
                      WhatsApp
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="facebook"
                      checked={canales.includes('facebook')}
                      onCheckedChange={() => toggleCanal('facebook')}
                    />
                    <label htmlFor="facebook" className="flex items-center gap-2 cursor-pointer">
                      <FacebookLogo className="w-5 h-5 text-blue-600" />
                      Facebook
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="instagram"
                      checked={canales.includes('instagram')}
                      onCheckedChange={() => toggleCanal('instagram')}
                    />
                    <label htmlFor="instagram" className="flex items-center gap-2 cursor-pointer">
                      <InstagramLogo className="w-5 h-5 text-pink-600" />
                      Instagram
                    </label>
                  </div>
                </div>
              </div>
              <Button onClick={handleCreate} className="w-full">
                Crear Perfil
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
            <SelectItem value="all">Todos los perfiles</SelectItem>
            <SelectItem value="bot_ia">Solo Bots IA</SelectItem>
            <SelectItem value="vendedor_humano">Solo Vendedores</SelectItem>
            <SelectItem value="sistema_automatico">Solo Sistemas</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Grid de perfiles */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProfiles.map((profile) => (
          <div
            key={profile.id}
            className={`border rounded-lg p-6 space-y-4 ${
              !profile.active ? 'opacity-50 bg-gray-50' : 'bg-white'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${getTipoColor(profile.tipo)}`}>
                  {getTipoIcon(profile.tipo)}
                </div>
                <div>
                  <h3 className="font-semibold text-lg">{profile.name}</h3>
                  <Badge variant="outline" className="mt-1">
                    {getTipoLabel(profile.tipo)}
                  </Badge>
                </div>
              </div>
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-2">Canales:</p>
              <div className="flex gap-2">{getCanalesIcons(profile.canales)}</div>
            </div>

            <div className="text-sm text-gray-500">
              Slug: <code className="bg-gray-100 px-2 py-1 rounded">{profile.slug}</code>
            </div>

            <div className="flex gap-2 pt-4 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => openEdit(profile)}
              >
                <Pencil className="w-4 h-4 mr-1" />
                Editar
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleToggleActive(profile)}
              >
                {profile.active ? 'Desactivar' : 'Activar'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDelete(profile.id)}
                className="text-red-600 hover:text-red-700"
              >
                <Trash className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      {filteredProfiles.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No hay perfiles de venta registrados. Crea el primer perfil.
        </div>
      )}

      {/* Diálogo de edición */}
      <Dialog open={!!editingProfile} onOpenChange={(open) => !open && setEditingProfile(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Perfil de Venta</DialogTitle>
            <DialogDescription>
              Modifica la configuración de este perfil de venta
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="edit-nombre">Nombre *</Label>
              <Input
                id="edit-nombre"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="edit-slug">Slug *</Label>
              <Input
                id="edit-slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="edit-tipo">Tipo *</Label>
              <Select value={tipo} onValueChange={(v: any) => setTipo(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bot_ia">Bot IA</SelectItem>
                  <SelectItem value="vendedor_humano">Vendedor Humano</SelectItem>
                  <SelectItem value="sistema_automatico">Sistema Automático</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Canales de Venta *</Label>
              <div className="space-y-2 mt-2">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="edit-whatsapp"
                    checked={canales.includes('whatsapp')}
                    onCheckedChange={() => toggleCanal('whatsapp')}
                  />
                  <label htmlFor="edit-whatsapp" className="flex items-center gap-2 cursor-pointer">
                    <WhatsappLogo className="w-5 h-5 text-green-600" />
                    WhatsApp
                  </label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="edit-facebook"
                    checked={canales.includes('facebook')}
                    onCheckedChange={() => toggleCanal('facebook')}
                  />
                  <label htmlFor="edit-facebook" className="flex items-center gap-2 cursor-pointer">
                    <FacebookLogo className="w-5 h-5 text-blue-600" />
                    Facebook
                  </label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="edit-instagram"
                    checked={canales.includes('instagram')}
                    onCheckedChange={() => toggleCanal('instagram')}
                  />
                  <label htmlFor="edit-instagram" className="flex items-center gap-2 cursor-pointer">
                    <InstagramLogo className="w-5 h-5 text-pink-600" />
                    Instagram
                  </label>
                </div>
              </div>
            </div>
            <Button onClick={handleUpdate} className="w-full">
              Actualizar Perfil
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
