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
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { Profile, Product, Supplier, Location, ProductWithStock } from '@/lib/types'
import { toast } from 'sonner'
import { calculateLuhnCheckDigit } from '@/lib/utils'
import { PrintLabelsDialog } from './PrintLabelsDialog'

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

// V2.1: Colores específicos por modelo para evitar sugerencias incorrectas
const COLORES_POR_MODELO: Record<string, string[]> = {
  // Apple
  'iPhone 15 Pro Max': ['Titanio Natural', 'Titanio Azul', 'Titanio Blanco', 'Titanio Negro'],
  'iPhone 15 Pro': ['Titanio Natural', 'Titanio Azul', 'Titanio Blanco', 'Titanio Negro'],
  'iPhone 15 Plus': ['Negro', 'Azul', 'Verde', 'Amarillo', 'Rosa'],
  'iPhone 15': ['Negro', 'Azul', 'Verde', 'Amarillo', 'Rosa'],
  'iPhone 14 Pro Max': ['Morado Oscuro', 'Oro', 'Plata', 'Negro Espacial'],
  'iPhone 14 Pro': ['Morado Oscuro', 'Oro', 'Plata', 'Negro Espacial'],
  'iPhone 14': ['Medianoche', 'Blanco Estelar', 'Azul', 'Púrpura', 'Rojo', 'Amarillo'],
  'iPhone 13': ['Medianoche', 'Blanco Estelar', 'Azul', 'Rosa', 'Verde', 'Rojo'],
  'iPhone 12': ['Negro', 'Blanco', 'Rojo', 'Verde', 'Azul', 'Púrpura'],
  'iPhone SE': ['Medianoche', 'Blanco Estelar', 'Rojo'],
  
  // Samsung
  'Galaxy S24 Ultra': ['Titanium Gray', 'Titanium Black', 'Titanium Violet', 'Titanium Yellow'],
  'Galaxy S24+': ['Onyx Black', 'Marble Gray', 'Cobalt Violet', 'Amber Yellow'],
  'Galaxy S24': ['Onyx Black', 'Marble Gray', 'Cobalt Violet', 'Amber Yellow'],
  'Galaxy S23 Ultra': ['Green', 'Phantom Black', 'Lavender', 'Cream'],
  
  // Xiaomi
  'Xiaomi 14': ['Black', 'White', 'Jade Green', 'Pink'],
  'Redmi Note 13 Pro': ['Midnight Black', 'Aurora Purple', 'Ocean Teal']
}

const COLORES_GENERICOS = [
  'Negro',
  'Blanco',
  'Azul',
  'Rojo',
  'Verde',
  'Morado',
  'Rosa',
  'Dorado',
  'Plateado',
  'Gris'
]

interface NewProductDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profiles: Profile[]
  locations?: Location[]  // V2.0: Ubicaciones disponibles
  onSubmit: (product: Omit<Product, 'id' | 'activo'>, stock: number, locationId?: number) => Promise<ProductWithStock | void>
}

