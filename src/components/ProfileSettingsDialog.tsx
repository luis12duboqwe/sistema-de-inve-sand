import { useState, useEffect } f
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { CurrencyDollar, Bell, Gear, Buildings } from
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
  onOpenChange: (open: boolean) => void
  onSubmit: (profileId: number, settings: ProfileSettings) => void

  currency: 'USD',
  lowStockThres
  defaultPaymentMethod: 'efectivo',
  autoCalculateTax
  onSubmit: (profileId: number, settings: ProfileSettings) => void
}

    <Dialog open={open} onOpenChange={onOp
        <DialogHea
        </Dia
  onSubmit,
}: ProfileSettingsDialogProps) {
  const defaultSettings: ProfileSettings = {
    currency: 'USD',
    taxRate: 0,
    lowStockThreshold: 5,
    enableNotifications: true,
    defaultPaymentMethod: 'efectivo',
    defaultChannel: 'whatsapp',
    autoCalculateTax: false,
    priceFormat: 'standard',
  }

  const [settings, setSettings] = useState<ProfileSettings>(
    profile.settings || defaultSettings
  )

  useEffect(() => {
    setSettings(profile.settings || defaultSettings)
  }, [profile])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(profile.id, settings)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configuración de {profile.name}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <Tabs defaultValue="general">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="general" className="flex items-center gap-2">
                <Gear size={16} />
                General
              </TabsTrigger>
              <TabsTrigger value="notifications" className="flex items-center gap-2">
                <Bell size={16} />
                Notificaciones
              </TabsTrigger>
              <TabsTrigger value="business" className="flex items-center gap-2">
                <Buildings size={16} />
                Negocios
              </TabsTrigger>
              <TabsTrigger value="finance" className="flex items-center gap-2">
                <CurrencyDollar size={16} />
                Finanzas
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
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD - Dólar estadounidense</SelectItem>
                    <SelectItem value="ARS">ARS - Peso Argentino</SelectItem>
                    <SelectItem value="EUR">EUR - Euro</SelectItem>
                    <SelectItem value="MXN">MXN - Peso Mexicano</SelectItem>
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
                    <SelectItem value="space">123 456.78</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="defaultPaymentMethod">Método de pago predeterminado</Label>
                <Select
                  value={settings.defaultPaymentMethod}
                  onValueChange={(value) => setSettings({ ...settings, defaultPaymentMethod: value as ProfileSettings['defaultPaymentMethod'] })}
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
                <Label htmlFor="defaultChannel">Canal de venta predeterminado</Label>
                <Select
                  value={settings.defaultChannel}
                  onValueChange={(value) => setSettings({ ...settings, defaultChannel: value as ProfileSettings['defaultChannel'] })}
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
                  Se mostrarán alertas cuando el stock esté por debajo de este número
                </p>
              </div>
            </TabsContent>

            <TabsContent value="notifications" className="space-y-4 mt-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="space-y-0.5">
                  <Label>Habilitar notificaciones</Label>
                  <p className="text-sm text-muted-foreground">
                    Recibe alertas sobre eventos importantes
                  </p>
                </div>
                <Switch
                  checked={settings.enableNotifications}
                  onCheckedChange={(checked) => setSettings({ ...settings, enableNotifications: checked })}
                />
              </div>

              {settings.enableNotifications && (
                <div className="space-y-2 p-4 bg-muted rounded-lg">
                  <p className="text-sm font-medium">Recibirás notificaciones cuando:</p>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Se cree una nueva orden</li>
                    <li>• El stock esté por debajo del umbral</li>
                    <li>• Una orden cambie de estado</li>
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
                  value={settings.businessPhone || ''}
                  onChange={(e) => setSettings({ ...settings, businessPhone: e.target.value })}
                  placeholder="+1234567890"
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

            <TabsContent value="finance" className="space-y-4 mt-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="space-y-0.5">
                  <Label>Calcular impuestos automáticamente</Label>
                  <p className="text-sm text-muted-foreground">
                    Aplicar tasa de impuestos a los precios
                  </p>
                </div>
                <Switch
                  checked={settings.autoCalculateTax}
                  onCheckedChange={(checked) => setSettings({ ...settings, autoCalculateTax: checked })}
                />
              </div>

              {settings.autoCalculateTax && (
                <div className="space-y-2">
                  <Label htmlFor="taxRate">Tasa de impuestos (%)</Label>
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
              Guardar Configuración
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
