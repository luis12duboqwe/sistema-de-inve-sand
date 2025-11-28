import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import type { Profile, Product } from '@/lib/types'

interface NewProductDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profiles: Profile[]
  onSubmit: (product: Omit<Product, 'id' | 'activo'>, stock: number) => Promise<void>
}

export function NewProductDialog({
  open,
  onOpenChange,
  profiles,
  onSubmit
}: NewProductDialogProps) {
  const [profileId, setProfileId] = useState<number>(0)
  const [sku, setSku] = useState('')
  const [nombre, setNombre] = useState('')
  const [categoria, setCategoria] = useState<'celular' | 'accesorio'>('celular')
  const [marca, setMarca] = useState('')
  const [modelo, setModelo] = useState('')
  const [capacidad, setCapacidad] = useState('')
  const [condicion, setCondicion] = useState<Product['condicion']>('nuevo')
  const [precio, setPrecio] = useState('')
  const [moneda] = useState('HNL')
  const [garantiaMeses, setGarantiaMeses] = useState('12')
  const [stockInicial, setStockInicial] = useState('0')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const resetForm = () => {
    setProfileId(0)
    setSku('')
    setNombre('')
    setCategoria('celular')
    setMarca('')
    setModelo('')
    setCapacidad('')
    setCondicion('nuevo')
    setPrecio('')
    setGarantiaMeses('12')
    setStockInicial('0')
  }

  const handleSubmit = async () => {
    if (!profileId || !sku || !nombre || !marca || !modelo || !precio) {
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit(
        {
          profile_id: profileId,
          sku,
          nombre,
          categoria,
          marca,
          modelo,
          capacidad: capacidad || 'N/A',
          condicion,
          precio: parseFloat(precio),
          moneda,
          garantia_meses: parseInt(garantiaMeses)
        },
        parseInt(stockInicial)
      )

      resetForm()
      onOpenChange(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Agregar Nuevo Producto</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="profile">Perfil *</Label>
              <Select value={profileId.toString()} onValueChange={(v) => setProfileId(parseInt(v))}>
                <SelectTrigger id="profile">
                  <SelectValue placeholder="Seleccionar perfil" />
                </SelectTrigger>
                <SelectContent>
                  {profiles.map(profile => (
                    <SelectItem key={profile.id} value={profile.id.toString()}>
                      {profile.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="sku">SKU *</Label>
              <Input
                id="sku"
                value={sku}
                onChange={e => setSku(e.target.value)}
                placeholder="IPH15-128-BLK"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="nombre">Nombre del Producto *</Label>
            <Input
              id="nombre"
              value={nombre}
              onChange={e => setNombre(e.target.value)}
              placeholder="iPhone 15 128GB Negro"
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
                placeholder="Apple, Samsung, Xiaomi..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="modelo">Modelo *</Label>
              <Input
                id="modelo"
                value={modelo}
                onChange={e => setModelo(e.target.value)}
                placeholder="iPhone 15, Galaxy S24..."
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
                placeholder="128GB, 256GB, N/A"
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
                placeholder="15000"
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
            <Label htmlFor="stock">Stock Inicial</Label>
            <Input
              id="stock"
              type="number"
              min="0"
              value={stockInicial}
              onChange={e => setStockInicial(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Agregando...' : 'Agregar Producto'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
