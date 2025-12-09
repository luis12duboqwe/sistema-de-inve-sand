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
import { apiClient } from '@/lib/apiClient'
import type { Profile, Product, Supplier } from '@/lib/types'
import { toast } from 'sonner'

// Datos predeterminados para celulares
const MARCAS_CELULAR = [
  'Apple',
  'Samsung',
  'Xiaomi',
  'Motorola',
  'Huawei',
  'OPPO',
  'OnePlus',
  'Realme',
  'Vivo',
  'Google',
  'Nokia',
  'LG',
  'Sony',
  'Otra'
]

const MODELOS_POR_MARCA: Record<string, string[]> = {
  Apple: ['iPhone 15 Pro Max', 'iPhone 15 Pro', 'iPhone 15 Plus', 'iPhone 15', 'iPhone 14 Pro Max', 'iPhone 14 Pro', 'iPhone 14', 'iPhone 13', 'iPhone 12', 'iPhone SE'],
  Samsung: ['Galaxy S24 Ultra', 'Galaxy S24+', 'Galaxy S24', 'Galaxy S23 Ultra', 'Galaxy S23', 'Galaxy A54', 'Galaxy A34', 'Galaxy A24', 'Galaxy A14', 'Galaxy Z Fold 5', 'Galaxy Z Flip 5'],
  Xiaomi: ['Xiaomi 14 Pro', 'Xiaomi 14', 'Xiaomi 13 Pro', 'Xiaomi 13', 'Redmi Note 13 Pro', 'Redmi Note 13', 'Redmi Note 12', 'Redmi 12', 'POCO X6 Pro', 'POCO F5'],
  Motorola: ['Moto G84', 'Moto G73', 'Moto G53', 'Moto G23', 'Moto Edge 40 Pro', 'Moto Edge 30', 'Razr 40'],
  Huawei: ['P60 Pro', 'P50 Pro', 'Mate 50 Pro', 'Nova 11', 'Nova 10'],
  OPPO: ['Find X6 Pro', 'Reno 10 Pro', 'Reno 8 Pro', 'A78', 'A58'],
  OnePlus: ['OnePlus 12', 'OnePlus 11', 'OnePlus Nord 3', 'OnePlus Nord CE 3'],
  Realme: ['GT 5 Pro', 'GT Neo 5', '11 Pro', 'C55', 'C53'],
  Vivo: ['X100 Pro', 'V29', 'Y78', 'Y36'],
  Google: ['Pixel 8 Pro', 'Pixel 8', 'Pixel 7a', 'Pixel 7'],
  Nokia: ['G60', 'G42', 'C32', 'C12'],
  LG: ['Wing', 'Velvet'],
  Sony: ['Xperia 1 V', 'Xperia 5 V', 'Xperia 10 V']
}

const CAPACIDADES = ['64GB', '128GB', '256GB', '512GB', '1TB']

