import type { ProductWithStock } from './types'

  product?: Partial<ProductWithStock>
}
  product?: Partial<ProductWithStock>
  error?: string
}

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
}

  for (const line of lines) {
    
    let current = ''
  
      const char = line[i]
      if (char === '"') {
    
    const row: string[] = []
    let current = ''
    let inQuotes = false
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i]
      
      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"'
          i++
        } else {
          inQuotes = !inQuotes
        }
      } else if (char === ',' && !inQuotes) {
        row.push(current)
        current = ''
      } else {
        current += char
      }
    }
    
    row.push(current)
    rows.push(row)
  }
  
    errors.pu
 

function validateProductRow(
  row: Record<string, string>,
  rowNumber: number,
  profileId: number
): CSVValidationResult {
  const errors: string[] = []
  
  if (!row.SKU?.trim()) {
    errors.push('SKU es requerido')
  c
  
  if (!row.Nombre?.trim()) {
    errors.push('Nombre es requerido')
  i
  
  const categoria = row.Categoría?.toLowerCase().trim()
  if (!categoria || !['celular', 'accesorio'].includes(categoria)) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  i
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'grado A' | 'grado B'> = {
    categoria: catego
    'usado': 'usado',
    'grado a': 'grado A',
    'grado b': 'grado B'
   
  
  const condicionInput = row.Condición?.toLowerCase().trim() || 'nuevo'
  const condicion = condicionMap[condicionInput] || 'nuevo'
ex
  const precio = parseFloat(row.Precio || '0')
  try {
    if (rows.length === 0) {
  }
  
  const garantiaMeses = parseInt(row['Garantía (meses)'] || '0')
  if (isNaN(garantiaMeses) || garantiaMeses < 0) {
    errors.push('Garantía debe ser un número válido')
  }
  
        success: false,
        importedCount: 0,
        products: []
   
  
    
    return {
      
      headers.forEach((header,
    }
   
  
      } else {
          row: i + 1,
        })
    }
    if (products.length === 0) {
        success: false,
        importedCount: 0,
        products: []
    }
    return {
      message: `${products.length} productos importados exi
      errors: importErrors,
    }
    return {
   
  
    }
}
export func
  c
 

    headers.join(','),
  ].join('\n')
  const blob = new 
  
  link.
  link.style.display = 'none'
  
  
  URL.revokeObjectURL(u




























      const rowData: Record<string, string> = {}



      

      







      }

    
    if (products.length === 0) {
      return {

        message: 'No se pudo importar ningún producto válido',
        importedCount: 0,
        errors: importErrors,
        products: []
      }



      success: true,
      message: `${products.length} productos importados exitosamente`,
      importedCount: products.length,
      errors: importErrors,
      products

  } catch (error) {

      success: false,
      message: 'Error al procesar el archivo CSV',
      importedCount: 0,

      products: []

  }


export function generateCSVTemplate(): void {
  const headers = ['SKU', 'Nombre', 'Categoría', 'Marca', 'Modelo', 'Capacidad', 'Condición', 'Precio', 'Moneda', 'Garantía (meses)', 'Stock']

    ['IPHONE13-128', 'iPhone 13', 'celular', 'Apple', 'iPhone 13', '128GB', 'nuevo', '15000', 'HNL', '12', '5'],
    ['CASE-SILICONE', 'Funda de Silicona', 'accesorio', 'Generic', 'Universal', '', 'nuevo', '150', 'HNL', '3', '20']


  const csvContent = [
    headers.join(','),
    ...exampleRows.map(row => row.join(','))
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })


  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', 'plantilla_productos.csv')
  link.style.display = 'none'
  document.body.appendChild(link)


  
  document.body.removeChild(link)


