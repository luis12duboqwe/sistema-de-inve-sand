import type { ProductWithStock } from './types'

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
}

export interface CSVValidationError {
  field: string
  message: string
}

export function parseCSV(csvText: string): string[][] {
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

export function validateProductRow(
  row: Record<string, string>,
  rowNumber: number,
  profileId: number
): { valid: boolean; errors: string[]; product?: Partial<ProductWithStock> } {
  const errors: string[] = []
  
  if (!row.SKU || row.SKU.trim() === '') {
    errors.push('SKU es requerido')
  }
  
  if (!row.Nombre || row.Nombre.trim() === '') {
    errors.push('Nombre es requerido')
  }
  
  const precio = parseFloat(row.Precio)
  if (isNaN(precio) || precio <= 0) {
    errors.push('Precio debe ser un número mayor a 0')
  }
  
  const stock = parseInt(row.Stock)
  if (isNaN(stock) || stock < 0) {
    errors.push('Stock debe ser un número mayor o igual a 0')
  }
  
  const garantia = parseInt(row['Garantía (meses)'])
  if (isNaN(garantia) || garantia < 0) {
    errors.push('Garantía debe ser un número mayor o igual a 0')
  }
  
  const categoria = row['Categoría']?.toLowerCase()
  if (!categoria || !['celular', 'accesorio'].includes(categoria)) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'reacondicionado' | 'grado A'> = {
    'nuevo': 'nuevo',
    'usado': 'usado',
    'reacondicionado': 'reacondicionado',
    'grado a': 'grado A',
    'grado A': 'grado A'
  }
  
  const condicion = condicionMap[row['Condición']?.toLowerCase()]
  if (!condicion) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado A"')
  }
  
  if (errors.length > 0) {
    return { valid: false, errors }
  }
  
  const product: Partial<ProductWithStock> = {
    profile_id: profileId,
    nombre: row.Nombre.trim(),
    marca: row.Marca.trim(),
    modelo: row.Modelo.trim(),
    categoria: categoria as 'celular' | 'accesorio',
    capacidad: row.Capacidad.trim(),
    sku: row.SKU.trim(),
    condicion: condicion,
    precio: precio,
    moneda: (row.Moneda || 'HNL') as 'HNL' | 'USD',
    garantia_meses: garantia,
    stock_disponible: stock
  }
  
  return { valid: true, errors: [], product }
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
        message: 'El archivo está vacío',
        importedCount: 0,
        errors: [],
        products: []
      }
    }
    
    const headers = rows[0]
    const requiredHeaders = ['SKU', 'Nombre', 'Categoría', 'Marca', 'Modelo', 'Capacidad', 'Condición', 'Precio', 'Moneda', 'Garantía (meses)', 'Stock']
    
    const missingHeaders = requiredHeaders.filter(h => !headers.includes(h))
    if (missingHeaders.length > 0) {
      return {
        success: false,
        message: `Columnas faltantes: ${missingHeaders.join(', ')}`,
        importedCount: 0,
        errors: [],
        products: []
      }
    }
    
    const products: Partial<ProductWithStock>[] = []
    const errors: { row: number; error: string }[] = []
    
    for (let i = 1; i < rows.length; i++) {
      const row = rows[i]
      if (row.length === 0 || row.every(cell => cell.trim() === '')) {
        continue
      }
      
      const rowData: Record<string, string> = {}
      headers.forEach((header, index) => {
        rowData[header] = row[index] || ''
      })
      
      const validation = validateProductRow(rowData, i + 1, profileId)
      
      if (validation.valid && validation.product) {
        products.push(validation.product)
      } else {
        validation.errors.forEach(error => {
          errors.push({
            row: i + 1,
            error: error
          })
        })
      }
    }
    
    if (products.length === 0) {
      return {
        success: false,
        message: 'No se encontraron productos válidos para importar',
        importedCount: 0,
        errors,
        products: []
      }
    }
    
    return {
      success: true,
      message: `${products.length} productos listos para importar`,
      importedCount: products.length,
      errors,
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
    ['IPH14-128-NEW', 'iPhone 14', 'celular', 'Apple', 'iPhone 14', '128GB', 'nuevo', '18500', 'HNL', '12', '5'],
    ['SAM-S23-256-USED', 'Samsung Galaxy S23', 'celular', 'Samsung', 'Galaxy S23', '256GB', 'usado', '12000', 'HNL', '6', '3'],
    ['CASE-IPH14-BLK', 'Funda iPhone 14', 'accesorio', 'Generic', 'Funda Silicona', 'N/A', 'nuevo', '150', 'HNL', '0', '20']
  ]
  
  const rows = [headers, ...exampleRows]
  return rows.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
}

export function downloadCSVTemplate() {
  const csvContent = generateCSVTemplate()
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  
  link.setAttribute('href', url)
  link.setAttribute('download', 'plantilla_importacion_productos.csv')
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
