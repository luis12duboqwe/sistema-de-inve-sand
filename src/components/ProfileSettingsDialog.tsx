import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
        <form onSubmit=
          onSubmit(profile.i
          <Tabs defaultValue="gener
              <TabsTrigger va
                General
              <TabsTrigge
 

                Notificaciones
              <TabsTrigger value="business" className="flex items-center gap-2">

          
            <TabsContent value="general" className="
                <Label htmlFor="defaultPaym
                  valu
                >
                    <Se

                    <SelectItem 
                  </SelectCo
              </div>
           
                <Select
            <TabsList className="grid w-full grid-cols-4">
                  <SelectTrigger id="defaultChannel">
                  </SelectTrigger>
                    <Se
              </TabsTrigger>
                  </SelectContent>
              </div>
              <div clas
              </TabsTrigger>
                  type="number"
                  min="0"
                />
                  Se mostrar
              </div>

                Negocios
              </TabsTrigger>
                  onVal

            <TabsContent value="general" className="space-y-4 mt-4">
                    <SelectItem value="US
                    <SelectItem value="ARS">ARS - Peso Argentino</SelectItem>
                <Select
                </Select>

                >
                  value={settings.priceFormat}
                    <SelectValue />
                    <SelectValue /
                  <SelectContent>
                    <SelectItem value="comma">123.456,78</SelectItem>
                </Select>


                <div clas
                  <p

                <Switch
                  checked={settings.autoCalculateTax}
                />

                <div className="space-y-2">
                 
                    type="number"
                    min="0"
                    onChange={(e) 
                </div>
            </TabsContent>
            <TabsContent value="notifications" className="space-y-4 mt-4
                <div className="space-y-0.5">
                  <p className="text-sm text-muted-foreground">
                  </p>
                <Switch
                  ch


                <div className="space-y-2 p-4 bg-muted rounded-lg">
                  <ul 
                    <li>• Se cree una nu
                  </ul>
              )}

              <div className="space-y-2">
                <I
                  value={settings.businessAddress || ''}
                  placeholder="Calle, número, ciudad"
              </div>
              <div c
                <Input

                  onChange={(e) => setSettings({ ...settings, busine
                />

                <Label 
                  id="businessEmail"
                  value={settings.businessEmail || ''}
                 
              </div>
          </Tabs>
          <div className="flex jus
              Cancelar
            <Button type="submit">
            </Button>
        </form>
    </Dialog>
}





                <Label htmlFor="priceFormat">Formato de precio</Label>
                <Select
                  value={settings.priceFormat}
                  onValueChange={(value) => setSettings({ ...settings, priceFormat: value as ProfileSettings['priceFormat'] })}
                >




















































































































