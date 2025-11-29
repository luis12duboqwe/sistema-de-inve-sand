import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/butto
import { Separator } from '@/components/ui/sepa
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { CurrencyDollar, Bell, Gear, Buildings } from '@phosphor-icons/react'
  open: boolean
import type { Profile, ProfileSettings } from '@/lib/types'

interface ProfileSettingsDialogProps {
  open: boolean
  profile: Profile
  profile,
  onSubmit,
 

export function ProfileSettingsDialog({
  open,
  profile,
  onOpenChange,
  }, [profi
  const handleSubmit = (e: React
    onSubmit(profile.id, settings)

    <Dialog ope
        <DialogHeader>
        </DialogHeader>
          <Tabs defaultValue="general
              <TabsTrigger valu
                General
              <TabsTrigger v
   

                Negocios
              <TabsTrigger value="finan
   

            <TabsCo
                <Label htmlFor="currency">Moneda</La
               

                    <SelectValue />
                  <Sel
                    <SelectItem va
   


                <Label htmlFor="priceFormat">Formato
                  value={settings.priceFormat}
                >
                    <SelectValue />
                  <Sele
                    <SelectItem value=
                  </SelectContent>
              </div>
              <div className="space-y-2">
                <Select
                  onVal
                  <SelectTri
                  </SelectTrigger>
                    <SelectItem va
                    <SelectIte
                  </SelectCo
              </div>
              <div className="space-y-2
                <Select
                  onValueCha
                  <SelectTrigger id="defaultChannel">
                  </SelectTrigger>
                    <Sel
                    <SelectI
                </Selec

                <Label htmlFor="lowStockThreshold">Umbral de stock b
                  id="lowStockThreshold"
                  min="0"
                  onCha
                <p className="text-xs text-
                </p>
            </Tab
            <TabsContent value="notifications" 
                <div className="spa
                  <p className="te
                  </p>
                <Switch
                  onCheckedChange={(checked) => setSettings({ ...settings, en
              </div>
              {settings.enableNotifications && (
                  <p className="te
                    <li>•
                    

            </TabsContent>
            <TabsContent value="business" className="space-y-4 mt-4">
                <Label 
                  id="businessAddress"
                  onChange={(e) => setSettings({ ...settings, businessAddress: e.target.value })}
                /

                <Label htmlFor="bus
                  id="businessPhon
                  onChange={(e) =
                />

                <Label htmlFor="businessEmail">Email del negocio</Lab
                  id="businessEmai
                  value={
                  pl


              <div className="flex items-center justify-between p-4 border rounded-lg">
                  <Labe
                    Aplicar tasa de impuestos a los pre
                </div>
                 
                />

                <div className="sp
                  <Input
                    type="number"
                    max="100"
                    value={settings.taxRate}
                  />
              )}
          </Tabs>
          <DialogFoo

            <Button type="submit">
            </Button>
        </form>
    </Dialog>
}


































































































































