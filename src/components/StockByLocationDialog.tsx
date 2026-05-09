import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog'
import { Button } from './ui/button'
import { Label } from './ui/label'
import { Badge } from './ui/badge'
import { MapPin, Package, Barcode } from '@phosphor-icons/react'
import { toast } from 'sonner'
import type { StockByLocation, Location, Product } from '@/lib/types'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { IMEIListDialog } from './IMEIListDialog'

interface StockByLocationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product?: Product
  productId?: number
  productName?: string
  asInline?: boolean
}

export function StockByLocationDialog({
  open,
  onOpenChange,
  product,
  productId: propProductId,
  productName: propProductName,
  asInline = false
}: StockByLocationDialogProps) {
  const productId = product?.id || propProductId
  const productName = product?.nombre || propProductName || 'Producto'
  
  const [stockItems, setStockItems] = useState<(StockByLocation & { location?: Location })[]>([])
  const [loading, setLoading] = useState(true)
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

  const getTotalStock = () => {
    return stockItems.reduce((sum, item) => sum + (item.stock_libre ?? Math.max(item.cantidad_disponible - item.cantidad_reservada, 0)), 0)
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
                {stockItems.map((stock) => {
                  const stockLibre = stock.stock_libre ?? Math.max(stock.cantidad_disponible - stock.cantidad_reservada, 0)
                  return (
                  <div key={stock.location_id} className="p-4 hover:bg-muted/50 transition-colors">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
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

                      <div className="flex flex-row sm:flex-col items-center sm:items-end gap-2 sm:gap-1 mt-2 sm:mt-0 justify-between sm:justify-end w-full sm:w-auto">
                        <Badge 
                          variant={stockLibre > 0 ? "default" : "secondary"}
                          className="text-base px-3 py-1"
                        >
                          {stockLibre} libres
                        </Badge>
                        
                        <div className="flex flex-wrap items-center justify-end gap-1 text-xs">
                          <span className="text-muted-foreground">
                            Total: {stock.cantidad_disponible}
                          </span>
                          {stock.cantidad_reservada > 0 && (
                            <span className="text-amber-600 mr-2 sm:mr-0">
                              Reservadas: {stock.cantidad_reservada}
                            </span>
                          )}
                          {(stock.en_transito_salida || 0) > 0 && (
                            <span className="text-blue-600 mr-2 sm:mr-0">
                              Salida pendiente: {stock.en_transito_salida}
                            </span>
                          )}
                          {(stock.en_transito_entrada || 0) > 0 && (
                            <span className="text-emerald-600 mr-2 sm:mr-0">
                              Entrada pendiente: {stock.en_transito_entrada}
                            </span>
                          )}
                          {(stock.cantidad_defectuosa || 0) > 0 && (
                            <span className="text-red-600 mr-2 sm:mr-0">
                              Defectuosas: {stock.cantidad_defectuosa}
                            </span>
                          )}
                          {product?.categoria === 'celular' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setSelectedLocationId(stock.location_id)
                                setShowIMEIs(true)
                              }}
                              className="h-8 w-8 p-0"
                              title="Ver IMEIs"
                            >
                              <Barcode className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )})}
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
          productSku={product?.sku || ''}
          productColor={product?.color || ''}
          productCapacity={product?.capacidad || ''}
        />
      )}
    </>
  )

  if (asInline) {
    return content
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[96vw] max-w-5xl max-h-[92vh] overflow-y-auto">
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
