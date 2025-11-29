import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switc
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
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
                <Bell size={16} />
              </TabsTrigger>
                <Buildi


              <div className="space-y-2">
                <Select
                  onValueChange={(value) => setSettings({ ...settings, defaultP
                  <SelectTrigger i
                  </SelectTrigger>
                    <SelectI
                    <SelectItem value="tarjeta">Tarjeta</SelectItem>
                  </SelectContent>
              </div>
              <div className
                <Select
                  onValueChange={(
                  <SelectTrigger id="defaultChannel">
                  </SelectTr
                    <SelectItem value="whatsapp">WhatsApp</SelectItem>
                    <SelectItem value="
                </Select>

                <Label 

                  min="0"
                  onChange={(e) => setSet
                <p className="text-sm text-muted-foreground">
                </p>
            </TabsContent>
            <TabsContent value="pricing" className="space-y-4 mt-4">
                <
                  value={settings.currency}
                >
                    <SelectValue /
                  <SelectContent>
                    <SelectItem value="EUR">EUR - Euro</SelectItem>
                    <SelectItem value="ARS">ARS - Peso Argentino</SelectItem>
                    <SelectItem value="CLP">CLP - Peso Chileno</Sele
                    <SelectItem value="BRL">BRL - Real Brasileño</SelectItem>
                </Select>

                <Lab

                >
                    <SelectValue />
                  <Sele
                    <SelectItem value="comma">123
                  </SelectContent>
              </d
              <Separator />
              <div className="flex 
                  <Label htmlFor="
                    Añadir impues
                </div>
                  id="autoCalculateTax"
                  onCheckedChange={(checked) => setSettings({ ...setting
              </div>
              {settings.a
                  <L

                    min="0"
                    step="0.1"
                    on
                </div>
            </TabsContent>
            <TabsContent 
                <div className="space-y-0.5">
                  <p className="text-sm text-muted-foreground">
                  
                <Switch
                  checked={settings.enableNotifications}
                />

                <div class

                    <li>• Se cree una nueva orden</li>
                  </ul>
              )}

              <div className="space-y-2">
                <Input
                 
                  placeholder="Calle, número, c
              </div>
              <div className="spac
                <Input
                  type="tel"
                  onChange={(e) => setSettings({ ...settings, busin
                />

                <Label htmlFor="businessEmail">Email del negocio</Label>
                  id="businessEmail"
                  value={settings.businessEmail || ''}
                  placeholder="contacto@negocio.com"
              </div>
          </Tabs>
          <div class

            <Button type="submit">
            </Button>
        </form>
    </Dialog>
}























































































































