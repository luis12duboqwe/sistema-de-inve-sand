import { useState, useEffect } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { CurrencyDollar, Bell, Storefront } from '@phosphor-icons/react'
import type { Profile, ProfileSettings } from '@/lib/types'

interface ProfileSettingsDialogProps {
  open: boolean
  profile: Profile
  onOpenChange: (open: boolean) => void
  onSubmit: (profileId: number, settings: ProfileSettings) => void
}

export function ProfileSettingsDialog({
  open,
  profile,
  onOpenChange,
  onSubmit,
}: ProfileSettingsDialogProps) {
  const [settings, setSettings] = useState<ProfileSettings>({
    currency: 'USD',
    taxRate: 0,
    lowStockThreshold: 5,
    enableNotifications: false,
    defaultPaymentMethod: 'efectivo',
    defaultChannel: 'whatsapp',
    businessAddress: '',
    businessPhone: '',
    businessEmail: '',
    autoCalculateTax: false,
    priceFormat: 'standard',
  })

  useEffect(() => {
    if (profile.settings) {
      setSettings(profile.settings)
    }
  }, [profile])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(profile.id, settings)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configuración de {profile.name}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <Tabs defaultValue="general">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="general" className="flex items-center gap-2">
                <CurrencyDollar size={16} />
                <span className="hidden sm:inline">General</span>
              </TabsTrigger>
              <TabsTrigger value="notifications" className="flex items-center gap-2">
                <Bell size={16} />
                <span className="hidden sm:inline">Notificaciones</span>
              </TabsTrigger>
              <TabsTrigger value="business" className="flex items-center gap-2">
                <Storefront size={16} />
                <span className="hidden sm:inline">Negocio</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="currency">Moneda</Label>
                <Select
                  value={settings.currency}
                  onValueChange={(value: ProfileSettings['currency']) => setSettings({ ...settings, currency: value })}
                >
                  <SelectTrigger id="currency">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD ($)</SelectItem>
                    <SelectItem value="EUR">EUR (€)</SelectItem>
                    <SelectItem value="MXN">MXN ($)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="priceFormat">Formato de precio</Label>
                <Select
                  value={settings.priceFormat}
                  onValueChange={(value: ProfileSettings['priceFormat']) => setSettings({ ...settings, priceFormat: value })}
                >
                  <SelectTrigger id="priceFormat">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">1,234.56 (Estándar)</SelectItem>
                    <SelectItem value="comma">1.234,56 (Coma)</SelectItem>
                    <SelectItem value="space">1 234.56 (Espacio)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="defaultPaymentMethod">Método de pago por defecto</Label>
                <Select
                  value={settings.defaultPaymentMethod}
                  onValueChange={(value: ProfileSettings['defaultPaymentMethod']) => setSettings({ ...settings, defaultPaymentMethod: value })}
                >
                  <SelectTrigger id="defaultPaymentMethod">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="efectivo">Efectivo</SelectItem>
                    <SelectItem value="transferencia">Transferencia</SelectItem>
                    <SelectItem value="tarjeta">Tarjeta</SelectItem>
                    <SelectItem value="financiamiento">Financiamiento</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="defaultChannel">Canal por defecto</Label>
                <Select
                  value={settings.defaultChannel}
                  onValueChange={(value: ProfileSettings['defaultChannel']) => setSettings({ ...settings, defaultChannel: value })}
                >
                  <SelectTrigger id="defaultChannel">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="whatsapp">WhatsApp</SelectItem>
                    <SelectItem value="facebook">Facebook</SelectItem>
                    <SelectItem value="instagram">Instagram</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between py-2">
                <div className="space-y-0.5">
                  <Label>Cálculo automático de impuestos</Label>
                  <p className="text-sm text-muted-foreground">
                    Agregar impuestos automáticamente a los precios
                  </p>
                </div>
                <Switch
                  checked={settings.autoCalculateTax}
                  onCheckedChange={(checked) => setSettings({ ...settings, autoCalculateTax: checked })}
                />
              </div>

              {settings.autoCalculateTax && (
                <div className="space-y-2">
                  <Label htmlFor="taxRate">Tasa de impuesto (%)</Label>
                  <Input
                    id="taxRate"
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={settings.taxRate}
                    onChange={(e) => setSettings({ ...settings, taxRate: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              )}
            </TabsContent>

            <TabsContent value="notifications" className="space-y-4 mt-4">
              <div className="flex items-center justify-between py-2">
                <div className="space-y-0.5">
                  <Label>Activar notificaciones</Label>
                  <p className="text-sm text-muted-foreground">
                    Recibir alertas sobre stock bajo y órdenes
                  </p>
                </div>
                <Switch
                  checked={settings.enableNotifications}
                  onCheckedChange={(checked) => setSettings({ ...settings, enableNotifications: checked })}
                />
              </div>

              {settings.enableNotifications && (
                <div className="pl-4 text-sm text-muted-foreground">
                  <p className="mb-2">Recibirás notificaciones para:</p>
                  <ul className="space-y-1 list-disc list-inside">
                    <li>Stock bajo (menos de {settings.lowStockThreshold} unidades)</li>
                    <li>Nuevas órdenes pendientes</li>
                    <li>Órdenes completadas</li>
                  </ul>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="lowStockThreshold">Umbral de stock bajo</Label>
                <Input
                  id="lowStockThreshold"
                  type="number"
                  min="1"
                  value={settings.lowStockThreshold}
                  onChange={(e) => setSettings({ ...settings, lowStockThreshold: parseInt(e.target.value) || 5 })}
                />
                <p className="text-sm text-muted-foreground">
                  Número mínimo de unidades antes de recibir alerta
                </p>
              </div>
            </TabsContent>

            <TabsContent value="business" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="businessAddress">Dirección del negocio</Label>
                <Input
                  id="businessAddress"
                  value={settings.businessAddress}
                  onChange={(e) => setSettings({ ...settings, businessAddress: e.target.value })}
                  placeholder="Calle, número, colonia, ciudad"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="businessPhone">Teléfono del negocio</Label>
                <Input
                  id="businessPhone"
                  value={settings.businessPhone}
                  onChange={(e) => setSettings({ ...settings, businessPhone: e.target.value })}
                  placeholder="+52 123 456 7890"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="businessEmail">Email del negocio</Label>
                <Input
                  id="businessEmail"
                  type="email"
                  value={settings.businessEmail}
                  onChange={(e) => setSettings({ ...settings, businessEmail: e.target.value })}
                  placeholder="contacto@negocio.com"
                />
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit">
              Guardar cambios
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
