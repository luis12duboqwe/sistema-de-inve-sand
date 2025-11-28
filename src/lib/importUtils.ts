import type { ProductWithStock } from './types'

export interface CSVValidationResult {
  valid: boolean
  errors: string[]
  product?: Partial<ProductWithStock>
}

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
  products: Partial<ProductWithStock>[]
  errors: { row: number; error: string }[]
}

function parseCSVLine(line: string): string[] {
  const row: string[] = []
  let current = ''
  let insideQuotes = false

  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    
    if (char === '"') {
      if (insideQuotes && line[i + 1] === '"') {
        current += '"'
        i++
      } else {
        insideQuotes = !insideQuotes
      }
    } else if (char === ',' && !insideQuotes) {
      row.push(current.trim())
      current = ''
    } else {
      current += char
    }
  }
  
  row.push(current.trim())
  return row
}

function validateProductRow(
  row: Record<string, string>,
  rowNumber: number,
  profileId?: number
): CSVValidationResult {
  const errors: string[] = []
  
  if (!row.Nombre?.trim()) {
    errors.push('Nombre es requerido')
  }
  
  if (!row.Categoría || !['celular', 'accesorio'].includes(row.Categoría.toLowerCase())) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  const condicion = row.Condición?.toLowerCase()
  if (!condicion || !['nuevo', 'usado', 'reacondicionado'].includes(condicion)) {
    errors.push('Condición debe ser "nuevo", "usado" o "reacondicionado"')
  }
  
  const precio = parseFloat(row.Precio || '0')
  if (isNaN(precio) || precio < 0) {
    errors.push('Precio debe ser un número válido mayor o igual a 0')
  }
  
  const garantia = parseInt(row.Garantía || '0')
  if (isNaN(garantia) || garantia < 0) {
    errors.push('Garantía debe ser un número válido de meses')
  }
  
  const stock = parseInt(row.Stock || '0')
  if (isNaN(stock) || stock < 0) {
    errors.push('Stock debe ser un número válido mayor o igual a 0')
  }
  
  if (errors.length > 0) {
    return {
      valid: false,
      errors
    }
  }
  
  return {
    valid: true,
    errors: [],
    product: {
      sku: row.Código?.trim() || '',
      nombre: row.Nombre.trim(),
      categoria: row.Categoría.toLowerCase() as 'celular' | 'accesorio',
      marca: row.Marca?.trim() || '',
      modelo: row.Modelo?.trim() || '',
      capacidad: row.Capacidad?.trim() || '',
      condicion: condicion as 'nuevo' | 'usado' | 'reacondicionado',
      precio: precio,
      moneda: (row.Moneda?.toUpperCase() || 'HNL'),
      garantia_meses: garantia,
      stock_disponible: stock,
      profile_id: profileId,
      activo: true
    }
  }
}

export function parseProductsCSV(csvContent: string, profileId?: number): CSVImportResult {
  const lines = csvContent.split('\n').filter(line => line.trim())
  
  if (lines.length < 2) {
    return {
      success: false,
      message: 'El archivo CSV está vacío o no tiene datos',
      importedCount: 0,
      products: [],
      errors: []
    }
  }
  
  const products: Partial<ProductWithStock>[] = []
  const importErrors: { row: number; error: string }[] = []
  
  const headerLine = lines[0]
  const headers = parseCSVLine(headerLine)
  
  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i])
    const rowData: Record<string, string> = {}
    
    headers.forEach((header, index) => {
      rowData[header] = values[index] || ''
    })
    
    const validation = validateProductRow(rowData, i + 1, profileId)
    
    if (validation.valid && validation.product) {
      products.push(validation.product)
    } else {
      validation.errors.forEach(error => {
        importErrors.push({
          row: i + 1,
          error
        })
      })
    }
  }
  
  return {
    success: products.length > 0,
    message: products.length > 0
      ? `${products.length} productos listos para importar`
      : 'No se encontraron productos válidos',
    importedCount: products.length,
    products,
    errors: importErrors
  }
}

export function downloadCSVTemplate() {
  const csvContent = [
    'Código,Nombre,Categoría,Marca,Modelo,Capacidad,Condición,Precio,Moneda,Garantía,Stock',
    'ABC123,iPhone 13,celular,Apple,13,128GB,nuevo,15000,HNL,12,5'
  ].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'plantilla_productos.csv'
  link.click()
  URL.revokeObjectURL(url)
}
