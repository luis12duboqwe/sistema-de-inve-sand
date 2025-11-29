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
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="general" className="flex items-center gap-2">
                <CurrencyDollar size={16} />
                General
              </TabsTrigger>
              <TabsTrigger value="notifications" className="flex items-center gap-2">
                <Bell size={16} />
                Notificaciones
              </TabsTrigger>
              <TabsTrigger value="business" className="flex items-center gap-2">
                Negocio
            </TabsList>
            <TabsContent val
                <Label 

                >
                    <SelectValue />
                  <SelectContent>
                    <Se
                  </SelectContent>
              </div>
              <di
                <Select
                  onValueChange={(v
                  <SelectTrigger i
                  </SelectTrigger
                    <SelectItem value="standard">1,234.56 (Están
                    <SelectItem value="space">1 234.56 (Espacio)
                </Select>

                <Label ht
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

              <div className="space-y-2">
                <Label htmlFor="lowStockThreshold">Umbral de stock bajo</Label>
                <Input
                  id="lowStockThreshold"
                  type="number"
                  min="0"
                  value={settings.lowStockThreshold}
                  onChange={(e) => setSettings({ ...settings, lowStockThreshold: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">
                  Recibirás alertas cuando el stock caiga por debajo de este número
                </p>
              </div>
            </TabsContent>

            <TabsContent value="notifications" className="space-y-4 mt-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="space-y-0.5">
                  <Label htmlFor="enableNotifications">Habilitar notificaciones</Label>
                  <p className="text-sm text-muted-foreground">
                    Recibe alertas sobre stock bajo y nuevas órdenes
                  </p>
                </div>
                <Switch
                  id="enableNotifications"
                  checked={settings.enableNotifications}
                  onCheckedChange={(checked) => setSettings({ ...settings, enableNotifications: checked })}
                />
              </div>

              {settings.enableNotifications && (
                <div className="pl-4 text-sm text-muted-foreground">
                  <p className="mb-2">Se enviarán notificaciones para:</p>
                  <ul className="space-y-1">
                    <li>• Stock bajo en productos</li>
                    <li>• Nuevas órdenes creadas</li>
                    <li>• Órdenes completadas</li>
                  </ul>
                </div>
              )}
            </TabsContent>

            <TabsContent value="business" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="businessAddress">Dirección del negocio</Label>
                <Input
                  id="businessAddress"
                  value={settings.businessAddress}
                  onChange={(e) => setSettings({ ...settings, businessAddress: e.target.value })}
                  placeholder="Calle Principal #123"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="businessPhone">Teléfono del negocio</Label>
                <Input
                  id="businessPhone"
                  value={settings.businessPhone}
                  onChange={(e) => setSettings({ ...settings, businessPhone: e.target.value })}
                  placeholder="+1234567890"
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

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="space-y-0.5">
                  <Label htmlFor="autoCalculateTax">Calcular impuestos automáticamente</Label>
                  <p className="text-sm text-muted-foreground">
                    Aplicar tasa de impuestos a los precios de productos
                  </p>
                </div>
                <Switch
                  id="autoCalculateTax"
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
