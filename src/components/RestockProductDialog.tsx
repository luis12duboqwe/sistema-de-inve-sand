import { useEffect, useMemo, useRef, useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import type { Location, ProductWithStock, Supplier } from '@/lib/types'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { calculateLuhnCheckDigit } from '@/lib/utils'

interface RestockProductDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  products: ProductWithStock[]
  locations: Location[]
  onSuccess?: (updatedProduct: ProductWithStock) => void
}

export function RestockProductDialog({ open, onOpenChange, products, locations, onSuccess }: RestockProductDialogProps) {
  const [productId, setProductId] = useState<string>('')
  const [productSearch, setProductSearch] = useState('')
  const [locationId, setLocationId] = useState<string>('')
  const [cantidad, setCantidad] = useState<string>('1')
  const [costoUnitario, setCostoUnitario] = useState<string>('')
  const [supplierId, setSupplierId] = useState<string>('none')
  const [notas, setNotas] = useState('')
  const [imeis, setImeis] = useState<string[]>([''])
  const [scanInput, setScanInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const scannerInputRef = useRef<HTMLInputElement | null>(null)
  const wasOpenRef = useRef(false)

  const activeProducts = useMemo(() => products.filter(p => p.activo), [products])
  const activeLocations = useMemo(() => locations.filter(l => l.activo), [locations])
  const selectedProduct = useMemo(
    () => activeProducts.find(p => p.id === Number(productId)),
    [activeProducts, productId]
  )
  const filteredProducts = useMemo(() => {
    const tokens = productSearch.trim().toLowerCase().split(/\s+/).filter(Boolean)
    return activeProducts
      .filter(product => {
        if (tokens.length === 0) return true
        const haystack = [product.nombre, product.sku, product.marca, product.modelo, product.color, product.capacidad]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
        return tokens.every(token => haystack.includes(token))
      })
      .slice(0, 12)
  }, [activeProducts, productSearch])
  const isSerialized = !!selectedProduct?.is_serialized

  useEffect(() => {
    if (!open) {
      wasOpenRef.current = false
      return
    }

    if (!wasOpenRef.current && activeProducts.length > 0) {
      setProductId(String(activeProducts[0].id))
      setProductSearch(activeProducts[0].nombre)
    }

    if (!wasOpenRef.current && !locationId && activeLocations.length > 0) {
      setLocationId(String(activeLocations[0].id))
    }

    wasOpenRef.current = true

    const loadSuppliers = async () => {
      try {
        const data = await inventoryServiceInstance.listSuppliers(false)
        setSuppliers(data)
      } catch {
        setSuppliers([])
      }
    }

    loadSuppliers()
  }, [open, activeProducts, activeLocations, locationId])

  useEffect(() => {
    if (!open || !isSerialized) {
      return
    }

    const qty = Math.max(1, Number(cantidad) || 1)
    setImeis(prev => {
      const next = [...prev]
      while (next.length < qty) next.push('')
      return next.slice(0, qty)
    })
  }, [cantidad, isSerialized, open])

  useEffect(() => {
    if (!open || !selectedProduct) {
      return
    }

    const currentCost = Number(selectedProduct.costo || 0)
    setCostoUnitario(currentCost > 0 ? String(currentCost) : '')
  }, [open, selectedProduct])

  useEffect(() => {
    if (!open || !isSerialized) {
      return
    }

    requestAnimationFrame(() => scannerInputRef.current?.focus())
  }, [open, isSerialized])

  const resetForm = () => {
    setCantidad('1')
    const currentCost = Number(selectedProduct?.costo || 0)
    setCostoUnitario(currentCost > 0 ? String(currentCost) : '')
    setSupplierId('none')
    setNotas('')
    setImeis([''])
    setScanInput('')
  }

  const handleProductSearchChange = (value: string) => {
    setProductSearch(value)
    setProductId('')
  }

  const handleSelectProduct = (product: ProductWithStock) => {
    setProductId(String(product.id))
    setProductSearch(product.nombre)
  }

  const normalizeImeiForScanner = (value: string): string => {
    const cleaned = value.replace(/\D/g, '')
    if (cleaned.length === 14) {
      try {
        return cleaned + calculateLuhnCheckDigit(cleaned)
      } catch {
        return cleaned
      }
    }
    return cleaned
  }

  const handleImeiChange = (index: number, value: string) => {
    const cleaned = value.replace(/\D/g, '')

    let finalValue = cleaned
    if (cleaned.length === 14) {
      try {
        const checkDigit = calculateLuhnCheckDigit(cleaned)
        finalValue = cleaned + checkDigit
        toast.success(`Dígito verificador generado: ${checkDigit}`)
      } catch {
        finalValue = cleaned
      }
    }

    setImeis(prev => {
      const next = [...prev]
      next[index] = finalValue
      return next
    })
  }

  const handleScanImei = () => {
    const scanned = normalizeImeiForScanner(scanInput.trim())
    if (!scanned) {
      toast.error('Escanea o escribe un IMEI válido')
      return
    }

    if (scanned.length !== 15) {
      toast.error('El IMEI escaneado debe tener 15 dígitos')
      return
    }

    if (imeis.includes(scanned)) {
      toast.error('Ese IMEI ya fue registrado en este ingreso')
      setScanInput('')
      return
    }

    const nextIndex = imeis.findIndex(current => !current.trim())
    if (nextIndex === -1) {
      toast.error('Ya se completaron todos los IMEIs requeridos para esta cantidad')
      setScanInput('')
      return
    }

    setImeis(prev => {
      const next = [...prev]
      next[nextIndex] = scanned
      return next
    })
    setScanInput('')
    requestAnimationFrame(() => scannerInputRef.current?.focus())
  }

  const handleSubmit = async () => {
    const parsedProductId = Number(productId)
    const parsedLocationId = Number(locationId)
    const parsedCantidad = Number(cantidad)
    const parsedCostoUnitario = Number(costoUnitario)

    if (!parsedProductId) {
      toast.error('Selecciona un producto')
      return
    }

    if (!parsedLocationId) {
      toast.error('Selecciona una ubicación')
      return
    }

    if (!Number.isFinite(parsedCantidad) || parsedCantidad <= 0) {
      toast.error('La cantidad debe ser mayor a 0')
      return
    }

    if (!Number.isFinite(parsedCostoUnitario) || parsedCostoUnitario <= 0) {
      toast.error('Ingresa el costo unitario de compra')
      return
    }

    const imeisLimpios = imeis.map(i => i.trim()).filter(Boolean)
    if (isSerialized) {
      if (imeisLimpios.length !== parsedCantidad) {
        toast.error(`Debes ingresar ${parsedCantidad} IMEI(s)`) 
        return
      }

      if (new Set(imeisLimpios).size !== imeisLimpios.length) {
        toast.error('No se permiten IMEIs repetidos en el mismo ingreso')
        return
      }
    }

    setIsSubmitting(true)
    try {
      const updated = await inventoryServiceInstance.restockProduct(parsedProductId, {
        location_id: parsedLocationId,
        cantidad: parsedCantidad,
        costo_unitario: parsedCostoUnitario,
        supplier_id: supplierId !== 'none' ? Number(supplierId) : undefined,
        notas: notas.trim() || undefined,
        imeis: isSerialized ? imeisLimpios : undefined,
      })

      toast.success(`Inventario actualizado: +${parsedCantidad} unidad(es)`) 
      onSuccess?.(updated)
      resetForm()
      onOpenChange(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Error al agregar inventario')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Agregar más inventario</DialogTitle>
          <DialogDescription>
            Reabastece un producto existente. Si es serializado, debes registrar los nuevos IMEIs.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Producto *</Label>
              <Input
                value={productSearch}
                onChange={event => handleProductSearchChange(event.target.value)}
                placeholder="Buscar producto, SKU o modelo"
              />
              <div className="max-h-32 overflow-y-auto rounded-md border bg-background p-1">
                {filteredProducts.length === 0 ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground">Sin productos encontrados</p>
                ) : filteredProducts.map(product => (
                  <button
                    key={product.id}
                    type="button"
                    className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-muted"
                    onClick={() => handleSelectProduct(product)}
                  >
                    <span className="min-w-0 truncate">{product.nombre}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">{product.sku || 'Sin SKU'}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Ubicación *</Label>
              <Select value={locationId} onValueChange={setLocationId}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar ubicación" />
                </SelectTrigger>
                <SelectContent>
                  {activeLocations.map(location => (
                    <SelectItem key={location.id} value={String(location.id)}>
                      {location.nombre} ({location.tipo})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Cantidad a agregar *</Label>
              <Input
                type="number"
                min="1"
                value={cantidad}
                onChange={(e) => setCantidad(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Costo unitario de compra *</Label>
              <Input
                type="number"
                min="0.01"
                step="0.01"
                value={costoUnitario}
                onChange={(e) => setCostoUnitario(e.target.value)}
                placeholder="0.00"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Proveedor (opcional)</Label>
              <Select value={supplierId} onValueChange={setSupplierId}>
                <SelectTrigger>
                  <SelectValue placeholder="Sin proveedor" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Sin proveedor</SelectItem>
                  {suppliers.map(supplier => (
                    <SelectItem key={supplier.id} value={String(supplier.id)}>
                      {supplier.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Notas de compra (opcional)</Label>
              <Textarea
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder="Ej: Lote abril, factura #A-1023"
                rows={3}
              />
            </div>
          </div>

          {isSerialized && (
            <div className="space-y-3 rounded-lg border p-4">
              <Label className="font-semibold">Nuevos IMEIs ({Math.max(1, Number(cantidad) || 1)})</Label>
              <div className="space-y-2 rounded-md border border-dashed p-3 bg-muted/30">
                <Label className="text-sm">Escáner 3nStar SC100-1</Label>
                <div className="flex gap-2">
                  <Input
                    ref={scannerInputRef}
                    autoFocus
                    value={scanInput}
                    onChange={(e) => setScanInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        handleScanImei()
                      }
                    }}
                    placeholder="Escanea IMEI aquí (modo teclado + Enter)"
                  />
                  <Button type="button" variant="outline" onClick={handleScanImei} disabled={!scanInput.trim()}>
                    Registrar
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Recomendado: SC100-1 en modo USB HID Keyboard con sufijo Enter (CR).
                </p>
              </div>
              <div className="space-y-2">
                {imeis.map((imei, index) => (
                  <Input
                    key={`${index}-${selectedProduct?.id || 'product'}`}
                    value={imei}
                    onChange={(e) => handleImeiChange(index, e.target.value)}
                    placeholder={`IMEI ${index + 1} (123456789012345)`}
                    maxLength={15}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting || activeProducts.length === 0 || activeLocations.length === 0}>
            {isSubmitting ? 'Guardando...' : 'Agregar más'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
