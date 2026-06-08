import { useEffect, useMemo, useState, type KeyboardEvent } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { ArrowsLeftRight, CheckCircle, MapPin, Plus, Trash } from '@phosphor-icons/react'

import type { CreateStockTransferRequest, Location, ProductWithStock } from '@/lib/types'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { calculateLuhnCheckDigit } from '@/lib/utils'

interface TransferStockDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock | null
  products?: ProductWithStock[]
  onTransferComplete: () => void
  initialFromLocationId?: number
  initialToLocationId?: number
}

interface TransferLine {
  id: string
  product_id: number | null
  cantidad: number
  imeis: string[]
  availableImeis: string[]
  scanInput: string
  searchTerm: string
}

const makeLine = (productId: number | null = null): TransferLine => ({
  id: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
  product_id: productId,
  cantidad: 1,
  imeis: [],
  availableImeis: [],
  scanInput: '',
  searchTerm: '',
})

const normalizeImeiScannerToken = (value: string) => {
  const trimmed = value.trim()
  const digits = trimmed.replace(/\D/g, '')

  if (digits.length === 14) {
    try {
      return `${digits}${calculateLuhnCheckDigit(digits)}`
    } catch {
      return digits
    }
  }

  if (digits.length === 15) return digits

  return trimmed
}

const parseImeiScannerTokens = (value: string) => value
  .split(/[\n,;\t ]+/)
  .map(normalizeImeiScannerToken)
  .filter(Boolean)

const isImeiToken = (value: string) => /^\d{15}$/.test(value)

