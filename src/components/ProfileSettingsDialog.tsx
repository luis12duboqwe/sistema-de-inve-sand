import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
  onSubmit
}: ProfileSettingsDialogProps) {
  const [settings, setSettings] = useState<ProfileSettings>({
    currency: 'HNL',
    taxRate: 0,
    lowStockThreshold: 5,
    enableNotifications: false,
    defaultPaymentMethod: 'efectivo',
    defaultChannel: 'whatsapp',
    autoCalculateTax: false,
    priceFormat: 'standard'
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

        <form onSubmit={handleSubmit} className="space-y-6">
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="general">
                <CurrencyDollar size={16} className="mr-2" />
                General
              </TabsTrigger>
              <TabsTrigger value="notifications">
                <Bell size={16} className="mr-2" />
                Notificaciones
              </TabsTrigger>
              <TabsTrigger value="business">
                <Storefront size={16} className="mr-2" />
                Negocio
              </TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="currency">Moneda</Label>
                <Select
                  value={settings.currency}
                  onValueChange={(v) => setSettings({ ...settings, currency: v })}
                >
                  <SelectTrigger id="currency">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="HNL">HNL (Lempira)</SelectItem>
                    <SelectItem value="USD">USD (Dólar)</SelectItem>
                    <SelectItem value="MXN">MXN (Peso Mexicano)</SelectItem>
                    <SelectItem value="EUR">EUR (Euro)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="priceFormat">Formato de Precio</Label>
                <Select
                  value={settings.priceFormat}
                  onValueChange={(v) => setSettings({ ...settings, priceFormat: v as ProfileSettings['priceFormat'] })}
                >
                  <SelectTrigger id="priceFormat">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">Estándar (1234.56)</SelectItem>
                    <SelectItem value="comma">Coma (1.234,56)</SelectItem>
                    <SelectItem value="space">Espacio (1 234.56)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="taxRate">Tasa de Impuesto (%)</Label>
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

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="autoCalculateTax">Calcular Impuesto Automáticamente</Label>
                  <p className="text-sm text-muted-foreground">Agrega impuesto a precios en órdenes</p>
                </div>
                <Switch
                  id="autoCalculateTax"
                  checked={settings.autoCalculateTax}
                  onCheckedChange={(checked) => setSettings({ ...settings, autoCalculateTax: checked })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="lowStockThreshold">Umbral de Stock Bajo</Label>
                <Input
                  id="lowStockThreshold"
                  type="number"
                  min="0"
                  value={settings.lowStockThreshold}
                  onChange={(e) => setSettings({ ...settings, lowStockThreshold: parseInt(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="defaultPaymentMethod">Método de Pago Predeterminado</Label>
                <Select
                  value={settings.defaultPaymentMethod}
                  onValueChange={(v) => setSettings({ ...settings, defaultPaymentMethod: v as ProfileSettings['defaultPaymentMethod'] })}
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
                <Label htmlFor="defaultChannel">Canal Predeterminado</Label>
                <Select
                  value={settings.defaultChannel}
                  onValueChange={(v) => setSettings({ ...settings, defaultChannel: v as ProfileSettings['defaultChannel'] })}
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
            </TabsContent>

            <TabsContent value="notifications" className="space-y-4 pt-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="enableNotifications">Habilitar Notificaciones</Label>
                  <p className="text-sm text-muted-foreground">Recibe alertas de stock bajo y nuevas órdenes</p>
                </div>
                <Switch
                  id="enableNotifications"
                  checked={settings.enableNotifications}
                  onCheckedChange={(checked) => setSettings({ ...settings, enableNotifications: checked })}
                />
              </div>
            </TabsContent>

            <TabsContent value="business" className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="businessAddress">Dirección del Negocio</Label>
                <Input
                  id="businessAddress"
                  placeholder="Calle Principal #123, Ciudad"
                  value={settings.businessAddress || ''}
                  onChange={(e) => setSettings({ ...settings, businessAddress: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="businessPhone">Teléfono del Negocio</Label>
                <Input
                  id="businessPhone"
                  placeholder="+504 1234-5678"
                  value={settings.businessPhone || ''}
                  onChange={(e) => setSettings({ ...settings, businessPhone: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="businessEmail">Correo del Negocio</Label>
                <Input
                  id="businessEmail"
                  type="email"
                  placeholder="negocio@example.com"
                  value={settings.businessEmail || ''}
                  onChange={(e) => setSettings({ ...settings, businessEmail: e.target.value })}
                />
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit">
              Guardar Configuración
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
