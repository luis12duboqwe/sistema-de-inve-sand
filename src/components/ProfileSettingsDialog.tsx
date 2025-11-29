import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switc
import { Tabs, TabsContent, TabsList, TabsTrigg
import { Input } from '@/components/ui/input'
import { CurrencyDollar, Bell, Gear, Buildings } from '@phosphor-icons/react'
interface ProfileSettingsDialogProps {
import type { Profile, ProfileSettings } from '@/lib/types'
import { CurrencyDollar, Bell, Gear, Buildings } from '@phosphor-icons/react'

interface ProfileSettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profile: Profile
  onSubmit: (profileId: number, settings: ProfileSettings) => void
}

const defaultSettings: ProfileSettings = {
  currency: 'USD',
  taxRate: 0,
  lowStockThreshold: 5,
  enableNotifications: true,
  defaultPaymentMethod: 'efectivo',
  defaultChannel: 'whatsapp',
  autoCalculateTax: false,
  priceFormat: 'standard'
}

export function ProfileSettingsDialog({ open, onOpenChange, profile, onSubmit }: ProfileSettingsDialogProps) {
  const [settings, setSettings] = useState<ProfileSettings>(profile.settings || defaultSettings)

  return (
      <DialogContent c
          <DialogTitle>Configuraci
   

        <f
            <TabsList className="grid w-full grid-co
                <Gear size={16} />
              </TabsTr
                <CurrencyDollar size={16} />
              </TabsTrigger>
              <TabsTrigger value="general" className="flex items-center gap-2">
                <Gear size={16} />
                General
              </TabsTrigger>
              <TabsTrigger value="pricing" className="flex items-center gap-2">
                <CurrencyDollar size={16} />
                Precios
              </TabsTrigger>
              <TabsTrigger value="notifications" className="flex items-center gap-2">
                <Bell size={16} />
                Notificaciones
              </TabsTrigger>
              <TabsTrigger value="business" className="flex items-center gap-2">
                <Buildings size={16} />
                Negocio
              </TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="defaultPaymentMethod">Método de pago por defecto</Label>
                <Select
                  value={settings.defaultPaymentMethod}
                  onValueChange={(value) => setSettings({ ...settings, defaultPaymentMethod: value as ProfileSettings['defaultPaymentMethod'] })}
                >
                  <SelectTrigger id="defaultPaymentMethod">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="efectivo">Efectivo</SelectItem>
                    <SelectItem value="tarjeta">Tarjeta</SelectItem>
                    <SelectItem value="transferencia">Transferencia</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="defaultChannel">Canal de venta por defecto</Label>
                <Select
                  value={settings.defaultChannel}
                  onValueChange={(value) => setSettings({ ...settings, defaultChannel: value as ProfileSettings['defaultChannel'] })}
                >
                  <SelectTrigger id="defaultChannel">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="whatsapp">WhatsApp</SelectItem>
                    <SelectItem value="instagram">Instagram</SelectItem>
                    <SelectItem value="telefono">Teléfono</SelectItem>
                    <SelectItem value="presencial">Presencial</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="lowStockThreshold">Umbral de stock bajo</Label>
                <Input
                  id="lowStockThreshold"
                  type="number"
                  value={settings.lowStockThreshold}
                  min="0"
                  onChange={(e) => setSettings({ ...settings, lowStockThreshold: parseInt(e.target.value) || 0 })}
                />
                <p className="text-sm text-muted-foreground">
                  Se mostrará una advertencia cuando el stock esté por debajo de este valor
                </p>
              </div>
            </TabsContent>

            <TabsContent value="pricing" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="currency">Moneda</Label>
                <Select
                  value={settings.currency}
                  onValueChange={(value) => setSettings({ ...settings, currency: value })}
                >
                  <SelectTrigger id="currency">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD - Dólar</SelectItem>
                    <SelectItem value="EUR">EUR - Euro</SelectItem>
                    <SelectItem value="ARS">ARS - Peso Argentino</SelectItem>
                    <SelectItem value="CLP">CLP - Peso Chileno</SelectItem>
                    <SelectItem value="BRL">BRL - Real Brasileño</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="priceFormat">Formato de precio</Label>
                <Select
                  value={settings.priceFormat}
                  onValueChange={(value) => setSettings({ ...settings, priceFormat: value as ProfileSettings['priceFormat'] })}
                >
                  <SelectTrigger id="priceFormat">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">123,456.78</SelectItem>
                    <SelectItem value="comma">123.456,78</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="autoCalculateTax">Cálculo automático de impuestos</Label>
                  <p className="text-sm text-muted-foreground">
                    Añadir impuestos automáticamente a los precios
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
                    value={settings.taxRate}
                    min="0"
                    step="0.1"
                    onChange={(e) => setSettings({ ...settings, taxRate: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              )}
            </TabsContent>

            <TabsContent value="notifications" className="space-y-4 mt-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="enableNotifications">Notificaciones</Label>
                  <p className="text-sm text-muted-foreground">
                    Recibir notificaciones sobre eventos importantes
                  </p>
                </div>
                <Switch
                  id="enableNotifications"
                  checked={settings.enableNotifications}
                  onCheckedChange={(checked) => setSettings({ ...settings, enableNotifications: checked })}
                />
              </div>

              {settings.enableNotifications && (
                <div className="space-y-2 p-4 bg-muted rounded-lg">
                  <p className="text-sm font-medium">Se enviarán notificaciones cuando:</p>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• El stock de un producto esté bajo</li>
                    <li>• Se cree una nueva orden</li>
                    <li>• El estado de una orden cambie</li>
                  </ul>
                </div>
              )}
            </TabsContent>

            <TabsContent value="business" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="businessAddress">Dirección del negocio</Label>
                <Input
                  id="businessAddress"
                  value={settings.businessAddress || ''}
                  onChange={(e) => setSettings({ ...settings, businessAddress: e.target.value })}
                  placeholder="Calle, número, ciudad"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="businessPhone">Teléfono del negocio</Label>
                <Input
                  id="businessPhone"
                  type="tel"
                  value={settings.businessPhone || ''}
                  onChange={(e) => setSettings({ ...settings, businessPhone: e.target.value })}
                  placeholder="+1 234 567 8900"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="businessEmail">Email del negocio</Label>
                <Input
                  id="businessEmail"
                  type="email"
                  value={settings.businessEmail || ''}
                  onChange={(e) => setSettings({ ...settings, businessEmail: e.target.value })}
                  placeholder="contacto@negocio.com"
                />
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit">
              Guardar configuración
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
