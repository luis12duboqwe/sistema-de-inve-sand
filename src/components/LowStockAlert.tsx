import { useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Warning, CaretDown, CaretUp } from '@phosphor-icons/react'
import type { ProductWithStock, Location } from '@/lib/types'

interface LowStockAlertProps {
  products: ProductWithStock[]
  locations: Location[]
  onProductClick?: (product: ProductWithStock) => void
}

export function LowStockAlert({ products, locations, onProductClick }: LowStockAlertProps) {
  const [isOpen, setIsOpen] = useState(true)
  const threshold = 5 // Default threshold for locations

  const activeLocations = locations.filter(l => l.activo)

  // Flatten products with low stock per location
  const alerts = activeLocations.flatMap(location => {
    return products
      .filter(p => p.activo)
      .map(p => {
        const stockItem = p.stock_items?.find(s => s.location_id === location.id)
        const quantity = stockItem?.cantidad_disponible || 0
        return { product: p, location, quantity }
      })
      .filter(item => item.quantity <= threshold)
  })

  const outOfStock = alerts.filter(a => a.quantity === 0)
  const critical = alerts.filter(a => a.quantity > 0 && a.quantity <= Math.floor(threshold / 2))
  const low = alerts.filter(a => a.quantity > Math.floor(threshold / 2))

  if (alerts.length === 0) {
    return null
  }

  const getSeverityBg = () => {
    if (outOfStock.length > 0) return 'border-destructive/50 bg-destructive/5'
    if (critical.length > 0) return 'border-yellow-500/50 bg-yellow-500/5'
    return 'border-blue-500/50 bg-blue-500/5'
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Alert className={getSeverityBg()}>
        <Warning size={20} className={outOfStock.length > 0 ? 'text-destructive' : 'text-yellow-500'} weight="fill" />
        <AlertTitle className="flex items-center justify-between gap-2">
          <span className={outOfStock.length > 0 ? 'text-destructive' : 'text-yellow-600'}>
            ⚠️ Alertas de Inventario ({alerts.length})
          </span>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="h-6 px-2">
              {isOpen ? <CaretUp size={16} /> : <CaretDown size={16} />}
            </Button>
          </CollapsibleTrigger>
        </AlertTitle>
        <AlertDescription>
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 text-xs">
              {outOfStock.length > 0 && (
                <Badge variant="destructive">
                  {outOfStock.length} agotado{outOfStock.length !== 1 ? 's' : ''}
                </Badge>
              )}
              {critical.length > 0 && (
                <Badge className="bg-yellow-500 text-white hover:bg-yellow-600">
                  {critical.length} crítico{critical.length !== 1 ? 's' : ''}
                </Badge>
              )}
              {low.length > 0 && (
                <Badge variant="secondary">
                  {low.length} bajo{low.length !== 1 ? 's' : ''}
                </Badge>
              )}
              <Badge variant="outline">
                Umbral: {threshold} unidades
              </Badge>
            </div>

            <CollapsibleContent className="space-y-2">
              {outOfStock.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-destructive">
                    Sin Stock ({outOfStock.length})
                  </p>
                  {outOfStock.slice(0, 3).map(({ product, location }) => (
                    <Card
                      key={`${location.id}-${product.id}`}
                      className="p-3 bg-background border-destructive/30 cursor-pointer hover:bg-accent/20 transition-colors"
                      onClick={() => onProductClick?.(product)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{product.nombre}</p>
                          <p className="text-xs text-muted-foreground">
                            {product.sku} • {location.nombre}
                          </p>
                        </div>
                        <Badge variant="destructive" className="shrink-0">0</Badge>
                      </div>
                    </Card>
                  ))}
                  {outOfStock.length > 3 && (
                    <p className="text-xs text-center text-muted-foreground">
                      + {outOfStock.length - 3} más...
                    </p>
                  )}
                </div>
              )}

              {critical.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-yellow-600">
                    Stock Crítico ({critical.length})
                  </p>
                  {critical.slice(0, 3).map(({ product, location, quantity }) => (
                    <Card
                      key={`${location.id}-${product.id}`}
                      className="p-3 bg-background border-yellow-500/30 cursor-pointer hover:bg-accent/20 transition-colors"
                      onClick={() => onProductClick?.(product)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{product.nombre}</p>
                          <p className="text-xs text-muted-foreground">
                            {product.sku} • {location.nombre}
                          </p>
                        </div>
                        <Badge className="bg-yellow-500 text-white shrink-0">{quantity}</Badge>
                      </div>
                    </Card>
                  ))}
                  {critical.length > 3 && (
                    <p className="text-xs text-center text-muted-foreground">
                      + {critical.length - 3} más...
                    </p>
                  )}
                </div>
              )}

              {low.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-muted-foreground">
                    Stock Bajo ({low.length})
                  </p>
                  {low.slice(0, 2).map(({ product, location, quantity }) => (
                    <Card
                      key={`${location.id}-${product.id}`}
                      className="p-3 bg-background cursor-pointer hover:bg-accent/20 transition-colors"
                      onClick={() => onProductClick?.(product)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{product.nombre}</p>
                          <p className="text-xs text-muted-foreground">
                            {product.sku} • {location.nombre}
                          </p>
                        </div>
                        <Badge variant="secondary" className="shrink-0">{quantity}</Badge>
                      </div>
                    </Card>
                  ))}
                  {low.length > 2 && (
                    <p className="text-xs text-center text-muted-foreground">
                      + {low.length - 2} más...
                    </p>
                  )}
                </div>
              )}
            </CollapsibleContent>
          </div>
        </AlertDescription>
      </Alert>
    </Collapsible>
  )
}
