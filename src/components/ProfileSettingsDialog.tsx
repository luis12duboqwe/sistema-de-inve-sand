import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription
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
import { Card } from '@/components/ui/card'
import { CurrencyDollar, Bell, Storefront, Eye } from '@phosphor-icons/react'
import type { Profile, ProfileSettings } from '@/lib/types'
import { formatPrice } from '@/lib/priceFormatter'

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
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configuración de {profile.name}</DialogTitle>
          <DialogDescription>
            Personaliza las opciones de tu perfil de negocio
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="general">
                <CurrencyDollar size={16} className="mr-2" />
                General
              </TabsTrigger>
              <TabsTrigger value="notifications">
                <Bell size={16} className="mr-2" />
                Alertas
              </TabsTrigger>
              <TabsTrigger value="business">
                <Storefront size={16} className="mr-2" />
                Negocio
              </TabsTrigger>
              <TabsTrigger value="preview">
                <Eye size={16} className="mr-2" />
                Vista Previa
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
                    <SelectItem value="HNL">🇭🇳 HNL (Lempira Hondureña)</SelectItem>
                    <SelectItem value="USD">🇺🇸 USD (Dólar Estadounidense)</SelectItem>
                    <SelectItem value="MXN">🇲🇽 MXN (Peso Mexicano)</SelectItem>
                    <SelectItem value="EUR">🇪🇺 EUR (Euro)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  La moneda se aplicará a todos los precios de este perfil
                </p>
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
                    <SelectItem value="standard">Estándar - 1,234.56</SelectItem>
                    <SelectItem value="comma">Europeo - 1.234,56</SelectItem>
                    <SelectItem value="space">Espaciado - 1 234.56</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Ejemplo: {formatPrice(1234.56, settings)}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
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

                <div className="flex items-end">
                  <div className="flex items-center space-x-2 pb-2">
                    <Switch
                      id="autoCalculateTax"
                      checked={settings.autoCalculateTax}
                      onCheckedChange={(checked) => setSettings({ ...settings, autoCalculateTax: checked })}
                    />
                    <Label htmlFor="autoCalculateTax" className="text-sm">
                      Auto-calcular
                    </Label>
                  </div>
                </div>
              </div>

              {settings.autoCalculateTax && (
                <Card className="p-3 bg-accent/10 border-accent/20">
                  <p className="text-xs text-muted-foreground">
                    💡 Los impuestos se calcularán automáticamente en las órdenes. 
                    Ejemplo: L 1,000 + {settings.taxRate}% = {formatPrice(1000 + (1000 * settings.taxRate / 100), settings)}
                  </p>
                </Card>
              )}

              <div className="space-y-2">
                <Label htmlFor="lowStockThreshold">Umbral de Stock Bajo</Label>
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
                    <SelectItem value="efectivo">💵 Efectivo</SelectItem>
                    <SelectItem value="transferencia">🏦 Transferencia</SelectItem>
                    <SelectItem value="tarjeta">💳 Tarjeta</SelectItem>
                    <SelectItem value="financiamiento">📊 Financiamiento</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="defaultChannel">Canal de Venta Predeterminado</Label>
                <Select
                  value={settings.defaultChannel}
                  onValueChange={(v) => setSettings({ ...settings, defaultChannel: v as ProfileSettings['defaultChannel'] })}
                >
                  <SelectTrigger id="defaultChannel">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="whatsapp">💬 WhatsApp</SelectItem>
                    <SelectItem value="facebook">📘 Facebook</SelectItem>
                    <SelectItem value="instagram">📷 Instagram</SelectItem>
                    <SelectItem value="tienda">🏬 Tienda Física</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </TabsContent>

            <TabsContent value="notifications" className="space-y-4 pt-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
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

              {settings.enableNotifications && (
                <Card className="p-4 bg-accent/5 border-accent/20">
                  <p className="text-sm font-medium mb-2">Recibirás alertas para:</p>
                  <ul className="space-y-1 text-sm text-muted-foreground list-disc list-inside">
                    <li>Stock por debajo de {settings.lowStockThreshold} unidades</li>
                    <li>Nuevas órdenes creadas</li>
                    <li>Cambios de estado en órdenes</li>
                  </ul>
                </Card>
              )}
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

              <Card className="p-4 bg-muted/50 border-dashed">
                <p className="text-xs text-muted-foreground">
                  💡 Esta información se puede usar para generar recibos y facturas en el futuro
                </p>
              </Card>
            </TabsContent>

            <TabsContent value="preview" className="space-y-4 pt-4">
              <Card className="p-6">
                <h3 className="font-semibold mb-4">Vista Previa de Configuración</h3>
                
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">Formato de Moneda</p>
                      <p className="font-semibold text-lg">{formatPrice(12345.67, settings)}</p>
                    </div>
                    
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">Impuestos</p>
                      <p className="font-semibold text-lg">
                        {settings.autoCalculateTax ? `${settings.taxRate}% Auto` : 'Desactivado'}
                      </p>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">Método de Pago</p>
                      <p className="font-semibold capitalize">{settings.defaultPaymentMethod}</p>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">Canal de Venta</p>
                      <p className="font-semibold capitalize">{settings.defaultChannel}</p>
                    </div>
                  </div>

                  <div className="border-t pt-4">
                    <p className="text-xs text-muted-foreground mb-2">Ejemplo de Orden</p>
                    <Card className="p-4 bg-muted/30">
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Subtotal:</span>
                          <span className="font-medium">{formatPrice(5000, settings)}</span>
                        </div>
                        {settings.autoCalculateTax && (
                          <div className="flex justify-between text-muted-foreground">
                            <span>Impuesto ({settings.taxRate}%):</span>
                            <span>{formatPrice(5000 * settings.taxRate / 100, settings)}</span>
                          </div>
                        )}
                        <div className="flex justify-between font-bold text-base pt-2 border-t">
                          <span>Total:</span>
                          <span>{formatPrice(settings.autoCalculateTax ? 5000 + (5000 * settings.taxRate / 100) : 5000, settings)}</span>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              </Card>
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