const COLORES = [
  'Negro',
  'Blanco',
  'Azul',
  'Rojo',
  'Verde',
  'Morado',
  'Rosa',
  'Dorado',
  'Plateado',
  'Gris',
  'Titanio',
  'Natural'
]

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
  const [sku, setSku] = useState('')
  const [nombre, setNombre] = useState('')
  const [categoria, setCategoria] = useState<'celular' | 'accesorio'>('celular')
  const [marca, setMarca] = useState('')
  const [marcaOtra, setMarcaOtra] = useState('')
  const [modelo, setModelo] = useState('')
  const [modeloOtro, setModeloOtro] = useState('')
  const [capacidad, setCapacidad] = useState('128GB')
  const [color, setColor] = useState('Negro')
  const [condicion, setCondicion] = useState<Product['condicion']>('nuevo')
  const [precio, setPrecio] = useState('')
  const [garantiaMeses, setGarantiaMeses] = useState('12')
  const [stockInicial, setStockInicial] = useState('1')
  const [supplierId, setSupplierId] = useState<number | undefined>(undefined)
  const [imeis, setImeis] = useState<string[]>([''])
  const [garantiaCondiciones, setGarantiaCondiciones] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])

  // Moneda global (TODO: mover a configuración global)
  const currency = 'HNL'

  // Cargar proveedores globalmente
  useEffect(() => {
    const loadSuppliers = async () => {
      if (open) {
        try {
          const response = await apiClient.request('/suppliers', {
            params: { include_inactive: false }
          })
          
          if (response && response.items) {
            setSuppliers(response.items)
          }
        } catch (err) {
          console.error('Error loading suppliers:', err)
          setSuppliers([])
        }
      }
    }
    
    loadSuppliers()
  }, [open])

  // Auto-generar SKU cuando cambian marca, modelo, capacidad o color
  useEffect(() => {
    if (categoria === 'celular' && marca && modelo && capacidad && color) {
      const marcaActual = marca === 'Otra' ? marcaOtra : marca
      const modeloActual = modelo === 'otro' ? modeloOtro : modelo
      
      if (marcaActual && modeloActual) {
        const marcaCode = marcaActual.substring(0, 3).toUpperCase()
        const modeloCode = modeloActual.replace(/\s+/g, '').substring(0, 8).toUpperCase()
        const capacidadCode = capacidad.replace('GB', '').replace('TB', '000')
        const colorCode = color.substring(0, 3).toUpperCase()
        const skuGenerado = `${marcaCode}-${modeloCode}-${capacidadCode}-${colorCode}`
        setSku(skuGenerado)
      }
    } else if (categoria === 'accesorio' && marca && modelo) {
      const marcaActual = marca === 'Otra' ? marcaOtra : marca
      const modeloActual = modelo === 'otro' ? modeloOtro : modelo
      
      if (marcaActual && modeloActual) {
        const marcaCode = marcaActual.substring(0, 3).toUpperCase()
        const modeloCode = modeloActual.replace(/\s+/g, '').substring(0, 10).toUpperCase()
        const timestamp = Date.now().toString().slice(-4)
        const skuGenerado = `ACC-${marcaCode}-${modeloCode}-${timestamp}`
        setSku(skuGenerado)
      }
    }
  }, [categoria, marca, marcaOtra, modelo, modeloOtro, capacidad, color])

  // Auto-generar nombre del producto
  useEffect(() => {
    if (categoria === 'celular' && marca && modelo) {
      const marcaActual = marca === 'Otra' ? marcaOtra : marca
      const modeloActual = modelo === 'otro' ? modeloOtro : modelo
      
      if (marcaActual && modeloActual) {
        const nombreGenerado = `${marcaActual} ${modeloActual} ${capacidad} ${color}`
        setNombre(nombreGenerado)
      }
    } else if (categoria === 'accesorio' && marca && modelo) {
      const marcaActual = marca === 'Otra' ? marcaOtra : marca
      const modeloActual = modelo === 'otro' ? modeloOtro : modelo
      
      if (marcaActual && modeloActual) {
        const nombreGenerado = `${marcaActual} ${modeloActual}`
        setNombre(nombreGenerado)
      }
    }
  }, [categoria, marca, marcaOtra, modelo, modeloOtro, capacidad, color])

  const resetForm = () => {
    setSku('')
    setNombre('')
    setCategoria('celular')
    setMarca('Samsung')
    setMarcaOtra('')
    setModelo('')
    setModeloOtro('')
    setCapacidad('128GB')
    setColor('Negro')
    setCondicion('nuevo')
    setPrecio('')
    setGarantiaMeses('12')
    setStockInicial('1')
    setSupplierId(undefined)
    setImeis([''])
    setGarantiaCondiciones('')
  }

  // Sincronizar la cantidad de campos IMEI con el stock
  useEffect(() => {
    const stockNum = parseInt(stockInicial) || 1
    setImeis(prev => {
      const newImeis = [...prev]
      // Ajustar el tamaño del array según el stock
      if (newImeis.length < stockNum) {
        // Agregar campos vacíos
        while (newImeis.length < stockNum) {
          newImeis.push('')
        }
      } else if (newImeis.length > stockNum) {
        // Reducir campos
        return newImeis.slice(0, stockNum)
      }
      return newImeis
    })
  }, [stockInicial])

  const handleImeiChange = (index: number, value: string) => {
    setImeis(prev => {
      const newImeis = [...prev]
      newImeis[index] = value
      return newImeis
    })
  }

  const handleSubmit = async () => {
    if (!sku.trim()) {
      toast.error('Por favor ingresa el SKU del producto')
      return
    }
    
    if (!nombre.trim()) {
      toast.error('Por favor ingresa el nombre del producto')
      return
    }
    
    const marcaFinal = marca === 'Otra' ? marcaOtra : marca
    const modeloFinal = modelo === 'otro' ? modeloOtro : modelo
    
    if (!marcaFinal.trim()) {
      toast.error('Por favor ingresa la marca del producto')
      return
    }
    
    if (!modeloFinal.trim()) {
      toast.error('Por favor ingresa el modelo del producto')
      return
    }
    
    if (!precio || parseFloat(precio) <= 0) {
      toast.error('Por favor ingresa un precio válido')
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit(
        {
          profile_id: profiles[0]?.id || 1, // Legacy: usar primer perfil para compatibilidad backend
          supplier_id: supplierId,
          sku,
          nombre,
          categoria,
          marca: marcaFinal,
          modelo: modeloFinal,
          capacidad: categoria === 'celular' ? capacidad : 'N/A',
          condicion,
          precio: parseFloat(precio),
          moneda: currency,
          garantia_meses: parseInt(garantiaMeses),
          garantia_condiciones: garantiaCondiciones.trim() || undefined,
          imeis: imeis.filter(i => i.trim()).length > 0 ? imeis.filter(i => i.trim()) : undefined
        },
        parseInt(stockInicial)
      )

      resetForm()
      onOpenChange(false)
    } catch (error) {
      console.error('Error creating product:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Agregar Nuevo Producto</DialogTitle>
          <DialogDescription>
            Completa los datos del producto. Los celulares tienen opciones predefinidas.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
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
          </div>

          {categoria === 'celular' ? (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="marca">Marca *</Label>
                  <Select value={marca} onValueChange={setMarca}>
                    <SelectTrigger id="marca">
                      <SelectValue placeholder="Seleccionar marca" />
                    </SelectTrigger>
                    <SelectContent>
                      {MARCAS_CELULAR.map(m => (
                        <SelectItem key={m} value={m}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {marca === 'Otra' && (
                    <Input
                      value={marcaOtra}
                      onChange={e => setMarcaOtra(e.target.value)}
                      placeholder="Ingresa la marca"
                      className="mt-2"
                    />
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="modelo">Modelo *</Label>
                  {marca && marca !== 'Otra' && MODELOS_POR_MARCA[marca] ? (
                    <Select value={modelo} onValueChange={setModelo}>
                      <SelectTrigger id="modelo">
                        <SelectValue placeholder="Seleccionar modelo" />
                      </SelectTrigger>
                      <SelectContent>
                        {MODELOS_POR_MARCA[marca].map(m => (
                          <SelectItem key={m} value={m}>{m}</SelectItem>
                        ))}
                        <SelectItem value="otro">Otro modelo...</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      id="modelo"
                      value={modeloOtro}
                      onChange={e => setModeloOtro(e.target.value)}
                      placeholder="Ingresa el modelo"
                    />
                  )}
                  {modelo === 'otro' && (
                    <Input
                      value={modeloOtro}
                      onChange={e => setModeloOtro(e.target.value)}
                      placeholder="Ingresa el modelo"
                      className="mt-2"
                    />
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="capacidad">Capacidad *</Label>
                  <Select value={capacidad} onValueChange={setCapacidad}>
                    <SelectTrigger id="capacidad">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CAPACIDADES.map(c => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="color">Color *</Label>
                  <Select value={color} onValueChange={setColor}>
                    <SelectTrigger id="color">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {COLORES.map(c => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="marca">Marca *</Label>
                  <Input
                    id="marca"
                    value={marca}
                    onChange={e => setMarca(e.target.value)}
                    placeholder="Marca del accesorio"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="modelo">Modelo *</Label>
                  <Input
                    id="modelo"
                    value={modelo}
                    onChange={e => setModelo(e.target.value)}
                    placeholder="Modelo del accesorio"
                  />
                </div>
              </div>
            </>
          )}

          <div className="space-y-2">
            <Label htmlFor="nombre">Nombre del Producto * (generado automáticamente)</Label>
            <Input
              id="nombre"
              value={nombre}
              onChange={e => setNombre(e.target.value)}
              placeholder="Nombre completo del producto"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="sku">SKU * (generado automáticamente)</Label>
            <Input
              id="sku"
              value={sku}
              onChange={e => setSku(e.target.value)}
              placeholder="SKU único del producto"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
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

            <div className="space-y-2">
              <Label htmlFor="stock">Stock Inicial *</Label>
              <Input
                id="stock"
                type="number"
                min="0"
                value={stockInicial}
                onChange={e => setStockInicial(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="precio">Precio ({currency}) *</Label>
              <Input
                id="precio"
                type="number"
                min="0"
                step="0.01"
                value={precio}
                onChange={e => setPrecio(e.target.value)}
                placeholder="15000"
              />
              {selectedProfile?.settings && (
                <p className="text-xs text-muted-foreground">
                  Moneda: {currency}
                </p>
              )}
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

          {/* Campos nuevos: Proveedor e IMEI */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="supplier">Proveedor (Opcional)</Label>
              <Select 
                value={supplierId?.toString() || 'none'} 
                onValueChange={(v) => setSupplierId(v === 'none' ? undefined : parseInt(v))}
              >
                <SelectTrigger id="supplier">
                  <SelectValue placeholder="Sin proveedor" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Sin proveedor</SelectItem>
                  {suppliers.map(supplier => (
                    <SelectItem key={supplier.id} value={supplier.id.toString()}>
                      {supplier.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Para gestionar reclamos y devoluciones
              </p>
            </div>

            {categoria === 'celular' && (
              <div className="space-y-2">
                <Label>IMEI (Opcional)</Label>
                <div className="space-y-2">
                  {imeis.map((imei, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <Input
                        placeholder={`IMEI ${index + 1} (123456789012345)`}
                        value={imei}
                        onChange={e => handleImeiChange(index, e.target.value)}
                        maxLength={15}
                      />
                      <span className="text-sm text-muted-foreground whitespace-nowrap">
                        Unidad {index + 1}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  Ingresa el IMEI único de cada unidad ({imeis.length} unidad{imeis.length > 1 ? 'es' : ''})
                </p>
              </div>
            )}

            {supplierId && (
              <div className="space-y-2">
                <Label htmlFor="garantia-condiciones">Condiciones de Garantía (Opcional)</Label>
                <Textarea
                  id="garantia-condiciones"
                  value={garantiaCondiciones}
                  onChange={e => setGarantiaCondiciones(e.target.value)}
                  placeholder="Ej: Garantía de fábrica. Cubre defectos de manufactura. No cubre daños físicos ni líquidos."
                  rows={3}
                  className="resize-none"
                />
                <p className="text-xs text-muted-foreground">
                  Detalles de la garantía proporcionada por el proveedor
                </p>
              </div>
            )}
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
