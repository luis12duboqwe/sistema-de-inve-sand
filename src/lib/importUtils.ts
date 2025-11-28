import type { ProductWithStock } from './types'

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
        row.push(current.trim())
        current = ''
      } else {
        current += char
      }
    }
    
    row.push(current.trim())
    rows.push(row)
  }
  
  return rows
}

interface ValidationResult {
  valid: boolean
  error?: string
  product?: Partial<ProductWithStock>
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
  
  const garantiaMeses = parseInt(row['Garantía (meses)'] || '0')
  if (isNaN(garantiaMeses) || garantiaMeses < 0) {
    errors.push('Garantía debe ser un número válido')
  }
  
  const categoria = row['Categoría']?.toLowerCase()
  if (!categoria || !['celular', 'accesorio'].includes(categoria)) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'reacondicionado' | 'grado A'> = {
    'nuevo': 'nuevo',
    'usado': 'usado',
    'reacondicionado': 'reacondicionado',
    'grado a': 'grado A'
  }
  
  const condicion = condicionMap[row['Condición']?.toLowerCase()]
  if (!condicion) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado A"')
  }
  
  const precio = parseFloat(row.Precio || '0')
  if (isNaN(precio) || precio <= 0) {
    errors.push('Precio debe ser un número válido mayor a 0')
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
    profile_id: profileId,
    activo: true
  }
  
  return {
    valid: true,
    product
  }
}

export function importProductsFromCSV(
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
    
    const headers = rows[0].map(h => h.replace(/^"|"$/g, '').trim())
    const requiredHeaders = ['SKU', 'Nombre', 'Categoría', 'Precio']
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
        rowData[header] = row[index]?.replace(/^"|"$/g, '').trim() || ''
      })
      
      const validation = validateProductRow(rowData, i + 1, profileId)
      
      if (validation.valid && validation.product) {
        products.push(validation.product)
      } else if (validation.error) {
        importErrors.push({
          row: i + 1,
          error: validation.error
        })
      }
    }
    
    if (products.length === 0 && importErrors.length > 0) {
      return {
        success: false,
        message: 'No se pudo importar ningún producto debido a errores de validación',
        importedCount: 0,
        errors: importErrors,
        products: []
      }
    }
    
    return {
      success: true,
      message: `${products.length} productos listos para importar`,
      importedCount: products.length,
      errors: importErrors,
      products
    }
  } catch (error) {
    return {
      success: false,
      message: `Error al procesar el archivo CSV: ${error instanceof Error ? error.message : 'Error desconocido'}`,
      importedCount: 0,
      errors: [],
      products: []
    }
  }
}

export function generateCSVTemplate(): string {
  const headers = ['SKU', 'Nombre', 'Categoría', 'Marca', 'Modelo', 'Capacidad', 'Condición', 'Precio', 'Moneda', 'Garantía (meses)', 'Stock']
  const exampleRows = [
    ['SAM-S23-256-U', 'Samsung Galaxy S23', 'celular', 'Samsung', 'Galaxy S23', '256GB', 'usado', '15000', 'HNL', '6', '3'],
    ['IPH-14-128-N', 'iPhone 14', 'celular', 'Apple', 'iPhone 14', '128GB', 'nuevo', '22000', 'HNL', '12', '5'],
    ['CASE-IPH-14', 'Funda iPhone 14', 'accesorio', 'Generic', 'Funda Protectora', '', 'nuevo', '250', 'HNL', '3', '20']
  ]
  
  const csvRows = [headers, ...exampleRows]
  return csvRows.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
}

export function downloadCSVTemplate() {
  const csvContent = generateCSVTemplate()
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', 'plantilla_productos.csv')
  
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
}
