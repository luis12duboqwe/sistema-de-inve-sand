import { useState, useEffect } from 'react'
import { Robot, User, Cpu, Plus, Pencil, Trash, WhatsappLogo, FacebookLogo, InstagramLogo, Plug, Storefront } from '@phosphor-icons/react'
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
import { apiClient } from '@/lib/apiClient'
import { AIProfileConfigDialog } from './AIProfileConfigDialog'

type ChannelIntegrationFormState = {
  whatsapp: {
    phone_number_id: string
    access_token: string
    verify_token: string
  }
  messenger: {
    page_id: string
    page_access_token: string
    verify_token: string
  }
  instagram: {
    instagram_account_id: string
    page_access_token: string
    verify_token: string
  }
}

const emptyChannelIntegrationState = (): ChannelIntegrationFormState => ({
  whatsapp: {
    phone_number_id: '',
    access_token: '',
    verify_token: ''
  },
  messenger: {
    page_id: '',
    page_access_token: '',
    verify_token: ''
  },
  instagram: {
    instagram_account_id: '',
    page_access_token: '',
    verify_token: ''
  }
})

const buildChannelIntegrationsConfig = (state: ChannelIntegrationFormState) => {
  const result: Record<string, Record<string, string>> = {}

  if (state.whatsapp.phone_number_id || state.whatsapp.access_token || state.whatsapp.verify_token) {
    result.whatsapp = {
      phone_number_id: state.whatsapp.phone_number_id.trim(),
      access_token: state.whatsapp.access_token.trim(),
      verify_token: state.whatsapp.verify_token.trim()
    }
  }

  if (state.messenger.page_id || state.messenger.page_access_token || state.messenger.verify_token) {
    result.messenger = {
      page_id: state.messenger.page_id.trim(),
      page_access_token: state.messenger.page_access_token.trim(),
      verify_token: state.messenger.verify_token.trim()
    }
  }

  if (state.instagram.instagram_account_id || state.instagram.page_access_token || state.instagram.verify_token) {
    result.instagram = {
      instagram_account_id: state.instagram.instagram_account_id.trim(),
      page_access_token: state.instagram.page_access_token.trim(),
      verify_token: state.instagram.verify_token.trim()
    }
  }

  return result
}

const countConfiguredIntegrations = (configuracion?: Record<string, any>) => {
  const integrations = configuracion?.channel_integrations || {}
  return ['whatsapp', 'messenger', 'instagram'].filter((channel) => integrations?.[channel]).length
}

const getIntegrationStatus = (configuracion: Record<string, any> | undefined, channel: 'whatsapp' | 'facebook' | 'instagram' | 'tienda') => {
  const integrations = configuracion?.channel_integrations || {}

  if (channel === 'tienda') {
    return {
      label: 'Tienda Física',
      ready: true,
      missing: [] as string[]
    }
  }

  if (channel === 'whatsapp') {
    const config = integrations?.whatsapp
    const ready = Boolean(config?.phone_number_id && config?.access_token)
    return {
      label: 'WhatsApp',
      ready,
      missing: ready ? [] : ['phone_number_id', 'access_token'].filter((key) => !config?.[key])
    }
  }

  if (channel === 'facebook') {
    const config = integrations?.messenger
    const ready = Boolean(config?.page_id && config?.page_access_token)
    return {
      label: 'Messenger',
      ready,
      missing: ready ? [] : ['page_id', 'page_access_token'].filter((key) => !config?.[key])
    }
  }

  const config = integrations?.instagram
  const ready = Boolean(config?.instagram_account_id && config?.page_access_token)
  return {
    label: 'Instagram',
    ready,
    missing: ready ? [] : ['instagram_account_id', 'page_access_token'].filter((key) => !config?.[key])
  }
}

interface SalesProfilesListProps {
  onUpdate?: () => void
  canManageAI?: boolean
  canManageTechnicalChannels?: boolean
}

