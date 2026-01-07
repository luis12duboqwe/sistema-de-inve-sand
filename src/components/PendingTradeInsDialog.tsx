import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { Wrench, CheckCircle, Gear } from '@phosphor-icons/react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { ProductWithStock, Location } from '@/lib/types'
import { useKV } from '@/hooks/use-kv'
import { TradeInPoliciesDialog } from './TradeInPoliciesDialog'
import { validateTradeInActivation, type TradeInActivationDraft } from '@/lib/validation/tradeInActivationSchema'

interface PendingTradeInsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PendingTradeInsDialog({ open, onOpenChange }: PendingTradeInsDialogProps) {
  const [products, setProducts] = useState<ProductWithStock[]>([])
  const [locations] = useKV<Location[]>('inventory-locations', [])
  const [selectedProduct, setSelectedProduct] = useState<ProductWithStock | null>(null)
  const [showPolicies, setShowPolicies] = useState(false)
  
  // Activation Form State
  const [activationForm, setActivationForm] = useState<TradeInActivationDraft>({
    imei: '',
    color: '',
    capacidad: '',
    precio: '',
    targetLocationId: ''
  })
  type ActivationField = keyof TradeInActivationDraft
  const [formErrors, setFormErrors] = useState<Partial<Record<ActivationField, string>>>({})

