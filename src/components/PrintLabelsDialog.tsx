import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { ProductWithStock } from '@/lib/types'
import { Printer } from '@phosphor-icons/react'

interface PrintLabelsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock
}

export function PrintLabelsDialog({ open, onOpenChange, product }: PrintLabelsDialogProps) {
  const [imeis, setImeis] = useState<string[]>([])
  const [selectedImeis, setSelectedImeis] = useState<string[]>([])

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
      }
      fetchAll()
    }
  }, [open, product])

  const handlePrint = () => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return

    const html = `
      <html>
        <head>
          <title>Print Labels - ${product.nombre}</title>
          <link href="https://fonts.googleapis.com/css2?family=Libre+Barcode+128&display=swap" rel="stylesheet">
          <style>
            body { margin: 0; padding: 20px; font-family: sans-serif; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, 50mm); gap: 10px; }
            .label-container { 
              width: 50mm; 
              height: 25mm; 
              border: 1px solid #ccc; 
              display: flex; 
              flex-direction: column; 
              align-items: center; 
              justify-content: center; 
              box-sizing: border-box;
              page-break-inside: avoid;
            }
            .product-name { font-size: 10px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; text-align: center; }
            .details { font-size: 8px; }
            .barcode { font-family: 'Libre Barcode 128', cursive; font-size: 32px; line-height: 1; margin: 2px 0; }
            .imei-text { font-size: 9px; font-family: monospace; }
            .sku { font-size: 7px; color: #666; }
            @media print {
              body { margin: 0; padding: 0; }
              .grid { display: block; }
              .label-container { float: left; margin: 2px; border: none; }
            }
          </style>
        </head>
        <body>
          <div class="grid">
            ${selectedImeis.map(imei => `
              <div class="label-container">
                <div class="product-name">${product.nombre}</div>
                <div class="details">${product.color || ''} ${product.capacidad || ''}</div>
                <div class="barcode">${imei}</div>
                <div class="imei-text">${imei}</div>
                <div class="sku">${product.sku}</div>
              </div>
            `).join('')}
          </div>
          <script>
            window.onload = () => { window.print(); window.close(); }
          </script>
        </body>
      </html>
    `
    printWindow.document.write(html)
    printWindow.document.close()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Imprimir Etiquetas: {product.nombre}</DialogTitle>
        </DialogHeader>
        <div className="py-4">
            <div className="flex justify-between mb-4">
                <Button variant="outline" size="sm" onClick={() => setSelectedImeis(imeis)}>Seleccionar Todos</Button>
                <Button variant="outline" size="sm" onClick={() => setSelectedImeis([])}>Deseleccionar Todos</Button>
            </div>
            <div className="max-h-[300px] overflow-y-auto space-y-2">
                {imeis.map(imei => (
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
