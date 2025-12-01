import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { CurrencyDollar, Bell, Storefront } from '@phosphor-icons/react'

  open: boolean
  onOpenChange: (open: boolean) => void
}

  profile,
  onSubmit,
  const [settings,
    taxRate: 0,
    enableNotifications: false,
 

    autoCalculateTax: false,
  })
  useEffec
      setSettin
  }, [profi
  const handleSubmit = (e: React
    onSubmit(profile.id, settings)

    <Dialog ope
        <DialogHeader>
        </DialogHeader>
        <form onSubmit={handleSubmit}
            <TabsList className
                <Currenc
              </TabsTr
                <Bell 
              </TabsTrigger>
                <Storefront 
    

              <div 
                <Select
                  onValueChange={(v
     
               

                    <SelectItem value="MXN">MXN 
                </Sele

   

          
                    <SelectValue />
                  <SelectContent>
                    <S
                  </SelectContent>
              </div>

                <Select
          <Tabs defaultValue="general">
                >
              <TabsTrigger value="general" className="flex items-center gap-2">
                  </SelectTrigger>
                <span className="hidden sm:inline">General</span>
                    <SelectI
              <TabsTrigger value="notifications" className="flex items-center gap-2">
                  </SelectContent>
                <span className="hidden sm:inline">Notificaciones</span>
                <Label htmlF
              <TabsTrigger value="business" className="flex items-center gap-2">
                  </SelectTrigger>
                <span className="hidden sm:inline">Negocio</span>
                    <SelectI
            </TabsList>

                <div className="space-y-0.5">
                  <p className="text-sm t
                  </p>
                <Switch
                  onCheckedChange={(checked
              </div>
              {se
                  <Label htmlFor="taxRate">Tasa
                    <SelectValue />
                    type="number"
                  <SelectContent>
                    onChange={(e) => setSettings({ ...settings, 
                </div>
            </TabsContent>
                  </SelectContent>
                <div clas
              </div>

                <Switch
                  onCheckedChange={(checked) => setSettings({ ...setti
                <Select
              {settings.enableNotifications &&
                  <p className="mb-2">Recibirás notificaciones para:</p>
                 
                    <li>Órdenes completadas</li>
                </div>

                <Label htmlFor="l
                  id="lowStockThreshold"
                    <SelectItem value="comma">1.234,56 (Coma)</SelectItem>
                  value={settings.lowStockThreshold}
                />
                </Select>
              </div>

              <div className="space-y-2">
                <Input
                  value
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
  )


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


              <div className="flex items-center justify-between py-2">
                <div className="space-y-0.5">
                  <Label>Cálculo automático de impuestos</Label>
                  <p className="text-sm text-muted-foreground">
                    Agregar impuestos automáticamente a los precios

                </div>
                <Switch

                  onCheckedChange={(checked) => setSettings({ ...settings, autoCalculateTax: checked })}

              </div>

              {settings.autoCalculateTax && (
                <div className="space-y-2">
                  <Label htmlFor="taxRate">Tasa de impuesto (%)</Label>













            <TabsContent value="notifications" className="space-y-4 mt-4">
              <div className="flex items-center justify-between py-2">
                <div className="space-y-0.5">
                  <Label>Activar notificaciones</Label>
                  <p className="text-sm text-muted-foreground">
                    Recibir alertas sobre stock bajo y órdenes
                  </p>
                </div>
                <Switch
                  checked={settings.enableNotifications}
                  onCheckedChange={(checked) => setSettings({ ...settings, enableNotifications: checked })}
                />
              </div>

              {settings.enableNotifications && (
                <div className="pl-4 text-sm text-muted-foreground">
                  <p className="mb-2">Recibirás notificaciones para:</p>
                  <ul className="space-y-1 list-disc list-inside">
                    <li>Stock bajo (menos de {settings.lowStockThreshold} unidades)</li>
                    <li>Nuevas órdenes pendientes</li>
                    <li>Órdenes completadas</li>
                  </ul>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="lowStockThreshold">Umbral de stock bajo</Label>
                <Input
                  id="lowStockThreshold"
                  type="number"
                  min="1"
                  value={settings.lowStockThreshold}
                  onChange={(e) => setSettings({ ...settings, lowStockThreshold: parseInt(e.target.value) || 5 })}
                />
                <p className="text-sm text-muted-foreground">
                  Número mínimo de unidades antes de recibir alerta
                </p>
              </div>
            </TabsContent>

            <TabsContent value="business" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="businessAddress">Dirección del negocio</Label>
                <Input
                  id="businessAddress"
                  value={settings.businessAddress}
                  onChange={(e) => setSettings({ ...settings, businessAddress: e.target.value })}
                  placeholder="Calle, número, colonia, ciudad"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="businessPhone">Teléfono del negocio</Label>
                <Input
                  id="businessPhone"
                  value={settings.businessPhone}
                  onChange={(e) => setSettings({ ...settings, businessPhone: e.target.value })}
                  placeholder="+52 123 456 7890"
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
            </TabsContent>















