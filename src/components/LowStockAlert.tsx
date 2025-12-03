import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Warning, Package } from '@phosphor-icons/react'
import type { ProductWithStock, Profile } from '@/lib/types'

interface LowStockAlertProps {
  products: ProductWithStock[]
  profile: Profile
}

export function LowStockAlert({ products, profile }: LowStockAlertProps) {
  const threshold = profile.settings?.lowStockThreshold || 5
  const notificationsEnabled = profile.settings?.enableNotifications || false

  if (!notificationsEnabled) {
    return null
  }

  const lowStockProducts = products.filter(
    p => p.profile_id === profile.id && p.activo && p.stock_disponible <= threshold
  )

  if (lowStockProducts.length === 0) {
    return null
  }

  return (
    <Alert className="border-destructive/50 bg-destructive/5">
      <Warning size={20} className="text-destructive" weight="fill" />
      <AlertTitle className="text-destructive">
        ⚠️ Stock Bajo en {profile.name}
      </AlertTitle>
      <AlertDescription>
        <p className="text-sm text-muted-foreground mb-3">
          {lowStockProducts.length} producto{lowStockProducts.length !== 1 ? 's' : ''} {lowStockProducts.length !== 1 ? 'están' : 'está'} por debajo del umbral de {threshold} unidades
        </p>
        <div className="space-y-2">
          {lowStockProducts.slice(0, 3).map(product => (
            <Card key={product.id} className="p-3 bg-background">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <Package size={16} className="text-muted-foreground shrink-0" />
                  <span className="text-sm font-medium truncate">
                    {product.nombre}
                  </span>
                </div>
                <Badge variant="destructive" className="shrink-0">
                  {product.stock_disponible} unid.
                </Badge>
              </div>
            </Card>
          ))}
          {lowStockProducts.length > 3 && (
            <p className="text-xs text-muted-foreground text-center">
              +{lowStockProducts.length - 3} producto{lowStockProducts.length - 3 !== 1 ? 's' : ''} más con stock bajo
            </p>
          )}
        </div>
      </AlertDescription>
    </Alert>
  )
}