export function TransferStockDialog({
  open,
  onOpenChange,
  product,
  products = [],
  onTransferComplete,
  initialFromLocationId,
  initialToLocationId,
}: TransferStockDialogProps) {
  const [locations, setLocations] = useState<Location[]>([])
  const [fromLocationId, setFromLocationId] = useState<number | null>(initialFromLocationId ?? null)
  const [toLocationId, setToLocationId] = useState<number | null>(initialToLocationId ?? null)
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState<TransferLine[]>([makeLine(product?.id ?? null)])
  const [loading, setLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const selectableProducts = useMemo(() => {
    const byId = new Map<number, ProductWithStock>()
    if (product) byId.set(product.id, product)
    products.forEach(item => byId.set(item.id, item))
    return Array.from(byId.values()).filter(item => item.activo !== false)
  }, [product, products])

  useEffect(() => {
    if (!open) return

    const loadLocations = async () => {
      setLoading(true)
      try {
        const data = await inventoryServiceInstance.getLocations()
        setLocations(data.filter(location => location.activo))
      } catch (error) {
        console.error('Error al cargar ubicaciones:', error)
        toast.error('Error al cargar ubicaciones')
      } finally {
        setLoading(false)
      }
    }

    void loadLocations()
    setFromLocationId(initialFromLocationId ?? null)
    setToLocationId(initialToLocationId ?? null)
    setNotes('')
    setLines([makeLine(product?.id ?? null)])
  }, [open, product?.id, initialFromLocationId, initialToLocationId])

  const getProduct = (productId: number | null) => selectableProducts.find(item => item.id === productId)

  const getAvailableStockForProduct = (item: ProductWithStock | undefined): number => {
    if (!item || !fromLocationId) return 0
    const stockItem = item.stock_items?.find(stock => stock.location_id === fromLocationId)
    const disponible = stockItem?.cantidad_disponible || 0
    const reservado = stockItem?.cantidad_reservada || 0
    return Math.max(disponible - reservado, 0)
  }

  const getProductSearchText = (item: ProductWithStock): string => [
    item.nombre,
    item.sku,
    item.marca,
    item.modelo,
    item.color,
    item.capacidad,
    item.categoria,
  ].filter(Boolean).join(' ').toLowerCase()

  const filterProductsForLine = (line: TransferLine) => {
    const tokens = line.searchTerm.trim().toLowerCase().split(/\s+/).filter(Boolean)
    const selectedIds = new Set(lines.filter(item => item.id !== line.id && item.product_id).map(item => item.product_id))

    return selectableProducts.filter(item => {
      if (selectedIds.has(item.id)) return false
      const stockLibre = getAvailableStockForProduct(item)
      if (fromLocationId && stockLibre <= 0) return false
      if (tokens.length === 0) return true
      const searchText = getProductSearchText(item)
      return tokens.every(token => searchText.includes(token))
    })
  }

  const updateLine = (lineId: string, updates: Partial<TransferLine>) => {
    setLines(previous => previous.map(line => line.id === lineId ? { ...line, ...updates } : line))
  }

  const loadLineImeis = async (lineId: string, productId: number, locationId = fromLocationId) => {
    const selectedProduct = getProduct(productId)
    const isSerialized = Boolean(selectedProduct?.is_serialized || selectedProduct?.categoria === 'celular')
    if (!locationId || !isSerialized) {
      updateLine(lineId, { availableImeis: [], imeis: [], scanInput: '' })
      return
    }

    try {
      const imeis = await inventoryServiceInstance.getAvailableIMEIs(productId, locationId)
      updateLine(lineId, { availableImeis: imeis, imeis: [], scanInput: '' })
    } catch (error) {
      console.error('Error cargando IMEIs para transferencia:', error)
      updateLine(lineId, { availableImeis: [], imeis: [], scanInput: '' })
    }
  }

  const handleFromLocationChange = (value: string) => {
    const nextFrom = value ? Number(value) : null
    setFromLocationId(nextFrom)
    if (toLocationId && nextFrom === toLocationId) setToLocationId(null)
    setLines(previous => previous.map(line => ({ ...line, imeis: [], availableImeis: [], scanInput: '' })))
    for (const line of lines) {
      if (line.product_id) void loadLineImeis(line.id, line.product_id, nextFrom)
    }
  }

  const handleProductSelect = (line: TransferLine, productId: number) => {
    updateLine(line.id, {
      product_id: productId,
      cantidad: 1,
      imeis: [],
      availableImeis: [],
      scanInput: '',
      searchTerm: '',
    })
    void loadLineImeis(line.id, productId)
  }

  const addLine = () => setLines(previous => [...previous, makeLine()])
  const removeLine = (lineId: string) => setLines(previous => previous.length === 1 ? previous : previous.filter(line => line.id !== lineId))

  const addScannedImeisToLine = (line: TransferLine) => {
    const selectedProduct = getProduct(line.product_id)
    if (!selectedProduct) {
      toast.error('Selecciona un producto antes de escanear IMEIs')
      return
    }

    const parsedImeis = parseImeiScannerTokens(line.scanInput)
    if (parsedImeis.length === 0) {
      toast.error('Escanea o escribe un IMEI válido')
      return
    }

    const invalidFormat = parsedImeis.filter(imei => !isImeiToken(imei))
    if (invalidFormat.length > 0) {
      toast.error(`IMEI inválido: ${invalidFormat[0]}`)
      return
    }

    const availableSet = new Set(line.availableImeis)
    const currentSet = new Set(line.imeis)
    const duplicatedInInput = parsedImeis.filter((imei, index) => parsedImeis.indexOf(imei) !== index)
    if (duplicatedInInput.length > 0) {
      toast.error(`IMEI duplicado en el escaneo: ${duplicatedInInput[0]}`)
      return
    }

    const alreadyScanned = parsedImeis.find(imei => currentSet.has(imei))
    if (alreadyScanned) {
      toast.error(`El IMEI ${alreadyScanned} ya fue escaneado para esta transferencia`)
      return
    }

    const unavailable = parsedImeis.find(imei => !availableSet.has(imei))
    if (unavailable) {
      toast.error(`El IMEI ${unavailable} no está disponible en la ubicación de origen`)
      return
    }

    if (line.imeis.length + parsedImeis.length > line.cantidad) {
      toast.error(`Solo debes escanear ${line.cantidad} IMEI(s) para ${selectedProduct.nombre}`)
      return
    }

    updateLine(line.id, { imeis: [...line.imeis, ...parsedImeis], scanInput: '' })
  }

  const handleScanKeyDown = (event: KeyboardEvent<HTMLInputElement>, line: TransferLine) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    addScannedImeisToLine(line)
  }

  const validateAndBuildPayloads = (): CreateStockTransferRequest[] | null => {
    if (!fromLocationId) {
      toast.error('Selecciona la ubicación de origen')
      return null
    }
    if (!toLocationId) {
      toast.error('Selecciona la ubicación de destino')
      return null
    }
    if (fromLocationId === toLocationId) {
      toast.error('La ubicación de destino debe ser diferente al origen')
      return null
    }

    const payloads: CreateStockTransferRequest[] = []
    for (const line of lines) {
      if (!line.product_id) {
        toast.error('Selecciona el producto en todas las líneas')
        return null
      }

      const selectedProduct = getProduct(line.product_id)
      const stockLibre = getAvailableStockForProduct(selectedProduct)
      const isSerialized = Boolean(selectedProduct?.is_serialized || selectedProduct?.categoria === 'celular')

      if (!selectedProduct) {
        toast.error('Uno de los productos ya no está disponible')
        return null
      }
      if (!Number.isInteger(line.cantidad) || line.cantidad <= 0) {
        toast.error(`Ingresa una cantidad válida para ${selectedProduct.nombre}`)
        return null
      }
      if (line.cantidad > stockLibre) {
        toast.error(`Solo hay ${stockLibre} unidades disponibles de ${selectedProduct.nombre}`)
        return null
      }
      if (isSerialized && line.imeis.length !== line.cantidad) {
        toast.error(`Debes seleccionar ${line.cantidad} IMEI(s) para ${selectedProduct.nombre}`)
        return null
      }

      payloads.push({
        product_id: selectedProduct.id,
        from_location_id: fromLocationId,
        to_location_id: toLocationId,
        cantidad: line.cantidad,
        notas: notes.trim() || undefined,
        imeis: line.imeis.length > 0 ? line.imeis : undefined,
        created_by: 'Sistema',
      })
    }

    return payloads
  }

  const handleSubmit = async () => {
    const payloads = validateAndBuildPayloads()
    if (!payloads) return

    setIsSubmitting(true)
    try {
      for (const payload of payloads) {
        await inventoryServiceInstance.createStockTransfer(payload)
      }

      const fromName = locations.find(location => location.id === fromLocationId)?.nombre
      const toName = locations.find(location => location.id === toLocationId)?.nombre
      toast.success(`Transferencia creada: ${payloads.length} modelo(s) de "${fromName}" a "${toName}"`, { duration: 5000 })
      onTransferComplete()
      onOpenChange(false)
    } catch (error) {
      console.error('Error al transferir stock:', error)
      toast.error(error instanceof Error ? error.message : 'Error al transferir stock')
    } finally {
      setIsSubmitting(false)
    }
  }

  const availableDestinations = locations.filter(location => location.id !== fromLocationId)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-[760px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowsLeftRight className="w-5 h-5" weight="bold" />
            Transferir stock entre ubicaciones
          </DialogTitle>
          <DialogDescription>
            Selecciona origen, destino y uno o varios modelos para moverlos en una sola operación.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {loading ? (
            <div className="text-center py-4 text-muted-foreground">Cargando ubicaciones...</div>
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="grid gap-2">
                  <Label>Ubicación origen *</Label>
                  <Select value={fromLocationId ? String(fromLocationId) : ''} onValueChange={handleFromLocationChange}>
                    <SelectTrigger><SelectValue placeholder="Selecciona origen" /></SelectTrigger>
                    <SelectContent>
                      {locations.map(location => (
                        <SelectItem key={location.id} value={String(location.id)}>
                          {location.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label>Ubicación destino *</Label>
                  <Select value={toLocationId ? String(toLocationId) : ''} onValueChange={value => setToLocationId(Number(value))}>
                    <SelectTrigger><SelectValue placeholder="Selecciona destino" /></SelectTrigger>
                    <SelectContent>
                      {availableDestinations.map(location => (
                        <SelectItem key={location.id} value={String(location.id)}>
                          {location.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {fromLocationId && toLocationId && (
                <div className="flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
                  <MapPin size={14} weight="fill" />
                  <span>{locations.find(location => location.id === fromLocationId)?.nombre}</span>
                  <ArrowsLeftRight size={14} />
                  <span>{locations.find(location => location.id === toLocationId)?.nombre}</span>
                </div>
              )}

              <div className="space-y-3 rounded-lg border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <Label>Modelos a transferir</Label>
                    <p className="text-xs text-muted-foreground">Cada línea puede ser un modelo diferente. Para celulares, selecciona los IMEIs exactos.</p>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={addLine} disabled={!fromLocationId}>
                    <Plus size={16} className="mr-1" /> Agregar modelo
                  </Button>
                </div>

                {lines.map((line, index) => {
                  const selectedProduct = getProduct(line.product_id)
                  const isSerialized = Boolean(selectedProduct?.is_serialized || selectedProduct?.categoria === 'celular')
                  const stockLibre = getAvailableStockForProduct(selectedProduct)
                  const filteredProducts = filterProductsForLine(line)

                  return (
                    <div key={line.id} className="rounded-md border bg-background p-3 space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-[1fr_120px_auto] gap-2 md:items-end">
                        <div className="space-y-1.5">
                          <Label>Producto {index + 1}</Label>
                          <Input
                            value={line.searchTerm || selectedProduct?.nombre || ''}
                            onChange={event => updateLine(line.id, { searchTerm: event.target.value, product_id: null, imeis: [], availableImeis: [], scanInput: '' })}
                            placeholder="Buscar por modelo, marca o SKU"
                            disabled={!fromLocationId}
                          />
                          <div className="max-h-32 overflow-y-auto rounded-md border bg-background p-1">
                            {filteredProducts.length === 0 ? (
                              <p className="px-2 py-1.5 text-xs text-muted-foreground">No se encontraron productos con stock.</p>
                            ) : filteredProducts.map(item => {
                              const available = getAvailableStockForProduct(item)
                              const selected = line.product_id === item.id

                              return (
                                <button
                                  key={item.id}
                                  type="button"
                                  className="flex w-full items-center justify-between gap-3 rounded px-2 py-1.5 text-left text-sm hover:bg-muted"
                                  onClick={() => handleProductSelect(line, item.id)}
                                >
                                  <div className="min-w-0">
                                    <p className="truncate font-medium">{item.nombre}</p>
                                    <p className="truncate text-xs text-muted-foreground">
                                      {item.marca || 'Sin marca'} {item.modelo || ''} · SKU: {item.sku || 'Sin SKU'}
                                    </p>
                                  </div>
                                  <Badge variant="secondary" className="shrink-0">{available} uds</Badge>
                                  {selected && <CheckCircle size={16} weight="fill" className="shrink-0 text-primary" />}
                                </button>
                              )
                            })}
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <Label>Cantidad</Label>
                          <Input
                            type="number"
                            min="1"
                            max={stockLibre || undefined}
                            value={line.cantidad || ''}
                            onChange={event => {
                              const nextQuantity = Number(event.target.value) || 0
                              updateLine(line.id, { cantidad: nextQuantity, imeis: line.imeis.slice(0, nextQuantity) })
                            }}
                            disabled={!selectedProduct}
                          />
                          {selectedProduct && <p className="text-xs text-muted-foreground">Máx: {stockLibre}</p>}
                        </div>

                        <Button type="button" variant="outline" size="icon" onClick={() => removeLine(line.id)} disabled={lines.length === 1} title="Quitar modelo">
                          <Trash size={16} />
                        </Button>
                      </div>

                      {isSerialized && selectedProduct && (
                        <div className="rounded-md border border-dashed bg-muted/30 p-2 space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <Label className="text-xs">Escanear IMEIs ({line.imeis.length}/{line.cantidad || 0})</Label>
                            <span className="text-xs text-muted-foreground">{line.availableImeis.length} disponibles</span>
                          </div>
                          {line.availableImeis.length === 0 ? (
                            <p className="text-xs text-muted-foreground">No hay IMEIs disponibles para este producto en origen.</p>
                          ) : (
                            <>
                              <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                                <Input
                                  value={line.scanInput}
                                  onChange={event => updateLine(line.id, { scanInput: event.target.value })}
                                  onKeyDown={event => handleScanKeyDown(event, line)}
                                  placeholder="Escanea IMEI aquí"
                                  className="font-mono text-sm"
                                  inputMode="numeric"
                                  autoComplete="off"
                                />
                                <Button type="button" variant="secondary" onClick={() => addScannedImeisToLine(line)}>
                                  <Plus size={16} className="mr-1" /> Agregar
                                </Button>
                              </div>
                              <p className="text-xs text-muted-foreground">El lector puede enviar Enter; también puedes pegar varios IMEIs separados por coma o salto de línea.</p>
                              {line.imeis.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                  {line.imeis.map(imei => (
                                    <button
                                      key={imei}
                                      type="button"
                                      className="rounded border border-primary bg-primary px-2 py-1 font-mono text-xs text-primary-foreground"
                                      onClick={() => updateLine(line.id, { imeis: line.imeis.filter(item => item !== imei) })}
                                      title="Quitar IMEI escaneado"
                                    >
                                      {imei}
                                    </button>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-xs text-muted-foreground">Aún no has escaneado IMEIs para esta línea.</p>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              <div className="grid gap-2">
                <Label>Notas (opcional)</Label>
                <Textarea value={notes} onChange={event => setNotes(event.target.value)} placeholder="Razón de la transferencia, observaciones, etc." maxLength={500} />
              </div>

              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                La transferencia queda pendiente de recepción. El destino debe confirmar la llegada para completar el movimiento.
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>Cancelar</Button>
          <Button type="button" onClick={handleSubmit} disabled={loading || isSubmitting || lines.length === 0}>
            {isSubmitting ? 'Registrando...' : `Registrar ${lines.length} modelo(s)`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
