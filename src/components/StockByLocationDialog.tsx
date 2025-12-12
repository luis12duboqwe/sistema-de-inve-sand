import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Badge } from './ui/badge'
import { MapPin, Package, Pencil, Check, Barcode } from '@phosphor-icons/react'
import { toast } from 'sonner'
import type { StockByLocation, Location, Product } from '@/lib/types'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { apiClient } from '@/lib/apiClient'
import { IMEIListDialog } from './IMEIListDialog'

interface StockByLocationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product?: Product
  productId?: number
  productName?: string
  editable?: boolean
  onStockUpdated?: () => void
  asInline?: boolean
}

export function StockByLocationDialog({
  open,
  onOpenChange,
  product,
  productId: propProductId,
  productName: propProductName,
  editable = false,
  onStockUpdated,
  asInline = false
}: StockByLocationDialogProps) {
  const productId = product?.id || propProductId
  const productName = product?.nombre || propProductName || 'Producto'
  
  const [stockItems, setStockItems] = useState<(StockByLocation & { location?: Location })[]>([])
  const [loading, setLoading] = useState(true)
  const [editingLocationId, setEditingLocationId] = useState<number | null>(null)
  const [editingQuantity, setEditingQuantity] = useState(0)
  const [showIMEIs, setShowIMEIs] = useState(false)
  const [selectedLocationId, setSelectedLocationId] = useState<number | undefined>(undefined)

  const loadStockByLocation = async () => {
    if (!productId) return
    setLoading(true)
    try {
      const data = await inventoryServiceInstance.getStockByLocation(productId)
      setStockItems(data || [])
    } catch (error) {
      console.error('Error:', error)
      toast.error('Error al cargar stock por ubicación')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if ((open || asInline) && productId) {
      loadStockByLocation()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, asInline, productId])

  const handleStartEdit = (locationId: number, currentQuantity: number) => {
    setEditingLocationId(locationId)
    setEditingQuantity(currentQuantity)
  }

  const handleSaveStock = async (locationId: number) => {
    if (!productId) return
    if (editingQuantity < 0) {
      toast.error('La cantidad no puede ser negativa')
      return
    }

    try {
      await apiClient.updateStockByLocation(productId, locationId, editingQuantity)
      toast.success('Stock actualizado exitosamente')
      setEditingLocationId(null)
      loadStockByLocation()
      onStockUpdated?.()
    } catch (error) {
      console.error('Error:', error)
      toast.error(error instanceof Error ? error.message : 'Error al actualizar stock')
    }
  }

  const getTotalStock = () => {
    return stockItems.reduce((sum, item) => sum + item.cantidad_disponible, 0)
  }

  const getLocationIcon = (tipo?: string) => {
    switch (tipo) {
      case 'tienda':
        return <Package className="w-4 h-4 text-blue-600" />
      case 'bodega':
        return <Package className="w-4 h-4 text-amber-600" />
      case 'oficina':
        return <MapPin className="w-4 h-4 text-purple-600" />
      default:
        return <MapPin className="w-4 h-4" />
    }
  }

  const content = (
    <>
      {loading ? (
        <div className="py-8 text-center text-muted-foreground">
          Cargando stock...
        </div>
      ) : (
        <div className="space-y-4">
          {/* Total */}
          <div className="bg-primary/10 border border-primary/20 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-lg">Stock Total</span>
              <Badge variant="default" className="text-lg px-4 py-1">
                {getTotalStock()} unidades
              </Badge>
            </div>
          </div>

          {/* Desglose por ubicación */}
          <div className="space-y-2">
            <Label className="text-sm font-semibold">Desglose por Ubicación</Label>
            
            {stockItems.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No hay stock registrado en ninguna ubicación
              </div>
            ) : (
              <div className="border rounded-lg divide-y">
                {stockItems.map((stock) => (
                  <div key={stock.location_id} className="p-4 hover:bg-muted/50 transition-colors">
                    <div className="flex items-center justify-between gap-4">
                      {/* Ubicación info */}
                      <div className="flex items-center gap-3 flex-1">
                        {getLocationIcon(stock.location?.tipo)}
                        <div>
                          <p className="font-medium">
                            {stock.location?.nombre || `Ubicación ${stock.location_id}`}
                          </p>
                          {stock.location?.tipo && (
                            <p className="text-sm text-muted-foreground capitalize">
                              {stock.location.tipo}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Stock display/edit */}
                      {editable && editingLocationId === stock.location_id ? (
                        <div className="flex items-center gap-2">
                          <Input
                            type="number"
                            min="0"
                            value={editingQuantity}
                            onChange={(e) => setEditingQuantity(parseInt(e.target.value) || 0)}
                            className="w-24"
                            autoFocus
                          />
                          <Button
                            size="sm"
                            onClick={() => handleSaveStock(stock.location_id)}
                          >
                            <Check className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditingLocationId(null)}
                          >
                            Cancelar
                          </Button>
                        </div>
                      ) : (
                        <div className="flex flex-col items-end gap-1">
                          <Badge 
                            variant={stock.cantidad_disponible > 0 ? "default" : "secondary"}
                            className="text-base px-3 py-1"
                          >
                            {stock.cantidad_disponible} unidades
                          </Badge>
                          {stock.cantidad_reservada > 0 && (
                            <span className="text-xs text-amber-600">
                              ({stock.cantidad_reservada} reservadas)
                            </span>
                          )}
                          {editable && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleStartEdit(stock.location_id, stock.cantidad_disponible)}
                              className="mt-1"
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                          )}
                          {product?.categoria === 'celular' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setSelectedLocationId(stock.location_id)
                                setShowIMEIs(true)
                              }}
                              className="mt-1"
                              title="Ver IMEIs"
                            >
                              <Barcode className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Acciones (solo si no es inline) */}
          {!asInline && (
            <div className="flex justify-end pt-4 border-t">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cerrar
              </Button>
            </div>
          )}
        </div>
      )}
      
      {productId && (
        <IMEIListDialog
          open={showIMEIs}
          onOpenChange={setShowIMEIs}
          productId={productId}
          productName={productName}
          locationId={selectedLocationId}
        />
      )}
    </>
  )

  if (asInline) {
    return content
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="w-5 h-5" />
            Stock por Ubicación: {productName}
          </DialogTitle>
          <DialogDescription>
            Visualiza y gestiona el inventario de este producto en cada ubicación
          </DialogDescription>
        </DialogHeader>
        {content}
      </DialogContent>
    </Dialog>
  )
}
