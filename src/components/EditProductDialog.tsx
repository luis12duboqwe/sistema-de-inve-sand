import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MapPin, Package } from '@phosphor-icons/react'
import type { ProductWithStock, Product } from '@/lib/types'
import { StockByLocationDialog } from './StockByLocationDialog'

interface EditProductDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock | null
  onSubmit: (productId: number, updates: Partial<Product>, newStock?: number) => Promise<void>
}

export function EditProductDialog({
  open,
  onOpenChange,
  product,
  onSubmit
}: EditProductDialogProps) {
  const [nombre, setNombre] = useState('')
  const [categoria, setCategoria] = useState<'celular' | 'accesorio'>('celular')
  const [marca, setMarca] = useState('')
  const [modelo, setModelo] = useState('')
  const [capacidad, setCapacidad] = useState('')
  const [condicion, setCondicion] = useState<Product['condicion']>('nuevo')
  const [precio, setPrecio] = useState('')
  const [garantiaMeses, setGarantiaMeses] = useState('')
  const [garantiaCondiciones, setGarantiaCondiciones] = useState('')
  const [stock, setStock] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showStockDialog, setShowStockDialog] = useState(false)
  const [stockRefreshKey, setStockRefreshKey] = useState(0)

  useEffect(() => {
    if (product) {
      setNombre(product.nombre)
      setCategoria(product.categoria)
      setMarca(product.marca)
      setModelo(product.modelo)
      setCapacidad(product.capacidad)
      setCondicion(product.condicion)
      setPrecio(product.precio.toString())
      setGarantiaMeses(product.garantia_meses.toString())
      setGarantiaCondiciones(product.garantia_condiciones || '')
      setStock(product.stock_disponible.toString())
    }
  }, [product])

  const handleSubmit = async () => {
    if (!product || !nombre || !marca || !modelo || !precio) {
      return
    }

    setIsSubmitting(true)
    try {
      const updates: Partial<Product> = {
        nombre,
        categoria,
        marca,
        modelo,
        capacidad,
        condicion,
        precio: parseFloat(precio),
        garantia_meses: parseInt(garantiaMeses),
        garantia_condiciones: garantiaCondiciones.trim() || undefined
      }

      const newStockValue = parseInt(stock)
      await onSubmit(product.id, updates, newStockValue !== product.stock_disponible ? newStockValue : undefined)

      onOpenChange(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!product) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar Producto</DialogTitle>
          <DialogDescription>
            Modifica los detalles del producto y su stock disponible.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="detalles" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="detalles">
              <Package className="mr-2 h-4 w-4" />
              Detalles
            </TabsTrigger>
            <TabsTrigger value="stock">
              <MapPin className="mr-2 h-4 w-4" />
              Stock por Ubicación
            </TabsTrigger>
          </TabsList>

          <TabsContent value="detalles" className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>SKU (solo lectura)</Label>
              <Input value={product.sku} disabled className="bg-muted" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="nombre">Nombre del Producto *</Label>
              <Input
                id="nombre"
                value={nombre}
                onChange={e => setNombre(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="categoria">Categoría *</Label>
                <Select value={categoria} onValueChange={(v) => setCategoria(v as typeof categoria)}>
                  <SelectTrigger id="categoria">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="celular">Celular</SelectItem>
                    <SelectItem value="accesorio">Accesorio</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="condicion">Condición *</Label>
                <Select value={condicion} onValueChange={(v) => setCondicion(v as typeof condicion)}>
                  <SelectTrigger id="condicion">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="nuevo">Nuevo</SelectItem>
                    <SelectItem value="usado">Usado</SelectItem>
                    <SelectItem value="reacondicionado">Reacondicionado</SelectItem>
                    <SelectItem value="grado A">Grado A</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="marca">Marca *</Label>
                <Input
                  id="marca"
                  value={marca}
                  onChange={e => setMarca(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="modelo">Modelo *</Label>
                <Input
                  id="modelo"
                  value={modelo}
                  onChange={e => setModelo(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="capacidad">Capacidad</Label>
                <Input
                  id="capacidad"
                  value={capacidad}
                  onChange={e => setCapacidad(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="precio">Precio (HNL) *</Label>
                <Input
                  id="precio"
                  type="number"
                  min="0"
                  step="0.01"
                  value={precio}
                  onChange={e => setPrecio(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="garantia">Garantía (meses)</Label>
                <Input
                  id="garantia"
                  type="number"
                  min="0"
                  value={garantiaMeses}
                  onChange={e => setGarantiaMeses(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="garantiaCondiciones">Condiciones de Garantía</Label>
              <Textarea
                id="garantiaCondiciones"
                placeholder="Especifica las condiciones de la garantía del producto..."
                value={garantiaCondiciones}
                onChange={e => setGarantiaCondiciones(e.target.value)}
                rows={3}
              />
              <p className="text-sm text-muted-foreground">
                Condiciones y términos aplicables a la garantía del producto
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="stock">Stock Total (solo lectura)</Label>
              <Input
                id="stock"
                type="number"
                value={stock}
                readOnly
                disabled
              />
              <p className="text-sm text-muted-foreground">
                El stock total se calcula automáticamente desde las ubicaciones. Usa la pestaña "Stock por Ubicación" para editar.
              </p>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit} disabled={isSubmitting}>
                {isSubmitting ? 'Guardando...' : 'Guardar Cambios'}
              </Button>
            </DialogFooter>
          </TabsContent>

          <TabsContent value="stock" className="py-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold">Gestionar Stock por Ubicación</h4>
                  <p className="text-sm text-muted-foreground">
                    Edita la cantidad disponible en cada ubicación física
                  </p>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setStockRefreshKey(prev => prev + 1)}
                >
                  Actualizar
                </Button>
              </div>
              
              {product && (
                <StockByLocationDialog
                  key={stockRefreshKey}
                  product={product}
                  open={true}
                  onOpenChange={() => {}}
                  editable={true}
                  asInline={true}
                />
              )}
            </div>

            <DialogFooter className="mt-6">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cerrar
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
