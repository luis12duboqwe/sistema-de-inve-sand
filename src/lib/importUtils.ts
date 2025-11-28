import type { ProductWithStock } from './types'

interface ValidationResult {
  valid: boolean
  error?: string
  product?: Partial<ProductWithStock>
}

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
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
  }
  
  if (!row.Nombre || !row.Nombre.trim()) {
    errors.push('Nombre es requerido')
  }
  
  const categoria = row.Categoría?.toLowerCase().trim()
  if (!categoria || (categoria !== 'celular' && categoria !== 'accesorio')) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'reacondicionado' | 'grado A'> = {
    'nuevo': 'nuevo',
    'usado': 'usado',
    'reacondicionado': 'reacondicionado',
    'grado a': 'grado A'
  }
  
  const condicion = condicionMap[row.Condición?.toLowerCase().trim() || 'nuevo']
  if (!condicion) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado A"')
  }
  
  const precio = parseFloat(row.Precio || '0')
  if (isNaN(precio) || precio < 0) {
    errors.push('Precio debe ser un número válido')
  }
  
  const garantiaMeses = parseInt(row['Garantía (meses)'] || '0')
  if (isNaN(garantiaMeses) || garantiaMeses < 0) {
    errors.push('Garantía debe ser un número válido')
  }
  
  const stock = parseInt(row.Stock || '0')
  if (isNaN(stock) || stock < 0) {
    errors.push('Stock debe ser un número válido')
  }
  
  if (errors.length > 0) {
    return {
      valid: false,
      error: errors.join(', ')
    }
  }
  
  const product: Partial<ProductWithStock> = {
    profile_id: profileId,
    sku: row.SKU.trim(),
    nombre: row.Nombre.trim(),
    categoria: categoria as 'celular' | 'accesorio',
    marca: row.Marca?.trim() || '',
    modelo: row.Modelo?.trim() || '',
    capacidad: row.Capacidad?.trim() || '',
    condicion: condicion,
    precio: precio,
    moneda: (row.Moneda?.trim() || 'HNL') as 'HNL' | 'USD',
    garantia_meses: garantiaMeses,
    stock_disponible: stock,
    activo: true
  }
  
  return {
    valid: true,
    product
  }
}

export function parseProductsCSV(
  csvText: string,
  profileId: number
): CSVImportResult {
  try {
    const rows = parseCSV(csvText)
    if (rows.length === 0) {
      return {
        success: false,
        message: 'El archivo CSV está vacío',
        importedCount: 0,
        errors: [],
        products: []
      }
    }
    
    const headers = rows[0].map(h => h.trim())
    const requiredHeaders = ['SKU', 'Nombre', 'Categoría', 'Precio', 'Stock']
    const missingHeaders = requiredHeaders.filter(h => !headers.includes(h))
    
    if (missingHeaders.length > 0) {
      return {
        success: false,
        message: `Faltan las siguientes columnas: ${missingHeaders.join(', ')}`,
        importedCount: 0,
        errors: [],
        products: []
      }
    }
    
    const products: Partial<ProductWithStock>[] = []
    const importErrors: { row: number; error: string }[] = []
    
    for (let i = 1; i < rows.length; i++) {
      const row = rows[i]
      if (row.length === 0 || row.every(cell => !cell.trim())) continue
      
      const rowData: Record<string, string> = {}
      headers.forEach((header, index) => {
        rowData[header] = row[index]?.trim() || ''
      })
      
      const validation = validateProductRow(rowData, i + 1, profileId)
      
      if (validation.valid && validation.product) {
        products.push(validation.product)
      } else {
        importErrors.push({
          row: i + 1,
          error: validation.error || 'Error desconocido'
        })
      }
    }
    
    if (products.length === 0) {
      return {
        success: false,
        message: 'No se pudieron importar productos válidos',
        importedCount: 0,
        errors: importErrors,
        products: []
      }
    }
    
    return {
      success: true,
      message: `${products.length} productos importados correctamente`,
      importedCount: products.length,
      errors: importErrors,
      products
    }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Error al procesar el archivo CSV',
      importedCount: 0,
      errors: [],
      products: []
    }
  }
}

export function generateCSVTemplate(): string {
  const headers = ['SKU', 'Nombre', 'Categoría', 'Marca', 'Modelo', 'Capacidad', 'Condición', 'Precio', 'Moneda', 'Garantía (meses)', 'Stock']
  const exampleRows = [
    ['IPHONE13-128-BLK', 'iPhone 13', 'celular', 'Apple', 'iPhone 13', '128GB', 'nuevo', '15000', 'HNL', '12', '5'],
    ['CASE-IPHONE13', 'Funda iPhone 13', 'accesorio', 'Generic', 'Silicona', '', 'nuevo', '150', 'HNL', '3', '20']
  ]
  
  const csvRows = [headers.join(',')]
  for (const row of exampleRows) {
    csvRows.push(row.map(cell => `"${cell}"`).join(','))
  }
  
  return csvRows.join('\n')
}

export function downloadCSVTemplate() {
  const csvContent = generateCSVTemplate()
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', 'plantilla_productos.csv')
  link.style.visibility = 'hidden'
  
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
