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
import { Warning, Package, CaretDown, CaretUp } from '@phosphor-icons/react'
import type { ProductWithStock, Profile } from '@/lib/types'

interface LowStockAlertProps {
  products: ProductWithStock[]
  profile: Profile
  onProductClick?: (product: ProductWithStock) => void
}

export function LowStockAlert({ products, profile, onProductClick }: LowStockAlertProps) {
  const [isOpen, setIsOpen] = useState(true)
  const threshold = profile.settings?.lowStockThreshold || 5
  const notificationsEnabled = profile.settings?.enableNotifications || false

  if (!notificationsEnabled) {
    return null
  }

  const lowStockProducts = products.filter(
    p => p.profile_id === profile.id && p.activo && p.stock_disponible <= threshold
  )

  const outOfStockProducts = lowStockProducts.filter(p => p.stock_disponible === 0)
  const criticalStockProducts = lowStockProducts.filter(
    p => p.stock_disponible > 0 && p.stock_disponible <= Math.floor(threshold / 2)
  )
  const lowStockOnly = lowStockProducts.filter(
    p => p.stock_disponible > Math.floor(threshold / 2)
  )

  if (lowStockProducts.length === 0) {
    return null
  }

  const getSeverityColor = () => {
    if (outOfStockProducts.length > 0) return 'destructive'
    if (criticalStockProducts.length > 0) return 'warning'
    return 'info'
  }

  const getSeverityBg = () => {
    if (outOfStockProducts.length > 0) return 'border-destructive/50 bg-destructive/5'
    if (criticalStockProducts.length > 0) return 'border-yellow-500/50 bg-yellow-500/5'
    return 'border-blue-500/50 bg-blue-500/5'
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Alert className={getSeverityBg()}>
        <Warning size={20} className={outOfStockProducts.length > 0 ? 'text-destructive' : 'text-yellow-500'} weight="fill" />
        <AlertTitle className="flex items-center justify-between gap-2">
          <span className={outOfStockProducts.length > 0 ? 'text-destructive' : 'text-yellow-600'}>
            ⚠️ Alertas de Inventario - {profile.name}
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
              {outOfStockProducts.length > 0 && (
                <Badge variant="destructive">
                  {outOfStockProducts.length} agotado{outOfStockProducts.length !== 1 ? 's' : ''}
                </Badge>
              )}
              {criticalStockProducts.length > 0 && (
                <Badge className="bg-yellow-500 text-white hover:bg-yellow-600">
                  {criticalStockProducts.length} crítico{criticalStockProducts.length !== 1 ? 's' : ''}
                </Badge>
              )}
              {lowStockOnly.length > 0 && (
                <Badge variant="secondary">
                  {lowStockOnly.length} bajo{lowStockOnly.length !== 1 ? 's' : ''}
                </Badge>
              )}
              <Badge variant="outline">
                Umbral: {threshold} unidades
              </Badge>
            </div>

            <CollapsibleContent className="space-y-2">
              {outOfStockProducts.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-destructive">
                    Sin Stock ({outOfStockProducts.length})
                  </p>
                  {outOfStockProducts.slice(0, 3).map(product => (
                    <Card
                      key={product.id}
                      className="p-3 bg-background border-destructive/30 cursor-pointer hover:bg-accent/20 transition-colors"
                      onClick={() => onProductClick?.(product)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <Package size={16} className="text-destructive shrink-0" weight="fill" />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate">
                              {product.nombre}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {product.marca} {product.modelo}
                            </p>
                          </div>
                        </div>
                        <Badge variant="destructive" className="shrink-0">
                          Agotado
                        </Badge>
                      </div>
                    </Card>
                  ))}
                  {outOfStockProducts.length > 3 && (
                    <p className="text-xs text-muted-foreground text-center">
                      +{outOfStockProducts.length - 3} más agotado{outOfStockProducts.length - 3 !== 1 ? 's' : ''}
                    </p>
                  )}
                </div>
              )}

              {criticalStockProducts.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-yellow-600">
                    Stock Crítico ({criticalStockProducts.length})
                  </p>
                  {criticalStockProducts.slice(0, 3).map(product => (
                    <Card
                      key={product.id}
                      className="p-3 bg-background border-yellow-500/30 cursor-pointer hover:bg-accent/20 transition-colors"
                      onClick={() => onProductClick?.(product)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <Package size={16} className="text-yellow-600 shrink-0" weight="duotone" />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate">
                              {product.nombre}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {product.marca} {product.modelo}
                            </p>
                          </div>
                        </div>
                        <Badge className="bg-yellow-500 text-white shrink-0">
                          {product.stock_disponible} unid.
                        </Badge>
                      </div>
                    </Card>
                  ))}
                  {criticalStockProducts.length > 3 && (
                    <p className="text-xs text-muted-foreground text-center">
                      +{criticalStockProducts.length - 3} más crítico{criticalStockProducts.length - 3 !== 1 ? 's' : ''}
                    </p>
                  )}
                </div>
              )}

              {lowStockOnly.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-muted-foreground">
                    Stock Bajo ({lowStockOnly.length})
                  </p>
                  {lowStockOnly.slice(0, 2).map(product => (
                    <Card
                      key={product.id}
                      className="p-3 bg-background cursor-pointer hover:bg-accent/20 transition-colors"
                      onClick={() => onProductClick?.(product)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <Package size={16} className="text-muted-foreground shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate">
                              {product.nombre}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {product.marca} {product.modelo}
                            </p>
                          </div>
                        </div>
                        <Badge variant="secondary" className="shrink-0">
                          {product.stock_disponible} unid.
                        </Badge>
                      </div>
                    </Card>
                  ))}
                  {lowStockOnly.length > 2 && (
                    <p className="text-xs text-muted-foreground text-center">
                      +{lowStockOnly.length - 2} más con stock bajo
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