  const clearFieldError = (field: ActivationField) => {
    setFormErrors(prev => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  const loadPendingProducts = async () => {
    try {
      const pending = (await inventoryServiceInstance.fetchProducts(undefined, undefined, true))
        .filter(p => p.categoria === 'pendiente_revision')
      setProducts(pending)
    } catch (error) {
      console.error(error)
      toast.error('Error al cargar retomas pendientes')
    }
  }

  useEffect(() => {
    if (open) {
      loadPendingProducts()
    }
  }, [open])

  const handleEditClick = (product: ProductWithStock) => {
    setSelectedProduct(product)
    // Find current location (where stock > 0)
    const currentLocation = product.stock_items?.find(s => s.cantidad_disponible > 0)?.location_id
    
    setActivationForm({
      imei: product.imei || '', // Might be empty if not provided at intake
      color: product.color || '',
      capacidad: product.capacidad || '',
      precio: product.precio.toString(),
      targetLocationId: currentLocation?.toString() || ''
    })
    setFormErrors({})
  }

  const handleActivate = async () => {
    if (!selectedProduct) return

    const validation = validateTradeInActivation(activationForm)
    if (!validation.ok) {
      const mapped: Partial<Record<ActivationField, string>> = {}
      validation.issues.forEach(issue => {
        if (issue.field && ['imei', 'color', 'capacidad', 'precio', 'targetLocationId'].includes(issue.field)) {
          mapped[issue.field as ActivationField] = issue.message
        }
      })
      setFormErrors(mapped)
      toast.error(validation.issues[0]?.message ?? 'Revisa los datos de activación')
      return
    }

    try {
      await inventoryServiceInstance.updateProduct(selectedProduct.id, {
        ...selectedProduct,
        imei: activationForm.imei,
        color: activationForm.color,
        capacidad: activationForm.capacidad,
        precio: parseFloat(activationForm.precio),
        categoria: 'celular',
        activo: true,
        is_serialized: true
      })

      const currentLocationId = selectedProduct.stock_items?.find(s => s.cantidad_disponible > 0)?.location_id
      const targetLocationId = parseInt(activationForm.targetLocationId)

      if (currentLocationId && currentLocationId !== targetLocationId) {
        const transferPayload = {
          product_id: selectedProduct.id,
          from_location_id: currentLocationId,
          to_location_id: targetLocationId,
          cantidad: 1,
          notas: 'Transferencia automática por activación de retoma',
          imeis: [activationForm.imei]
        }

        await inventoryServiceInstance.createStockTransfer(transferPayload)
        toast.success('Producto activado y transferido exitosamente')
      } else {
        toast.success('Producto activado exitosamente')
      }

      setSelectedProduct(null)
      setFormErrors({})
      loadPendingProducts()
    } catch (error) {
      console.error(error)
      toast.error('Error al activar producto')
    }
  }

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[900px]">
        <DialogHeader>
          <div className="flex justify-between items-center">
            <DialogTitle>Gestión de Retomas Pendientes</DialogTitle>
            <Button variant="outline" size="sm" onClick={() => setShowPolicies(true)}>
              <Gear className="mr-2 h-4 w-4" />
              Configurar Políticas IA
            </Button>
          </div>
          <DialogDescription>
            Inspeccione, repare y active los dispositivos recibidos como parte de pago.
          </DialogDescription>
        </DialogHeader>

        {selectedProduct ? (
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between border-b pb-2">
              <h3 className="font-bold text-lg">{selectedProduct.marca} {selectedProduct.modelo}</h3>
              <Button variant="ghost" onClick={() => setSelectedProduct(null)}>Cancelar</Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>IMEI (Verificado)</Label>
                <Input 
                  value={activationForm.imei} 
                  onChange={e => {
                    setActivationForm({...activationForm, imei: e.target.value})
                    clearFieldError('imei')
                  }}
                  placeholder="Escanee o ingrese IMEI"
                />
                {formErrors.imei && (
                  <p className="text-xs text-red-600">{formErrors.imei}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label>Precio de Venta (HNL)</Label>
                <Input 
                  type="number"
                  value={activationForm.precio} 
                  onChange={e => {
                    setActivationForm({...activationForm, precio: e.target.value})
                    clearFieldError('precio')
                  }}
                />
                {formErrors.precio && (
                  <p className="text-xs text-red-600">{formErrors.precio}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label>Color</Label>
                <Input 
                  value={activationForm.color} 
                  onChange={e => {
                    setActivationForm({...activationForm, color: e.target.value})
                    clearFieldError('color')
                  }}
                />
                {formErrors.color && (
                  <p className="text-xs text-red-600">{formErrors.color}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label>Capacidad</Label>
                <Input 
                  value={activationForm.capacidad} 
                  onChange={e => {
                    setActivationForm({...activationForm, capacidad: e.target.value})
                    clearFieldError('capacidad')
                  }}
                />
                {formErrors.capacidad && (
                  <p className="text-xs text-red-600">{formErrors.capacidad}</p>
                )}
              </div>
              <div className="space-y-2 col-span-1 md:col-span-2">
                <Label>Ubicación de Destino (Para Venta)</Label>
                <Select 
                  value={activationForm.targetLocationId} 
                  onValueChange={v => {
                    setActivationForm({...activationForm, targetLocationId: v})
                    clearFieldError('targetLocationId')
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccione ubicación" />
                  </SelectTrigger>
                  <SelectContent>
                    {locations.map(loc => (
                      <SelectItem key={loc.id} value={loc.id.toString()}>
                        {loc.nombre} ({loc.tipo})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Si selecciona una ubicación diferente a la actual, se creará una transferencia automática.
                </p>
                {formErrors.targetLocationId && (
                  <p className="text-xs text-red-600">{formErrors.targetLocationId}</p>
                )}
              </div>
            </div>

            <DialogFooter>
               <Button onClick={handleActivate} className="w-full bg-green-600 hover:bg-green-700">
                 <CheckCircle className="mr-2 h-4 w-4" />
                 Aprobar y Activar para Venta
               </Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="border rounded-md overflow-hidden">
            {/* Desktop View */}
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead>Condición</TableHead>
                    <TableHead>Costo (Retoma)</TableHead>
                    <TableHead>Ubicación Actual</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {products.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                        No hay retomas pendientes de revisión.
                      </TableCell>
                    </TableRow>
                  ) : (
                    products.map(product => (
                      <TableRow key={product.id}>
                        <TableCell>
                          <div className="font-medium">{product.marca} {product.modelo}</div>
                          <div className="text-xs text-muted-foreground">
                            {product.color} {product.capacidad}
                          </div>
                          {!product.imei && <Badge variant="outline" className="text-xs mt-1 border-amber-500 text-amber-600">Sin IMEI</Badge>}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{product.condicion}</Badge>
                        </TableCell>
                        <TableCell>
                          {product.moneda} {(product.costo || 0).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          {product.stock_items?.find(s => s.cantidad_disponible > 0)?.location?.nombre || 'Desconocida'}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button size="sm" onClick={() => handleEditClick(product)}>
                            <Wrench className="mr-2 h-4 w-4" />
                            Revisar
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Mobile View (Cards) */}
            <div className="md:hidden space-y-4 p-4 bg-slate-50">
              {products.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No hay retomas pendientes.
                </div>
              ) : (
                products.map(product => (
                  <div key={product.id} className="bg-white p-4 rounded-lg shadow-sm border space-y-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-bold text-lg">{product.marca} {product.modelo}</div>
                        <div className="text-sm text-muted-foreground">
                          {product.color} {product.capacidad}
                        </div>
                      </div>
                      <Badge variant="secondary">{product.condicion}</Badge>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground block">Costo:</span>
                        <span className="font-medium">{product.moneda} {(product.costo || 0).toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block">Ubicación:</span>
                        <span className="font-medium">{product.stock_items?.find(s => s.cantidad_disponible > 0)?.location?.nombre || 'Desconocida'}</span>
                      </div>
                    </div>

                    {!product.imei && (
                      <div className="bg-amber-50 text-amber-700 text-xs p-2 rounded border border-amber-100">
                        ⚠️ Requiere ingreso de IMEI
                      </div>
                    )}

                    <Button className="w-full" onClick={() => handleEditClick(product)}>
                      <Wrench className="mr-2 h-4 w-4" />
                      Revisar y Activar
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>

    <TradeInPoliciesDialog open={showPolicies} onOpenChange={setShowPolicies} />
    </>
  )
}
