import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { ProductWithStock } from '@/lib/types'
import { Printer } from '@phosphor-icons/react'
import { useKV } from '@/hooks/use-kv'
import { buildLabelsPrintHtml, DEFAULT_LABEL_PRINT_SETTINGS, LABEL_SIZE_PRESETS, LabelPresetId, LabelPrintSettings } from '@/lib/labelPrint'

interface PrintLabelsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock
}

export function PrintLabelsDialog({ open, onOpenChange, product }: PrintLabelsDialogProps) {
  const [imeis, setImeis] = useState<string[]>([])
  const [selectedImeis, setSelectedImeis] = useState<string[]>([])
  const [imeiSearch, setImeiSearch] = useState('')
  const [labelPrintSettings, setLabelPrintSettings] = useKV<LabelPrintSettings>('settings_label_print', DEFAULT_LABEL_PRINT_SETTINGS)

  const filteredImeis = imeis.filter(imei => imei.includes(imeiSearch.trim()))

  useEffect(() => {
    if (open && product.is_serialized) {
      const fetchAll = async () => {
        const allImeis: string[] = []
        if (product.stock_items) {
            for (const stock of product.stock_items) {
                if (stock.cantidad_disponible > 0) {
                    try {
                      const locImeis = await inventoryServiceInstance.getAvailableIMEIs(product.id, stock.location_id)
                      allImeis.push(...locImeis)
                    } catch (error) {
                      console.warn('Error obteniendo IMEIs para impresión', error)
                    }
                }
            }
        }
        // Deduplicate
        const unique = Array.from(new Set(allImeis))
        setImeis(unique)
        setSelectedImeis(unique) // Select all by default
        setImeiSearch('')
      }
      fetchAll()
    }
  }, [open, product])

  const handlePrint = () => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return

    const html = buildLabelsPrintHtml(
      `Etiquetas - ${product.nombre}`,
      selectedImeis.map(imei => ({
        productName: product.nombre,
        sku: product.sku,
        imei,
        color: product.color,
        capacity: product.capacidad,
      })),
      labelPrintSettings,
    )

    printWindow.document.write(html)
    printWindow.document.close()
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
          <DialogTitle>Imprimir Etiquetas: {product.nombre}</DialogTitle>
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

            <div className="flex justify-between mb-4">
                <Button variant="outline" size="sm" onClick={() => setSelectedImeis(imeis)}>Seleccionar Todos</Button>
                <Button variant="outline" size="sm" onClick={() => setSelectedImeis([])}>Deseleccionar Todos</Button>
            </div>
            <div className="space-y-2 mb-3">
              <Label htmlFor="imei-search">Buscar IMEI</Label>
              <Input
                id="imei-search"
                type="text"
                placeholder="Escribe parte del IMEI..."
                value={imeiSearch}
                onChange={(e) => setImeiSearch(e.target.value.replace(/\D/g, ''))}
              />
              <p className="text-xs text-muted-foreground">
                Mostrando {filteredImeis.length} de {imeis.length} IMEIs.
              </p>
            </div>
            <div className="max-h-[300px] overflow-y-auto space-y-2">
                {filteredImeis.map(imei => (
                    <div key={imei} className="flex items-center space-x-2">
                        <Checkbox 
                            id={imei} 
                            checked={selectedImeis.includes(imei)}
                            onCheckedChange={(checked) => {
                                if (checked) setSelectedImeis([...selectedImeis, imei])
                                else setSelectedImeis(selectedImeis.filter(i => i !== imei))
                            }}
                        />
                        <label htmlFor={imei} className="text-sm font-mono">{imei}</label>
                    </div>
                ))}
                {imeis.length === 0 && <p className="text-sm text-muted-foreground">No hay IMEIs disponibles para imprimir.</p>}
                {imeis.length > 0 && filteredImeis.length === 0 && (
                  <p className="text-sm text-muted-foreground">No hay resultados para esa búsqueda.</p>
                )}
            </div>
        </div>
        <div className="flex justify-end">
            <Button onClick={handlePrint} disabled={selectedImeis.length === 0}>
                <Printer className="mr-2 h-4 w-4" />
                Imprimir {selectedImeis.length} Etiquetas
            </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
