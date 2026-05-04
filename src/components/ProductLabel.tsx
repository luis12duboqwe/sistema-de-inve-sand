import React from 'react'
import { Button } from '@/components/ui/button'
import { Printer } from '@phosphor-icons/react'
import { useKV } from '@/hooks/use-kv'
import { buildLabelsPrintHtml, DEFAULT_LABEL_PRINT_SETTINGS, LabelPrintSettings } from '@/lib/labelPrint'

interface ProductLabelProps {
  productName: string
  sku: string
  imei: string
  color?: string
  capacity?: string
}

export const ProductLabel: React.FC<ProductLabelProps> = ({ productName, sku, imei, color, capacity }) => {
  return (
    <div className="flex flex-col items-center justify-center p-2 border border-gray-300 w-[50mm] h-[25mm] bg-white text-black overflow-hidden box-border">
      <div className="text-[10px] font-bold truncate w-full text-center leading-tight">{productName}</div>
      <div className="text-[8px] mb-0 leading-tight">
        {color} {capacity}
      </div>
      <div className="font-['Libre_Barcode_128'] text-[32px] leading-none my-0 w-full text-center">
        {imei}
      </div>
      <div className="text-[9px] font-mono leading-none">{imei}</div>
      <div className="text-[7px] text-gray-500 leading-none mt-[1px]">{sku}</div>
    </div>
  )
}

export const PrintButton: React.FC<{ 
  product: { nombre: string; sku: string; color?: string; capacidad?: string }; 
  imei: string 
}> = ({ product, imei }) => {
  const [labelPrintSettings] = useKV<LabelPrintSettings>('settings_label_print', DEFAULT_LABEL_PRINT_SETTINGS)

  const handlePrint = () => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return

    const html = buildLabelsPrintHtml(
      `Etiqueta - ${product.nombre}`,
      [{
        productName: product.nombre,
        sku: product.sku,
        imei,
        color: product.color,
        capacity: product.capacidad,
      }],
      {
        ...labelPrintSettings,
        labelsPerPage: 1,
      },
    )

    printWindow.document.write(html)
    printWindow.document.close()
  }

  return (
    <Button variant="outline" size="sm" onClick={handlePrint} title="Imprimir Etiqueta">
      <Printer className="w-4 h-4 mr-2" />
      Etiqueta
    </Button>
  )
}
