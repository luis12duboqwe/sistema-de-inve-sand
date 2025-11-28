import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Phone, Plugs } from '@phosphor-icons/react'
import type { ProductWithStock } from '@/lib/types'

interface ProductCardProps {
  product: ProductWithStock
}

export function ProductCard({ product }: ProductCardProps) {
  const getStockBadgeColor = (stock: number) => {
    if (stock === 0) return 'bg-muted text-muted-foreground'
    if (stock < 5) return 'bg-destructive text-destructive-foreground'
    if (stock < 20) return 'bg-yellow-500 text-white'
    return 'bg-accent text-accent-foreground'
  }

  const getConditionText = (condicion: string) => {
    const map: Record<string, string> = {
      nuevo: 'Nuevo',
      usado: 'Usado',
      reacondicionado: 'Reacondicionado',
      'grado A': 'Grado A'
    }
    return map[condicion] || condicion
  }

  return (
    <Card className="p-6 hover:shadow-lg transition-shadow">
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            {product.categoria === 'celular' ? (
              <Phone size={24} className="text-primary" weight="duotone" />
            ) : (
              <Plugs size={24} className="text-accent" weight="duotone" />
            )}
            <div>
              <h3 className="font-semibold text-lg text-card-foreground">
                {product.nombre}
              </h3>
              <p className="text-sm text-muted-foreground">{product.sku}</p>
            </div>
          </div>
          <Badge className={getStockBadgeColor(product.stock_disponible)}>
            {product.stock_disponible} en stock
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-muted-foreground">Marca:</span>
            <p className="font-medium">{product.marca}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Modelo:</span>
            <p className="font-medium">{product.modelo}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Capacidad:</span>
            <p className="font-medium">{product.capacidad}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Condición:</span>
            <p className="font-medium">{getConditionText(product.condicion)}</p>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t">
          <div>
            <p className="text-2xl font-bold text-primary">
              {product.moneda} {product.precio.toLocaleString()}
            </p>
            {product.garantia_meses > 0 && (
              <p className="text-xs text-muted-foreground">
                Garantía: {product.garantia_meses} meses
              </p>
            )}
          </div>
          <Badge variant="outline" className="text-xs">
            {product.categoria === 'celular' ? 'Celular' : 'Accesorio'}
          </Badge>
        </div>
      </div>
    </Card>
  )
}
