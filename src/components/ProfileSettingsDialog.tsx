import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CurrencyDollar, Bell, Buildings } from '@phosphor-icons/react'
  open: boolean

}
export function
  profile,
  onOpenChange: (open: boolean) => void
  onSubmit: (profileId: number, settings: ProfileSettings) => void
}

    defaultChannel: 'whatsapp',
    bus
    autoCa
  })
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
                Notificaciones
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <div cla
          <DialogTitle>Configuración de {profile.name}</DialogTitle>
                  value
        <form onSubmit={handleSubmit}>
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="general" className="flex items-center gap-2">
                <CurrencyDollar size={16} />
                    <Se
              </TabsTrigger>
              <TabsTrigger value="notifications" className="flex items-center gap-2">
                <Bell size={16} />
                Notificaciones
              </TabsTrigger>
              <TabsTrigger value="business" className="flex items-center gap-2">
                <Buildings size={16} />
                  <Selec
              </TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="currency">Moneda</Label>
                <Select
                  value={settings.currency}
                  onValueChange={(value) => setSettings({ ...settings, currency: value })}
                >
                  <SelectTrigger id="currency">
                  <SelectContent>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD ($)</SelectItem>
                    <SelectItem value="EUR">EUR (€)</SelectItem>
                    <SelectItem value="MXN">MXN ($)</SelectItem>
                    <SelectItem value="COP">COP ($)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="priceFormat">Formato de precio</Label>
                <Select
                    <SelectItem value="instagr
                  onValueChange={(value: 'standard' | 'comma' | 'space') => setSettings({ ...settings, priceFormat: value })}
              </d
                  <SelectTrigger id="priceFormat">
                <Label htmlFor="low
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">1,234.56 (Estándar)</SelectItem>
                    <SelectItem value="comma">1.234,56 (Coma)</SelectItem>
                    <SelectItem value="space">1 234.56 (Espacio)</SelectItem>
                  Recibirás alerta
                </Select>
            </TabsCo

              <div className="flex items-
                <Label htmlFor="defaultPaymentMethod">Método de pago por defecto</Label>
                  <p cl
                  value={settings.defaultPaymentMethod}
                  onValueChange={(value: ProfileSettings['defaultPaymentMethod']) => setSettings({ ...settings, defaultPaymentMethod: value })}
                >
                  <SelectTrigger id="defaultPaymentMethod">
                    <SelectValue />
              </div>
                  <SelectContent>
                    <SelectItem value="efectivo">Efectivo</SelectItem>
                    <SelectItem value="transferencia">Transferencia</SelectItem>
                    <SelectItem value="tarjeta">Tarjeta</SelectItem>
                    <SelectItem value="financiamiento">Financiamiento</SelectItem>
                  </SelectContent>
                </Select>


              <div className="space-y-2">
                <Label htmlFor="defaultChannel">Canal por defecto</Label>
                  value
                  value={settings.defaultChannel}
                  onValueChange={(value: ProfileSettings['defaultChannel']) => setSettings({ ...settings, defaultChannel: value })}
                >
              <div className="space-y-2">
                    <SelectValue />
                  id="businessPhon
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
              <div className="flex items
                  type="number"
                  <p clas
                  value={settings.lowStockThreshold}
                  onChange={(e) => setSettings({ ...settings, lowStockThreshold: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">
                  Recibirás alertas cuando el stock caiga por debajo de este número
              </div>
              </div>
            </TabsContent>

            <TabsContent value="notifications" className="space-y-4 mt-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="space-y-0.5">
                  <Label htmlFor="enableNotifications">Habilitar notificaciones</Label>
                  <p className="text-sm text-muted-foreground">
                    Recibe alertas sobre stock bajo y nuevas órdenes
              )}
                </div>
          <DialogFooter
                  id="enableNotifications"
                  checked={settings.enableNotifications}
                  onCheckedChange={(checked) => setSettings({ ...settings, enableNotifications: checked })}
                />
          </DialogFo
      </DialogContent>
                <div className="pl-4 text-sm text-muted-foreground">
                  <p className="mb-2">Se enviarán notificaciones para:</p>
                  <ul className="space-y-1">
                    <li>• Stock bajo en productos</li>
                    <li>• Nuevas órdenes creadas</li>
                    <li>• Órdenes completadas</li>
                  </ul>
                </div>
              )}



              <div className="space-y-2">
                <Label htmlFor="businessAddress">Dirección del negocio</Label>
                <Input

                  value={settings.businessAddress}

                  placeholder="Calle Principal #123"

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


                <div className="space-y-0.5">
                  <Label htmlFor="autoCalculateTax">Calcular impuestos automáticamente</Label>
                  <p className="text-sm text-muted-foreground">
                    Aplicar tasa de impuestos a los precios de productos
                  </p>

                <Switch
                  id="autoCalculateTax"
                  checked={settings.autoCalculateTax}
                  onCheckedChange={(checked) => setSettings({ ...settings, autoCalculateTax: checked })}

              </div>

              {settings.autoCalculateTax && (
                <div className="space-y-2">
                  <Label htmlFor="taxRate">Tasa de impuesto (%)</Label>

                    id="taxRate"

                    min="0"

                    step="0.01"

                    onChange={(e) => setSettings({ ...settings, taxRate: parseFloat(e.target.value) || 0 })}

                </div>

            </TabsContent>

          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>

              Guardar cambios

          </DialogFooter>

      </DialogContent>

  )