export function SalesProfilesList({ onUpdate, canManageAI = false, canManageTechnicalChannels = false }: SalesProfilesListProps) {
  const [useAPI] = useKV<boolean>('settings_use_api', false)
  const [apiUrl] = useKV<string>('settings_api_url', 'http://localhost:8000/api')
  const [profiles, setProfiles] = useState<SalesProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingProfile, setEditingProfile] = useState<SalesProfile | null>(null)
  const [aiConfigProfile, setAiConfigProfile] = useState<SalesProfile | null>(null)
  const [technicalConfigProfile, setTechnicalConfigProfile] = useState<SalesProfile | null>(null)
  const [filterTipo, setFilterTipo] = useState<string>('all')

  // Formulario
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [tipo, setTipo] = useState<'bot_ia' | 'vendedor_humano' | 'sistema_automatico'>('bot_ia')
  const [canales, setCanales] = useState<('whatsapp' | 'facebook' | 'instagram' | 'tienda')[]>([])
  const [exchangeRate, setExchangeRate] = useState<string>('25.0')
  
  // Contact Info
  const [whatsappNumber, setWhatsappNumber] = useState('')
  const [facebookPage, setFacebookPage] = useState('')
  const [instagramHandle, setInstagramHandle] = useState('')
  const [channelIntegrations, setChannelIntegrations] = useState<ChannelIntegrationFormState>(emptyChannelIntegrationState())

  // Testing channels
  const [testingChannel, setTestingChannel] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { status: 'success' | 'error', details: string }>>({})

  useEffect(() => {
    loadProfiles()
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
        configuracion: {
          exchange_rate: parseFloat(exchangeRate) || 25.0,
          contact_info: {
            whatsapp: whatsappNumber,
            facebook: facebookPage,
            instagram: instagramHandle
          }
        }
      } as any)

      toast.success('Perfil de venta creado exitosamente')
      setIsCreateOpen(false)
      resetForm()
      loadProfiles()
      if (onUpdate) onUpdate()
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
        configuracion: {
          ...editingProfile.configuracion,
          exchange_rate: parseFloat(exchangeRate) || 25.0,
          contact_info: {
            whatsapp: whatsappNumber,
            facebook: facebookPage,
            instagram: instagramHandle
          }
        }
      })

      toast.success('Perfil actualizado exitosamente')
      setEditingProfile(null)
      resetForm()
      if (onUpdate) onUpdate()
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
      if (onUpdate) onUpdate()
    } catch (error: any) {
      toast.error(error.message || 'Error al eliminar perfil')
      console.error(error)
    }
  }

  const handleToggleActive = async (profile: SalesProfile) => {
    try {
      await inventoryServiceInstance.updateSalesProfile(profile.id, { active: !profile.active })

      toast.success(`Perfil ${!profile.active ? 'activado' : 'desactivado'}`)
      if (onUpdate) onUpdate()
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
    setExchangeRate('25.0')
    setWhatsappNumber('')
    setFacebookPage('')
    setInstagramHandle('')
    setChannelIntegrations(emptyChannelIntegrationState())
  }

  const testChannelConnection = async (profileSlug: string, channel: string) => {
    const testKey = `${profileSlug}__${channel}`
    setTestingChannel(testKey)
    
    try {
      const result = await apiClient.testChannelConnection(profileSlug, channel)

      const isSuccess = result.status === 'success'
      setTestResults(prev => ({
        ...prev,
        [testKey]: { 
          status: isSuccess ? 'success' : 'error',
          details: result.details 
        }
      }))

      if (isSuccess) {
        toast.success(`${channel.toUpperCase()} conectado exitosamente`)
      } else {
        toast.error(`Error en ${channel.toUpperCase()}: ${result.details}`)
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Error desconocido'
      setTestResults(prev => ({
        ...prev,
        [testKey]: { status: 'error', details: errorMsg }
      }))
      toast.error(`Error al probar ${channel}: ${errorMsg}`)
    } finally {
      setTestingChannel(null)
    }
  }

  const openEdit = (profile: SalesProfile) => {
    setEditingProfile(profile)
    setName(profile.name)
    setSlug(profile.slug)
    setTipo(profile.tipo)
    setCanales(profile.canales)
    
    // Cargar configuración
    if (profile.configuracion && profile.configuracion.exchange_rate) {
      setExchangeRate(String(profile.configuracion.exchange_rate))
    } else {
      setExchangeRate('25.0')
    }

    // Cargar info de contacto
    const contact = profile.configuracion?.contact_info || {}
    setWhatsappNumber(contact.whatsapp || '')
    setFacebookPage(contact.facebook || '')
    setInstagramHandle(contact.instagram || '')

    const integrations = profile.configuracion?.channel_integrations || {}
    setChannelIntegrations({
      whatsapp: {
        phone_number_id: integrations?.whatsapp?.phone_number_id || '',
        access_token: integrations?.whatsapp?.access_token || '',
        verify_token: integrations?.whatsapp?.verify_token || ''
      },
      messenger: {
        page_id: integrations?.messenger?.page_id || '',
        page_access_token: integrations?.messenger?.page_access_token || '',
        verify_token: integrations?.messenger?.verify_token || ''
      },
      instagram: {
        instagram_account_id: integrations?.instagram?.instagram_account_id || '',
        page_access_token: integrations?.instagram?.page_access_token || '',
        verify_token: integrations?.instagram?.verify_token || ''
      }
    })
  }

  const openTechnicalConfig = (profile: SalesProfile) => {
    setTechnicalConfigProfile(profile)

    const integrations = profile.configuracion?.channel_integrations || {}
    setChannelIntegrations({
      whatsapp: {
        phone_number_id: integrations?.whatsapp?.phone_number_id || '',
        access_token: integrations?.whatsapp?.access_token || '',
        verify_token: integrations?.whatsapp?.verify_token || ''
      },
      messenger: {
        page_id: integrations?.messenger?.page_id || '',
        page_access_token: integrations?.messenger?.page_access_token || '',
        verify_token: integrations?.messenger?.verify_token || ''
      },
      instagram: {
        instagram_account_id: integrations?.instagram?.instagram_account_id || '',
        page_access_token: integrations?.instagram?.page_access_token || '',
        verify_token: integrations?.instagram?.verify_token || ''
      }
    })
  }

  const handleSaveTechnicalConfig = async () => {
    if (!technicalConfigProfile) return

    try {
      await inventoryServiceInstance.updateSalesProfile(technicalConfigProfile.id, {
        configuracion: {
          ...technicalConfigProfile.configuracion,
          channel_integrations: buildChannelIntegrationsConfig(channelIntegrations)
        }
      })

      toast.success('Conexiones técnicas actualizadas')
      setTechnicalConfigProfile(null)
      setChannelIntegrations(emptyChannelIntegrationState())
      if (onUpdate) onUpdate()
      loadProfiles()
    } catch (error) {
      toast.error('Error al guardar conexiones técnicas')
      console.error(error)
    }
  }

  const updateIntegrationField = (
    channel: keyof ChannelIntegrationFormState,
    field: string,
    value: string
  ) => {
    setChannelIntegrations((prev) => ({
      ...prev,
      [channel]: {
        ...prev[channel],
        [field]: value
      }
    }))
  }

  const renderIntegrationsSection = (prefix: string) => (
    <div className="space-y-4 border-t pt-4">
      <div>
        <Label className="text-base flex items-center gap-2">
          <Plug className="w-4 h-4 text-sky-600" />
          Conexiones técnicas por canal
        </Label>
        <p className="text-xs text-gray-500 mt-1">
          Aquí conectas las cuentas reales y webhooks de este perfil. Esta área debe quedar restringida al Super Admin.
        </p>
      </div>

      {canales.includes('whatsapp') && (
        <div className="border rounded-lg p-3 space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <WhatsappLogo className="w-5 h-5 text-green-600" /> WhatsApp
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-wa-phone-id`} className="text-xs text-gray-500">Phone Number ID</Label>
            <Input
              id={`${prefix}-wa-phone-id`}
              value={channelIntegrations.whatsapp.phone_number_id}
              onChange={(e) => updateIntegrationField('whatsapp', 'phone_number_id', e.target.value)}
              placeholder="1234567890"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-wa-access-token`} className="text-xs text-gray-500">Access Token</Label>
            <Input
              id={`${prefix}-wa-access-token`}
              value={channelIntegrations.whatsapp.access_token}
              onChange={(e) => updateIntegrationField('whatsapp', 'access_token', e.target.value)}
              placeholder="EAAG..."
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-wa-verify-token`} className="text-xs text-gray-500">Verify Token</Label>
            <Input
              id={`${prefix}-wa-verify-token`}
              value={channelIntegrations.whatsapp.verify_token}
              onChange={(e) => updateIntegrationField('whatsapp', 'verify_token', e.target.value)}
              placeholder="verify-softmobile-wa"
            />
          </div>
        </div>
      )}

      {canales.includes('facebook') && (
        <div className="border rounded-lg p-3 space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <FacebookLogo className="w-5 h-5 text-blue-600" /> Messenger
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-mg-page-id`} className="text-xs text-gray-500">Page ID</Label>
            <Input
              id={`${prefix}-mg-page-id`}
              value={channelIntegrations.messenger.page_id}
              onChange={(e) => updateIntegrationField('messenger', 'page_id', e.target.value)}
              placeholder="987654321"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-mg-access-token`} className="text-xs text-gray-500">Page Access Token</Label>
            <Input
              id={`${prefix}-mg-access-token`}
              value={channelIntegrations.messenger.page_access_token}
              onChange={(e) => updateIntegrationField('messenger', 'page_access_token', e.target.value)}
              placeholder="EAAG..."
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-mg-verify-token`} className="text-xs text-gray-500">Verify Token</Label>
            <Input
              id={`${prefix}-mg-verify-token`}
              value={channelIntegrations.messenger.verify_token}
              onChange={(e) => updateIntegrationField('messenger', 'verify_token', e.target.value)}
              placeholder="verify-softmobile-mg"
            />
          </div>
        </div>
      )}

      {canales.includes('instagram') && (
        <div className="border rounded-lg p-3 space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <InstagramLogo className="w-5 h-5 text-pink-600" /> Instagram
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-ig-account-id`} className="text-xs text-gray-500">Instagram Account ID</Label>
            <Input
              id={`${prefix}-ig-account-id`}
              value={channelIntegrations.instagram.instagram_account_id}
              onChange={(e) => updateIntegrationField('instagram', 'instagram_account_id', e.target.value)}
              placeholder="1122334455"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-ig-access-token`} className="text-xs text-gray-500">Page Access Token</Label>
            <Input
              id={`${prefix}-ig-access-token`}
              value={channelIntegrations.instagram.page_access_token}
              onChange={(e) => updateIntegrationField('instagram', 'page_access_token', e.target.value)}
              placeholder="EAAG..."
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${prefix}-ig-verify-token`} className="text-xs text-gray-500">Verify Token</Label>
            <Input
              id={`${prefix}-ig-verify-token`}
              value={channelIntegrations.instagram.verify_token}
              onChange={(e) => updateIntegrationField('instagram', 'verify_token', e.target.value)}
              placeholder="verify-softmobile-ig"
            />
          </div>
        </div>
      )}
    </div>
  )

  const toggleCanal = (canal: 'whatsapp' | 'facebook' | 'instagram' | 'tienda') => {
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
        case 'tienda':
          return <Storefront key={canal} className="w-5 h-5 text-amber-600" />
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
                <Label htmlFor="exchange-rate">Tasa de Cambio (USD a HNL)</Label>
                <Input
                  id="exchange-rate"
                  type="number"
                  step="0.01"
                  value={exchangeRate}
                  onChange={(e) => setExchangeRate(e.target.value)}
                  placeholder="25.00"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Usada para convertir precios en USD al crear órdenes.
                </p>
              </div>

              <div className="space-y-3 border-t pt-3">
                <Label className="text-base">Información de Contacto (Para el Bot)</Label>
                
                <div className="grid gap-2">
                  <Label htmlFor="whatsapp-num" className="text-xs text-gray-500">Número de WhatsApp</Label>
                  <Input
                    id="whatsapp-num"
                    value={whatsappNumber}
                    onChange={(e) => setWhatsappNumber(e.target.value)}
                    placeholder="+504 9999-9999"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="fb-page" className="text-xs text-gray-500">Página de Facebook</Label>
                  <Input
                    id="fb-page"
                    value={facebookPage}
                    onChange={(e) => setFacebookPage(e.target.value)}
                    placeholder="https://facebook.com/mitienda"
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="ig-handle" className="text-xs text-gray-500">Instagram Handle</Label>
                  <Input
                    id="ig-handle"
                    value={instagramHandle}
                    onChange={(e) => setInstagramHandle(e.target.value)}
                    placeholder="@mitienda"
                  />
                </div>
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
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="tienda"
                      checked={canales.includes('tienda')}
                      onCheckedChange={() => toggleCanal('tienda')}
                    />
                    <label htmlFor="tienda" className="flex items-center gap-2 cursor-pointer">
                      <Storefront className="w-5 h-5 text-amber-600" />
                      Tienda Física
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

            {canManageTechnicalChannels && (
              <>
                <div>
                  <p className="text-sm text-gray-600 mb-2">Estado de conexiones técnicas:</p>
                  <div className="space-y-2">
                    {profile.canales.map((canal) => {
                      const status = getIntegrationStatus(profile.configuracion, canal)
                      const testKey = `${profile.slug}__${canal}`
                      const testResult = testResults[testKey]
                      const isTesting = testingChannel === testKey
                      
                      return (
                        <div key={`${profile.id}-${canal}`} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                          <span className="font-medium text-gray-700">{status.label}</span>
                          <div className="flex items-center gap-2">
                            {testResult && (
                              <span className={`text-xs px-2 py-1 rounded ${testResult.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                {testResult.status === 'success' ? '✓ OK' : '✗ Error'}
                              </span>
                            )}
                            {!status.ready && status.missing.length > 0 && (
                              <span className="text-xs text-gray-400 hidden xl:inline">
                                {status.missing.join(', ')}
                              </span>
                            )}
                            {canal !== 'tienda' && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => testChannelConnection(profile.slug, canal)}
                                disabled={isTesting || !status.ready}
                                className="h-6 px-2"
                              >
                                {isTesting ? '⟳' : <Plug size={14} />}
                              </Button>
                            )}
                            <Badge variant={status.ready ? 'secondary' : 'destructive'}>
                              {status.ready ? 'Listo' : 'Incompleto'}
                            </Badge>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                <div className="text-sm text-gray-500">
                  Conexiones configuradas: <span className="font-medium text-gray-700">{countConfiguredIntegrations(profile.configuracion)}</span>
                </div>
              </>
            )}

            <div className="text-sm text-gray-500">
              Slug: <code className="bg-gray-100 px-2 py-1 rounded">{profile.slug}</code>
            </div>

            <div className="flex gap-2 pt-4 border-t">
              {canManageTechnicalChannels && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openTechnicalConfig(profile)}
                  className="text-sky-600 hover:text-sky-700 border-sky-200 hover:bg-sky-50"
                >
                  <Plug className="w-4 h-4 mr-1" />
                  Conexiones
                </Button>
              )}
              {profile.tipo === 'bot_ia' && canManageAI && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setAiConfigProfile(profile)}
                  className="text-purple-600 hover:text-purple-700 border-purple-200 hover:bg-purple-50"
                >
                  <Robot className="w-4 h-4 mr-1" />
                  IA
                </Button>
              )}
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
              <Label htmlFor="edit-exchange-rate">Tasa de Cambio (USD a HNL)</Label>
              <Input
                id="edit-exchange-rate"
                type="number"
                step="0.01"
                value={exchangeRate}
                onChange={(e) => setExchangeRate(e.target.value)}
                placeholder="25.00"
              />
              <p className="text-xs text-gray-500 mt-1">
                Usada para convertir precios en USD al crear órdenes.
              </p>
            </div>

            <div className="space-y-3 border-t pt-3">
              <Label className="text-base">Información de Contacto (Para el Bot)</Label>
              
              <div className="grid gap-2">
                <Label htmlFor="edit-whatsapp-num" className="text-xs text-gray-500">Número de WhatsApp</Label>
                <Input
                  id="edit-whatsapp-num"
                  value={whatsappNumber}
                  onChange={(e) => setWhatsappNumber(e.target.value)}
                  placeholder="+504 9999-9999"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="edit-fb-page" className="text-xs text-gray-500">Página de Facebook</Label>
                <Input
                  id="edit-fb-page"
                  value={facebookPage}
                  onChange={(e) => setFacebookPage(e.target.value)}
                  placeholder="https://facebook.com/mitienda"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="edit-ig-handle" className="text-xs text-gray-500">Instagram Handle</Label>
                <Input
                  id="edit-ig-handle"
                  value={instagramHandle}
                  onChange={(e) => setInstagramHandle(e.target.value)}
                  placeholder="@mitienda"
                />
              </div>
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
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="edit-tienda"
                    checked={canales.includes('tienda')}
                    onCheckedChange={() => toggleCanal('tienda')}
                  />
                  <label htmlFor="edit-tienda" className="flex items-center gap-2 cursor-pointer">
                    <Storefront className="w-5 h-5 text-amber-600" />
                    Tienda Física
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

      {/* Diálogo de Configuración IA */}
      {canManageAI && aiConfigProfile && (
        <AIProfileConfigDialog
          open={!!aiConfigProfile}
          onOpenChange={(open) => !open && setAiConfigProfile(null)}
          salesProfileId={aiConfigProfile.id}
          salesProfileName={aiConfigProfile.name}
        />
      )}

      <Dialog open={!!technicalConfigProfile} onOpenChange={(open) => !open && setTechnicalConfigProfile(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Conexiones Técnicas del Canal</DialogTitle>
            <DialogDescription>
              Configuración técnica separada del perfil comercial. Solo Super Admin debe modificar tokens, IDs y webhooks.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {technicalConfigProfile && (
              <>
                <div className="rounded-md border bg-sky-50 px-3 py-2 text-sm text-sky-800">
                  Perfil: <span className="font-medium">{technicalConfigProfile.name}</span>
                </div>
                {renderIntegrationsSection('technical')}
                <Button onClick={handleSaveTechnicalConfig} className="w-full">
                  Guardar Conexiones Técnicas
                </Button>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
