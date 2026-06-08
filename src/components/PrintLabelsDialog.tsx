import { useState, useEffect, useMemo } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { ProductIMEI, ProductWithStock } from '@/lib/types'
import { Printer } from '@phosphor-icons/react'
import { useKV } from '@/hooks/use-kv'
import { buildLabelsPrintHtml, DEFAULT_LABEL_PRINT_SETTINGS, LABEL_SIZE_PRESETS, LabelPresetId, LabelPrintSettings } from '@/lib/labelPrint'

interface PrintLabelsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product?: ProductWithStock
  products?: ProductWithStock[]
}

interface PrintableImeiOption {
  key: string
  productId: number
  productName: string
  sku: string
  imei: string
  color?: string
  capacity?: string
  locationName?: string
}

export function PrintLabelsDialog({ open, onOpenChange, product, products = [] }: PrintLabelsDialogProps) {
  const [labelOptions, setLabelOptions] = useState<PrintableImeiOption[]>([])
  const [selectedImeis, setSelectedImeis] = useState<string[]>([])
  const [imeiSearch, setImeiSearch] = useState('')
  const [labelPrintSettings, setLabelPrintSettings] = useKV<LabelPrintSettings>('settings_label_print', DEFAULT_LABEL_PRINT_SETTINGS)
  const bulkMode = !product

  const filteredOptions = useMemo(() => {
    const tokens = imeiSearch.trim().toLowerCase().split(/\s+/).filter(Boolean)
    if (!tokens.length) return labelOptions

    return labelOptions.filter(option => {
      const haystack = [
        option.imei,
        option.productName,
        option.sku,
        option.color,
        option.capacity,
        option.locationName,
      ].filter(Boolean).join(' ').toLowerCase()
      return tokens.every(token => haystack.includes(token))
    })
  }, [imeiSearch, labelOptions])

  const selectedOptions = useMemo(() => {
    const selected = new Set(selectedImeis)
    return labelOptions.filter(option => selected.has(option.key))
  }, [labelOptions, selectedImeis])

  const productsWithOptions = useMemo(() => {
    const grouped = new Map<number, { productName: string; sku: string; count: number; keys: string[] }>()
    for (const option of labelOptions) {
      const current = grouped.get(option.productId) || { productName: option.productName, sku: option.sku, count: 0, keys: [] }
      current.count += 1
      current.keys.push(option.key)
      grouped.set(option.productId, current)
    }
    return Array.from(grouped.entries()).map(([productId, item]) => ({ productId, ...item }))
  }, [labelOptions])

  useEffect(() => {
    if (!open) return

    if (product?.is_serialized) {
      const fetchAll = async () => {
        const allOptions: PrintableImeiOption[] = []
        if (product.stock_items) {
            for (const stock of product.stock_items) {
                if (stock.cantidad_disponible > 0) {
                    try {
                      const locImeis = await inventoryServiceInstance.getAvailableIMEIs(product.id, stock.location_id)
                      allOptions.push(...locImeis.map(imei => ({
                        key: `${product.id}:${imei}`,
                        productId: product.id,
                        productName: product.nombre,
                        sku: product.sku,
                        imei,
                        color: product.color,
                        capacity: product.capacidad,
                        locationName: stock.location?.nombre,
                      })))
                    } catch (error) {
                      console.warn('Error obteniendo IMEIs para impresión', error)
                    }
                }
            }
        }
        const unique = Array.from(new Map(allOptions.map(option => [option.key, option])).values())
        setLabelOptions(unique)
        setSelectedImeis(unique.map(option => option.key))
        setImeiSearch('')
      }
      void fetchAll()
      return
    }

    if (bulkMode) {
      const fetchBulk = async () => {
        try {
          const productById = new Map(products.map(item => [item.id, item] as const))
          const serializedProducts = products.filter(item => item.activo !== false && (item.is_serialized || item.categoria === 'celular'))
          const serializedIds = new Set(serializedProducts.map(item => item.id))
          const records = await inventoryServiceInstance.listProductIMEIs({ vendido: false })
          const availableRecords = records.filter(record => (
            serializedIds.has(record.product_id) &&
            !record.vendido &&
            !record.order_id &&
            !record.transfer_id
          ))
          const options = availableRecords.map((record: ProductIMEI) => {
            const item = productById.get(record.product_id)
            return {
              key: `${record.product_id}:${record.imei}`,
              productId: record.product_id,
              productName: item?.nombre || record.product_name || `Producto ${record.product_id}`,
              sku: item?.sku || '',
              imei: record.imei,
              color: item?.color,
              capacity: item?.capacidad,
              locationName: record.location_name,
            }
          })
          setLabelOptions(options)
          setSelectedImeis([])
          setImeiSearch('')
        } catch (error) {
          console.warn('Error obteniendo IMEIs bulk para impresión', error)
          setLabelOptions([])
          setSelectedImeis([])
        }
      }
      void fetchBulk()
    }
  }, [open, product, products, bulkMode])

  const handlePrint = () => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return

    const html = buildLabelsPrintHtml(
      product ? `Etiquetas - ${product.nombre}` : 'Etiquetas bulk',
      selectedOptions.map(option => ({
        productName: option.productName,
        sku: option.sku,
        imei: option.imei,
        color: option.color,
        capacity: option.capacity,
      })),
      labelPrintSettings,
    )

    printWindow.document.write(html)
    printWindow.document.close()
  }

  const setAllSelected = () => setSelectedImeis(labelOptions.map(option => option.key))
  const setFilteredSelected = () => {
    const existing = new Set(selectedImeis)
    for (const option of filteredOptions) existing.add(option.key)
    setSelectedImeis(Array.from(existing))
  }
  const clearAllSelected = () => setSelectedImeis([])
  const toggleProductSelection = (keys: string[]) => {
    const selected = new Set(selectedImeis)
    const allSelected = keys.every(key => selected.has(key))
    if (allSelected) {
      keys.forEach(key => selected.delete(key))
    } else {
      keys.forEach(key => selected.add(key))
    }
    setSelectedImeis(Array.from(selected))
  }

  const applyPreset = (preset: LabelPresetId) => {
    if (preset === 'custom') {
      setLabelPrintSettings(prev => ({
        ...prev,
        preset,
      }))
      return
    }

    const presetConfig = LABEL_SIZE_PRESETS[preset]
    setLabelPrintSettings(prev => ({
      ...prev,
      preset,
      widthMm: presetConfig.widthMm,
      heightMm: presetConfig.heightMm,
    }))
  }

  const updateNumericSetting = (key: 'widthMm' | 'heightMm' | 'edgeMarginMm' | 'offsetXmm' | 'offsetYmm', value: string) => {
    const parsed = Number(value)
    setLabelPrintSettings(prev => ({
      ...prev,
      preset: key === 'widthMm' || key === 'heightMm' ? 'custom' : prev.preset,
      [key]: Number.isFinite(parsed) ? parsed : 0,
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{product ? `Imprimir Etiquetas: ${product.nombre}` : 'Impresión bulk de etiquetas'}</DialogTitle>
        </DialogHeader>
        <div className="py-4 space-y-6">
            <div className="rounded-lg border p-4 space-y-4">
                <div>
                    <h3 className="text-sm font-semibold">Ajuste para impresora térmica</h3>
                    <p className="text-xs text-muted-foreground">
                      Cada etiqueta ahora se imprime como una página individual con tamaño exacto en mm.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label>Tamaño de etiqueta</Label>
                        <Select value={labelPrintSettings.preset} onValueChange={(value) => applyPreset(value as LabelPresetId)}>
                            <SelectTrigger className="w-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="50x25">50 x 25 mm</SelectItem>
                                <SelectItem value="58x30">58 x 30 mm</SelectItem>
                                <SelectItem value="80x50">80 x 50 mm</SelectItem>
                                <SelectItem value="custom">Personalizado</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground flex items-center">
                        Si sale corrida, ajusta los offsets en pasos de 0.5 mm.
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Orientación</Label>
                    <Select
                      value={labelPrintSettings.orientation}
                      onValueChange={(value) => setLabelPrintSettings(prev => ({
                        ...prev,
                        orientation: value === 'vertical' ? 'vertical' : 'horizontal',
                      }))}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="horizontal">Horizontal</SelectItem>
                        <SelectItem value="vertical">Vertical</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground flex items-center">
                    Vertical intercambia ancho y alto para evitar que el contenido quede montado.
                  </div>
                </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Distribución</Label>
                      <Select
                        value={String(labelPrintSettings.labelsPerPage)}
                        onValueChange={(value) => setLabelPrintSettings(prev => ({
                        ...prev,
                        labelsPerPage: value === '3' ? 3 : 1,
                        }))}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">1 etiqueta por cuadro</SelectItem>
                          <SelectItem value="3">3 mini-etiquetas por cuadro</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground flex items-center">
                      El modo de 3 mini-etiquetas agrupa hasta 3 IMEIs dentro de un mismo cuadro físico.
                    </div>
                  </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <div className="space-y-2">
                        <Label htmlFor="label-width">Ancho (mm)</Label>
                        <Input
                          id="label-width"
                          type="number"
                          min="20"
                          max="120"
                          step="0.5"
                          value={labelPrintSettings.widthMm}
                          onChange={(e) => updateNumericSetting('widthMm', e.target.value)}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="label-height">Alto (mm)</Label>
                        <Input
                          id="label-height"
                          type="number"
                          min="10"
                          max="80"
                          step="0.5"
                          value={labelPrintSettings.heightMm}
                          onChange={(e) => updateNumericSetting('heightMm', e.target.value)}
                        />
                    </div>
                      <div className="space-y-2">
                        <Label htmlFor="label-edge-margin">Margen (mm)</Label>
                        <Input
                          id="label-edge-margin"
                          type="number"
                          min="0"
                          max="6"
                          step="0.1"
                          value={labelPrintSettings.edgeMarginMm}
                          onChange={(e) => updateNumericSetting('edgeMarginMm', e.target.value)}
                        />
                      </div>
                    <div className="space-y-2">
                        <Label htmlFor="label-offset-x">Offset X (mm)</Label>
                        <Input
                          id="label-offset-x"
                          type="number"
                          min="-10"
                          max="10"
                          step="0.5"
                          value={labelPrintSettings.offsetXmm}
                          onChange={(e) => updateNumericSetting('offsetXmm', e.target.value)}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="label-offset-y">Offset Y (mm)</Label>
                        <Input
                          id="label-offset-y"
                          type="number"
                          min="-10"
                          max="10"
                          step="0.5"
                          value={labelPrintSettings.offsetYmm}
                          onChange={(e) => updateNumericSetting('offsetYmm', e.target.value)}
                        />
                    </div>
                </div>
            </div>

            <div className="flex flex-wrap justify-between gap-2 mb-4">
                <Button variant="outline" size="sm" onClick={setAllSelected}>Seleccionar todos</Button>
                <Button variant="outline" size="sm" onClick={setFilteredSelected}>Seleccionar filtrados</Button>
                <Button variant="outline" size="sm" onClick={clearAllSelected}>Deseleccionar todos</Button>
            </div>
            <div className="space-y-2 mb-3">
              <Label htmlFor="imei-search">Buscar IMEI</Label>
              <Input
                id="imei-search"
                type="text"
                placeholder={bulkMode ? 'Buscar por modelo, SKU, IMEI o ubicación...' : 'Escribe parte del IMEI...'}
                value={imeiSearch}
                onChange={(e) => setImeiSearch(bulkMode ? e.target.value : e.target.value.replace(/\D/g, ''))}
              />
              <p className="text-xs text-muted-foreground">
                Mostrando {filteredOptions.length} de {labelOptions.length} IMEIs. Seleccionados: {selectedOptions.length}.
              </p>
            </div>
            {bulkMode && productsWithOptions.length > 0 && (
              <div className="max-h-[140px] overflow-y-auto rounded-md border bg-muted/20 p-2 space-y-2">
                {productsWithOptions.map(item => {
                  const selectedCount = item.keys.filter(key => selectedImeis.includes(key)).length
                  return (
                    <button
                      key={item.productId}
                      type="button"
                      className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-background"
                      onClick={() => toggleProductSelection(item.keys)}
                    >
                      <span className="min-w-0 truncate">{item.productName} <span className="text-muted-foreground">{item.sku}</span></span>
                      <span className="shrink-0 text-xs text-muted-foreground">{selectedCount}/{item.count}</span>
                    </button>
                  )
                })}
              </div>
            )}
            <div className="max-h-[300px] overflow-y-auto space-y-2">
                {filteredOptions.map(option => (
                    <div key={option.key} className="flex items-center space-x-2">
                        <Checkbox 
                            id={option.key} 
                            checked={selectedImeis.includes(option.key)}
                            onCheckedChange={(checked) => {
                                if (checked) setSelectedImeis([...selectedImeis, option.key])
                                else setSelectedImeis(selectedImeis.filter(i => i !== option.key))
                            }}
                        />
                        <label htmlFor={option.key} className="min-w-0 text-sm">
                          <span className="font-mono">{option.imei}</span>
                          {bulkMode && (
                            <span className="ml-2 text-xs text-muted-foreground">
                              {option.productName}{option.locationName ? ` · ${option.locationName}` : ''}
                            </span>
                          )}
                        </label>
                    </div>
                ))}
                {labelOptions.length === 0 && <p className="text-sm text-muted-foreground">No hay IMEIs disponibles para imprimir.</p>}
                {labelOptions.length > 0 && filteredOptions.length === 0 && (
                  <p className="text-sm text-muted-foreground">No hay resultados para esa búsqueda.</p>
                )}
            </div>
        </div>
        <div className="flex justify-end">
            <Button onClick={handlePrint} disabled={selectedOptions.length === 0}>
                <Printer className="mr-2 h-4 w-4" />
              Imprimir {selectedOptions.length} Etiquetas
            </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
