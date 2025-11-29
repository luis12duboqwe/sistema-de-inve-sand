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
            <TabsList className="grid w-full grid-cols-3">
                <CurrencyDollar size={16} />
              </TabsTrigger>
                <Bell size={16} />
              </TabsTri
                <Storefront 
              </TabsTrigger>

              <div className="
                <Select
                  onValueChange={(value: ProfileSettings['currency']) => setSett
                <Storefront size={16} />
                    <Se
              </TabsTrigger>
                    <Se

            <TabsContent value="general" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="currency">Moneda</Label>
                <Select
                  value={settings.currency}
                  onValueChange={(value: ProfileSettings['currency']) => setSettings({ ...settings, currency: value })}
                >
                  <SelectTrigger id="currency">
                  </SelectTrigger>
                  </SelectTrigger>
                    <SelectItem v
                    <SelectItem value="USD">USD ($)</SelectItem>
                    <SelectItem value="EUR">EUR (€)</SelectItem>
                    <SelectItem value="MXN">MXN ($)</SelectItem>
                <Label htmlFor="de
                </Select>
                  on

              <div className="space-y-2">
                <Label htmlFor="priceFormat">Formato de precio</Label>
                    <Se
                  value={settings.priceFormat}
                  onValueChange={(value: ProfileSettings['priceFormat']) => setSettings({ ...settings, priceFormat: value })}
                >
                  <SelectTrigger id="priceFormat">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">1,234.56 (Estándar)</SelectItem>
                    <SelectItem value="space">1 234.56 (Espacio)</SelectItem>
                  </SelectContent>
                  <Select
              </div>

              <div className="space-y-2">
                <Label htmlFor="defaultPaymentMethod">Método de pago por defecto</Label>
                <Select
                <Label htmlFor="lowStockThreshold">Umbr
                  id="lowStockThreshold"
                 
                  onChange={(e) => setSettings({ ...setting
                <p className="text-
                </p>
            </TabsContent>
            <TabsContent value="notifications" className="space-y-4 mt
                <div className="space-y-0.5">
                  <p className="text-sm text-muted-foreground">
                  </p>
                <Switch
                  checked
                />

                <div className="pl-4 text
                  <ul className="space-y-1">
                    <li
                  </ul>
              )}

              <div className="space-y-2">
                <Input
                  value={settings.
                  placeholder="Ca
              </div>
              <div className="space-y-2">
                <Input
                  value={settings.
                  placeho
              </div>

                <Input
                  type="email"
                  onCh
                />

                <div clas
                  <p className="text-sm text-muted-f
                  </p>
                <S
                  checked={settings.autoCalculateTax}
                />

                <div
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