export function NewProductDialog({
  open,
  onOpenChange,
  profiles,
  locations: externalLocations,
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
  const [colorOtro, setColorOtro] = useState('')
  const [condicion, setCondicion] = useState<Product['condicion']>('nuevo')
  const [isSerialized, setIsSerialized] = useState(true)
  const [precio, setPrecio] = useState('')
  const [costo, setCosto] = useState('')
  const [garantiaMeses, setGarantiaMeses] = useState('12')
  const [stockInicial, setStockInicial] = useState('1')
  const [supplierId, setSupplierId] = useState<number | undefined>(undefined)
  const [imeis, setImeis] = useState<string[]>([''])
  const [garantiaCondiciones, setGarantiaCondiciones] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  
  // V2.0: Stock por ubicación
  const [locations, setLocations] = useState<Location[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState<number | undefined>(undefined)
  
  // V2.1: Colores dinámicos
  const [availableColors, setAvailableColors] = useState<string[]>(COLORES_GENERICOS)

  // Moneda configurable
  const [moneda, setMoneda] = useState('HNL')

  // V2.5: Print Labels
  const [createdProduct, setCreatedProduct] = useState<ProductWithStock | null>(null)
  const [showPrintDialog, setShowPrintDialog] = useState(false)

  // Auto-set serialized flag based on category
  useEffect(() => {
    if (categoria === 'celular') {
      setIsSerialized(true)
    } else {
      setIsSerialized(false)
    }
  }, [categoria])

  // V2.1: Actualizar colores disponibles según modelo
  useEffect(() => {
    const modeloActual = modelo === 'otro' ? modeloOtro : modelo
    if (modeloActual && COLORES_POR_MODELO[modeloActual]) {
      setAvailableColors(COLORES_POR_MODELO[modeloActual])
      // Resetear color si el actual no está en la lista nueva
      if (!COLORES_POR_MODELO[modeloActual].includes(color) && color !== 'Otro') {
        setColor(COLORES_POR_MODELO[modeloActual][0])
      }
    } else {
      setAvailableColors(COLORES_GENERICOS)
    }
  }, [modelo, modeloOtro, color])

  // Cargar proveedores y ubicaciones globalmente
  useEffect(() => {
    const loadData = async () => {
      if (open) {
        try {
          // Cargar proveedores usando método público
          const suppliersData = await inventoryServiceInstance.listSuppliers(false)
          setSuppliers(suppliersData)
          
          // Usar ubicaciones externas si se proporcionan, sino cargar
          if (externalLocations && externalLocations.length > 0) {
            setLocations(externalLocations)
            if (!selectedLocationId) {
              setSelectedLocationId(externalLocations[0].id)
            }
          } else {
            // Cargar ubicaciones activas (V2.0) usando método público
            const locationsData = await inventoryServiceInstance.getLocations()
            const activeLocations = locationsData.filter(l => l.activo)
            setLocations(activeLocations)
            // Seleccionar la primera ubicación por defecto
            if (activeLocations.length > 0 && !selectedLocationId) {
              setSelectedLocationId(activeLocations[0].id)
            }
          }
        } catch (err) {
          console.error('Error loading data:', err)
          setSuppliers([])
          setLocations([])
        }
      }
    }
    
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, externalLocations])

  // Auto-generar SKU cuando cambian marca, modelo, capacidad o color
  useEffect(() => {
    if (categoria === 'celular' && marca && modelo && capacidad && color) {
      const marcaActual = marca === 'Otra' ? marcaOtra : marca
      const modeloActual = modelo === 'otro' ? modeloOtro : modelo
      
      if (marcaActual && modeloActual) {
        const marcaCode = marcaActual.substring(0, 3).toUpperCase()
        const modeloCode = modeloActual.replace(/\s+/g, '').substring(0, 8).toUpperCase()
        const capacidadCode = capacidad.replace('GB', '').replace('TB', '000')
        const colorActual = color === 'Otro' ? colorOtro : color
        const colorCode = colorActual.substring(0, 3).toUpperCase()
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
  }, [categoria, marca, marcaOtra, modelo, modeloOtro, capacidad, color, colorOtro])

  // Auto-generar nombre del producto
  useEffect(() => {
    if (categoria === 'celular' && marca && modelo) {
      const marcaActual = marca === 'Otra' ? marcaOtra : marca
      const modeloActual = modelo === 'otro' ? modeloOtro : modelo
      
      if (marcaActual && modeloActual) {
        const colorActual = color === 'Otro' ? colorOtro : color
        const nombreGenerado = `${marcaActual} ${modeloActual} ${capacidad} ${colorActual}`
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
  }, [categoria, marca, marcaOtra, modelo, modeloOtro, capacidad, color, colorOtro])

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
    setCosto('')
    setMoneda('HNL')
    setGarantiaMeses('12')
    setStockInicial('1')
    setSupplierId(undefined)
    setImeis([''])
    setGarantiaCondiciones('')
    // Resetear ubicación a la primera disponible
    if (locations.length > 0) {
      setSelectedLocationId(locations[0].id)
    }
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
    // Solo permitir números
    const cleanValue = value.replace(/\D/g, '')
    
    let finalValue = cleanValue
    
    // Auto-completar dígito 15 si hay 14
    if (cleanValue.length === 14) {
      try {
        const checkDigit = calculateLuhnCheckDigit(cleanValue)
        finalValue = cleanValue + checkDigit
        toast.success(`Dígito verificador generado: ${checkDigit}`)
      } catch {
        // Ignorar error
      }
    }

    setImeis(prev => {
      const newImeis = [...prev]
      newImeis[index] = finalValue
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
    const colorFinal = color === 'Otro' ? colorOtro : color
    
    if (!marcaFinal.trim()) {
      toast.error('Por favor ingresa la marca del producto')
      return
    }
    
    if (!modeloFinal.trim()) {
      toast.error('Por favor ingresa el modelo del producto')
      return
    }

    if (categoria === 'celular' && !colorFinal.trim()) {
      toast.error('Por favor ingresa el color del producto')
      return
    }
    
    if (!precio || parseFloat(precio) <= 0) {
      toast.error('Por favor ingresa un precio válido')
      return
    }
    
    // V2.0: Validar ubicación seleccionada
    if (!selectedLocationId && locations.length > 0) {
      toast.error('📍 Por favor selecciona una ubicación (tienda o bodega) para el stock inicial')
      return
    }

    setIsSubmitting(true)
    try {
      const result = await onSubmit(
        {
          profile_id: null, // V2.0: Productos globales
          supplier_id: supplierId,
          sku,
          nombre,
          categoria,
          marca: marcaFinal,
          modelo: modeloFinal,
          color: colorFinal,
          capacidad: categoria === 'celular' ? capacidad : 'N/A',
          condicion,
          precio: parseFloat(precio),
          costo: parseFloat(costo) || 0,
          moneda,
          garantia_meses: parseInt(garantiaMeses),
          garantia_condiciones: garantiaCondiciones.trim() || undefined,
          is_serialized: isSerialized,
          imeis: imeis.filter(i => i.trim()).length > 0 ? imeis.filter(i => i.trim()) : undefined
        },
        parseInt(stockInicial),
        selectedLocationId  // V2.0: Pasar ubicación seleccionada
      )

      // V2.5: Si es serializado, ofrecer imprimir etiquetas
      if (isSerialized && result) {
        setCreatedProduct(result)
        setShowPrintDialog(true)
        toast.success('Producto creado. Abriendo impresión de etiquetas...')
        resetForm()
        // No cerramos el diálogo principal todavía, lo hará el PrintLabelsDialog al cerrar
      } else {
        resetForm()
        onOpenChange(false)
      }
    } catch (error) {
      console.error('Error creating product:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-2xl max-h-[90vh] overflow-y-auto">
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
            <div className="flex items-center space-x-2 pt-8">
              <Checkbox 
                id="is_serialized" 
                checked={isSerialized} 
                onCheckedChange={(checked) => setIsSerialized(checked as boolean)}
              />
              <Label htmlFor="is_serialized" className="cursor-pointer">
                Producto Serializado (requiere IMEI)
              </Label>
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
                      {availableColors.map(c => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                      <SelectItem value="Otro">Otro color...</SelectItem>
                    </SelectContent>
                  </Select>
                  {color === 'Otro' && (
                    <Input
                      value={colorOtro}
                      onChange={e => setColorOtro(e.target.value)}
                      placeholder="Ej. Sierra Blue, Deep Purple"
                      className="mt-2"
                    />
                  )}
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

          {/* V2.0: Selector de ubicación para stock inicial */}
          {locations.length > 0 && (
            <div className="space-y-2 rounded-lg border border-blue-200 bg-blue-50/50 p-4">
              <Label htmlFor="location" className="text-base font-semibold flex items-center gap-2">
                <span className="text-blue-600">📍</span>
                Ubicación para Stock Inicial *
              </Label>
              <Select 
                value={selectedLocationId?.toString()} 
                onValueChange={(v) => setSelectedLocationId(parseInt(v))}
              >
                <SelectTrigger id="location" className="bg-white">
                  <SelectValue placeholder="Seleccionar tienda o bodega" />
                </SelectTrigger>
                <SelectContent>
                  {locations.map(location => (
                    <SelectItem key={location.id} value={location.id.toString()}>
                      📍 {location.nombre} ({location.tipo === 'tienda' ? '🏪 Tienda' : location.tipo === 'bodega' ? '📦 Bodega' : '🏢 ' + location.tipo})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-blue-600 font-medium">
                💡 El stock inicial ({stockInicial || 0} unidades) se agregará a esta ubicación
              </p>
            </div>
          )}

          {/* Alerta si no hay ubicaciones */}
          {locations.length === 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4">
              <p className="text-sm text-amber-800 font-medium">
                ⚠️ No hay ubicaciones disponibles. Por favor crea primero una ubicación (tienda o bodega) en la pestaña de Ubicaciones.
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="grid grid-cols-3 gap-2">
              <div className="col-span-2 space-y-2">
                <Label htmlFor="precio">Precio Venta *</Label>
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
                <Label htmlFor="moneda">Moneda</Label>
                <Select value={moneda} onValueChange={setMoneda}>
                  <SelectTrigger id="moneda">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="HNL">HNL</SelectItem>
                    <SelectItem value="USD">USD</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="costo">Costo (Reportes)</Label>
              <Input
                id="costo"
                type="number"
                min="0"
                step="0.01"
                value={costo}
                onChange={e => setCosto(e.target.value)}
                placeholder="0.00"
              />
            </div>
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

            {isSerialized && (
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

    {createdProduct && (
      <PrintLabelsDialog
        open={showPrintDialog}
        onOpenChange={(open) => {
          setShowPrintDialog(open)
          if (!open) {
            setCreatedProduct(null)
            onOpenChange(false) // Close parent dialog when print dialog closes
          }
        }}
        product={createdProduct}
      />
    )}
    </>
  )
}
