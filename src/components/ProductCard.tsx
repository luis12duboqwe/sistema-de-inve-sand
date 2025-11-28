import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Phone, Plugs, PencilSimple, Power } from '@phosphor-icons/react'
import type { ProductWithStock } from '@/lib/types'
import { motion } from 'framer-motion'

interface ProductCardProps {
  product: ProductWithStock
  onEdit?: (product: ProductWithStock) => void
  onToggleActive?: (product: ProductWithStock) => void
}

export function ProductCard({ product, onEdit, onToggleActive }: ProductCardProps) {
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
    <Card className={`p-6 hover:shadow-lg transition-all duration-300 ${!product.activo ? 'opacity-60 border-dashed' : ''}`}>
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-1">
            <motion.div
              whileHover={{ scale: 1.1, rotate: 5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              {product.categoria === 'celular' ? (
                <Phone size={24} className="text-primary" weight="duotone" />
              ) : (
                <Plugs size={24} className="text-accent" weight="duotone" />
              )}
            </motion.div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-lg text-card-foreground">
                  {product.nombre}
                </h3>
                {!product.activo && (
                  <Badge variant="outline" className="text-xs bg-muted">
                    Inactivo
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">{product.sku}</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <motion.div
              initial={{ scale: 1 }}
              animate={{ 
                scale: product.stock_disponible < 5 && product.stock_disponible > 0 ? [1, 1.05, 1] : 1 
              }}
              transition={{ 
                repeat: product.stock_disponible < 5 && product.stock_disponible > 0 ? Infinity : 0, 
                duration: 2 
              }}
            >
              <Badge className={getStockBadgeColor(product.stock_disponible)}>
                {product.stock_disponible} en stock
              </Badge>
            </motion.div>
            {onEdit && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onEdit(product)}
                className="h-8 w-8 hover:scale-110 transition-transform"
              >
                <PencilSimple size={18} />
              </Button>
            )}
            {onToggleActive && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onToggleActive(product)}
                className="h-8 w-8 hover:scale-110 transition-transform"
              >
                <Power size={18} className={product.activo ? 'text-accent' : 'text-muted-foreground'} />
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-muted-foreground">Marca:</span>
            <p className="font-medium">{product.marca || 'N/A'}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Modelo:</span>
            <p className="font-medium">{product.modelo || 'N/A'}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Capacidad:</span>
            <p className="font-medium">{product.capacidad || 'N/A'}</p>
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
