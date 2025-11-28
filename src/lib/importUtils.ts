import type { ProductWithStock } from './types'

export interface CSVValidationResult {
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
  const lines = csvText.split('\n').filter(line => line.trim())
  const rows: string[][] = []
  
  for (const line of lines) {
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
): CSVValidationResult {
  const errors: string[] = []
  
  if (!row.SKU?.trim()) {
    errors.push('SKU es requerido')
  }
  
  if (!row.Nombre?.trim()) {
    errors.push('Nombre es requerido')
  }
  
  const categoria = row.Categoría?.toLowerCase().trim()
  if (!categoria || !['celular', 'accesorio'].includes(categoria)) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'grado A' | 'reacondicionado'> = {
    'nuevo': 'nuevo',
    'usado': 'usado',
    'grado a': 'grado A',
    'grado b': 'grado A',
    'reacondicionado': 'reacondicionado'
  }
  
  const condicion = condicionMap[row.Condición?.toLowerCase().trim() || '']
  if (!condicion) {
    errors.push('Condición debe ser "nuevo", "usado", "grado A", o "reacondicionado"')
  }
  
  const precio = parseFloat(row.Precio || '0')
  if (isNaN(precio) || precio <= 0) {
    errors.push('Precio debe ser un número válido mayor a 0')
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
  
  return {
    valid: true,
    product: {
      profile_id: profileId,
      sku: row.SKU.trim(),
      nombre: row.Nombre.trim(),
      categoria: categoria as 'celular' | 'accesorio',
      marca: row.Marca?.trim() || '',
      modelo: row.Modelo?.trim() || '',
      capacidad: row.Capacidad?.trim() || '',
      condicion: condicion,
      precio: precio,
      moneda: row.Moneda?.trim() || 'HNL',
      garantia_meses: garantiaMeses,
      stock_disponible: stock,
      activo: true
    }
  }
}

export function parseCSVFile(csvText: string, profileId: number): CSVImportResult {
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
    
    const headers = rows[0]
    const products: Partial<ProductWithStock>[] = []
    const importErrors: { row: number; error: string }[] = []
    
    for (let i = 1; i < rows.length; i++) {
      const rowData: Record<string, string> = {}
      
      headers.forEach((header, index) => {
        rowData[header] = rows[i][index] || ''
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
    
    return {
      success: products.length > 0,
      message: products.length > 0 
        ? `${products.length} productos listos para importar` 
        : 'No se encontraron productos válidos',
      importedCount: products.length,
      errors: importErrors,
      products: products
    }
  } catch (error) {
    return {
      success: false,
      message: `Error al procesar CSV: ${error instanceof Error ? error.message : 'Error desconocido'}`,
      importedCount: 0,
      errors: [],
      products: []
    }
  }
}

export function generateCSVTemplate(): void {
  const headers = ['SKU', 'Nombre', 'Categoría', 'Marca', 'Modelo', 'Capacidad', 'Condición', 'Precio', 'Moneda', 'Garantía (meses)', 'Stock']
  
  const exampleRows = [
    ['IP13-128-BLK', 'iPhone 13', 'celular', 'Apple', 'iPhone 13', '128GB', 'nuevo', '15000', 'HNL', '12', '5'],
    ['CASE-IP13-SIL', 'Funda iPhone 13', 'accesorio', 'Generic', 'Silicona', '', 'nuevo', '150', 'HNL', '0', '20']
  ]
  
  const csvContent = [headers, ...exampleRows]
    .map(row => row.map(cell => `"${cell}"`).join(','))
    .join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', 'plantilla_productos.csv')
  link.click()
  URL.revokeObjectURL(url)
}






export const parseProductsCSV = parseCSVFile
export const downloadCSVTemplate = generateCSVTemplate
