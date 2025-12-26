import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Phone, Plugs, PencilSimple, Power, Trash, ArrowsLeftRight, ClockCounterClockwise, MapPin, Printer } from '@phosphor-icons/react'
import type { ProductWithStock } from '@/lib/types'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { StockByLocationDialog } from './StockByLocationDialog'
import { PrintLabelsDialog } from './PrintLabelsDialog'

interface ProductCardProps {
  product: ProductWithStock
  onEdit?: (product: ProductWithStock) => void
  onToggleActive?: (product: ProductWithStock) => void
  onDelete?: (product: ProductWithStock) => void
  onTransfer?: (product: ProductWithStock) => void
  onViewHistory?: (product: ProductWithStock) => void
}

export function ProductCard({ product, onEdit, onToggleActive, onDelete, onTransfer, onViewHistory }: ProductCardProps) {
  const [showStockDialog, setShowStockDialog] = useState(false)
  const [showPrintDialog, setShowPrintDialog] = useState(false)
  
  const getStockBadgeColor = (stock: number) => {
    if (stock === 0) return 'bg-muted text-muted-foreground'
    if (stock < 5) return 'bg-destructive text-destructive-foreground'
    if (stock < 20) return 'bg-yellow-500 text-white'
    return 'bg-accent text-accent-foreground'
  }

  const getConditionText = (condicion?: string) => {
    const map: Record<string, string> = {
      nuevo: 'Nuevo',
      usado: 'Usado',
      reacondicionado: 'Reacondicionado',
    }
       // 'grado A' condition removed
    return condicion ? (map[condicion] || condicion) : 'N/A'
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
                  {product.nombre || 'Sin nombre'}
                </h3>
                {!product.activo && (
                  <Badge variant="outline" className="text-xs bg-muted">
                    Inactivo
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground">{product.sku || 'N/A'}</p>
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
                title="Editar producto"
              >
                <PencilSimple size={18} />
              </Button>
            )}
            {onTransfer && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onTransfer(product)}
                className="h-8 w-8 hover:scale-110 transition-transform"
                title="Transferir stock entre ubicaciones"
              >
                <ArrowsLeftRight size={18} />
              </Button>
            )}
            {onViewHistory && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onViewHistory(product)}
                className="h-8 w-8 hover:scale-110 transition-transform"
                title="Ver historial de stock"
              >
                <ClockCounterClockwise size={18} />
              </Button>
            )}
            {product.is_serialized && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowPrintDialog(true)}
                className="h-8 w-8 hover:scale-110 transition-transform"
                title="Imprimir etiquetas"
              >
                <Printer size={18} />
              </Button>
            )}
            {onToggleActive && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onToggleActive(product)}
                className="h-8 w-8 hover:scale-110 transition-transform"
                title={product.activo ? 'Desactivar producto' : 'Activar producto'}
              >
                <Power size={18} className={product.activo ? 'text-accent' : 'text-muted-foreground'} />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onDelete(product)}
                className="h-8 w-8 hover:scale-110 transition-transform hover:text-destructive"
                title="Eliminar producto"
              >
                <Trash size={18} />
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
          {product.imeis && product.imeis.length > 0 && (
            <div className="col-span-2">
              <span className="text-muted-foreground">IMEIs disponibles:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {product.imeis.map((imei, idx) => (
                  <Badge key={idx} variant="secondary" className="text-xs font-mono">
                    {imei}
                  </Badge>
                ))}
              </div>
            </div>
          )}
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
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowStockDialog(true)}
              className="gap-1"
            >
              <MapPin className="w-4 h-4" />
              Ver por Ubicación
            </Button>
            <Badge variant="outline" className="text-xs">
              {product.categoria === 'celular' ? 'Celular' : 'Accesorio'}
            </Badge>
          </div>
        </div>
      </div>
      
      {/* Diálogo de stock por ubicación */}
      <StockByLocationDialog
        open={showStockDialog}
        onOpenChange={setShowStockDialog}
        productId={product.id}
        productName={product.nombre}
        editable={false}
      />

      <PrintLabelsDialog
        open={showPrintDialog}
        onOpenChange={setShowPrintDialog}
        product={product}
      />
    </Card>
  )
}
