import React from 'react'
import { Button } from '@/components/ui/button'
import { Printer } from '@phosphor-icons/react'

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
  const handlePrint = () => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return

    const html = `
      <html>
        <head>
          <title>Print Label</title>
          <link href="https://fonts.googleapis.com/css2?family=Libre+Barcode+128&display=swap" rel="stylesheet">
          <style>
            body { margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
            .label-container { 
              width: 50mm; 
              height: 25mm; 
              border: 1px solid #ccc; 
              display: flex; 
              flex-direction: column; 
              align-items: center; 
              justify-content: center; 
              font-family: sans-serif;
            }
            .product-name { font-size: 10px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; text-align: center; }
            .details { font-size: 8px; }
            .barcode { font-family: 'Libre Barcode 128', cursive; font-size: 32px; line-height: 1; margin: 2px 0; }
            .imei-text { font-size: 9px; font-family: monospace; }
            .sku { font-size: 7px; color: #666; }
            @media print {
              body { margin: 0; }
              .label-container { border: none; page-break-inside: avoid; }
            }
          </style>
        </head>
        <body>
          <div class="label-container">
            <div class="product-name">${product.nombre}</div>
            <div class="details">${product.color || ''} ${product.capacidad || ''}</div>
            <div class="barcode">${imei}</div>
            <div class="imei-text">${imei}</div>
            <div class="sku">${product.sku}</div>
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
    <Button variant="outline" size="sm" onClick={handlePrint} title="Imprimir Etiqueta">
      <Printer className="w-4 h-4 mr-2" />
      Etiqueta
    </Button>
  )
}
