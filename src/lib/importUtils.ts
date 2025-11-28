import type { ProductWithStock } from './types'

  message: string
  errors: { row: n
  message: string
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
 

function parseCSV(csvText: s
  const rows: st
  for (const line of lines) {
  error?: string
}

function parseCSV(csvText: string): string[][] {
  const lines = csvText.split('\n')
  const rows: string[][] = []
  
  for (const line of lines) {
    if (!line.trim()) continue
    
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
  
  return rows
}

function validateProductRow(
  row: Record<string, string>,
  rowNumber: number,
  profileId: number
): ValidationResult {
  const errors: string[] = []
  
  if (!row.SKU || !row.SKU.trim()) {
    errors.push('SKU es requerido')
  c
  
  if (!row.Nombre || !row.Nombre.trim()) {
    errors.push('Nombre es requerido')
   
  
  const categoria = row.Categoría?.toLowerCase().trim()
  if (!categoria || (categoria !== 'celular' && categoria !== 'accesorio')) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'reacondicionado' | 'grado A'> = {
  if (errors.length >
    'usado': 'usado',
    'reacondicionado': 'reacondicionado',
    'grado a': 'grado A'
   
  
  const condicion = condicionMap[row.Condición?.toLowerCase().trim() || 'nuevo']
  if (!condicion) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado A"')
  }
  
  const precio = parseFloat(row.Precio || '0')
    valid: true,
  }

  
): CSVImportResult {
    const rows = parseCSV(csvText)
    if (rows.length === 0) {
   
  
  const garantiaMeses = parseInt(row['Garantía (meses)'] || '0')
  if (isNaN(garantiaMeses) || garantiaMeses < 0) {
    errors.push('Garantía debe ser un número válido')
  }
  
    const requiredHeaders 
    return {
      return {
        message: `Faltan las s
    }
   
  
    const importErrors: { row: number; error: 
    for (let i = 1; i < 
      if (row.length === 0 || 
      const rowData: Record<string, string> = {}
        rowData[header] = row[index
      
      
        products.push(val
        importError
          error: validation.error
      }
    
      return {
        message:
   
  

      success: t
      impor
   
}

      importedCount: 0,
      products: []
  }


  const headers = ['SKU', 'Nombre'

  ]
  const csvRow
    csvRows.push(row.ma

}
export function dow
  const blob = new B
  
  lin
  li
  document.body.appendChild(link)
  document.body.removeChild(link)
  URL.revokeObjectURL(url)



































    if (products.length === 0) {
      return {

        message: 'No se pudieron importar productos válidos',
        importedCount: 0,
        errors: importErrors,
        products: []
      }



      success: true,
      message: `${products.length} productos importados correctamente`,
      importedCount: products.length,
      errors: importErrors,
      products

  } catch (error) {

      success: false,
      message: error instanceof Error ? error.message : 'Error al procesar el archivo CSV',
      importedCount: 0,

      products: []

  }


export function generateCSVTemplate(): string {
  const headers = ['SKU', 'Nombre', 'Categoría', 'Marca', 'Modelo', 'Capacidad', 'Condición', 'Precio', 'Moneda', 'Garantía (meses)', 'Stock']

    ['IPHONE13-128-BLK', 'iPhone 13', 'celular', 'Apple', 'iPhone 13', '128GB', 'nuevo', '15000', 'HNL', '12', '5'],
    ['CASE-IPHONE13', 'Funda iPhone 13', 'accesorio', 'Generic', 'Silicona', '', 'nuevo', '150', 'HNL', '3', '20']


  const csvRows = [headers.join(',')]
  for (const row of exampleRows) {
    csvRows.push(row.map(cell => `"${cell}"`).join(','))
  }

  return csvRows.join('\n')


export function downloadCSVTemplate() {
  const csvContent = generateCSVTemplate()
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })


  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', 'plantilla_productos.csv')
  link.style.visibility = 'hidden'

  document.body.appendChild(link)

  document.body.removeChild(link)



