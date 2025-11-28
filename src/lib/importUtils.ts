import type { ProductWithStock } from './types'

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
  errors: { row: number; message: string }[]
  products: Partial<ProductWithStock>[]
}

export interface CSVValidationError {
  row: number
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
  
  if (!row.Categoría || !['celular', 'accesorio'].includes(row.Categoría.toLowerCase())) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  if (!row.Marca || row.Marca.trim() === '') {
    errors.push('Marca es requerida')
  }
  
  if (!row.Condición || !['nuevo', 'usado', 'reacondicionado', 'grado a'].includes(row.Condición.toLowerCase())) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado A"')
  }
  
  const precio = parseFloat(row.Precio)
  if (isNaN(precio) || precio < 0) {
    errors.push('Precio debe ser un número válido mayor o igual a 0')
  }
  
  const stock = parseInt(row.Stock)
  if (isNaN(stock) || stock < 0) {
    errors.push('Stock debe ser un número entero mayor o igual a 0')
  }
  
  const garantia = parseInt(row['Garantía (meses)'] || row.Garantía || '0')
  if (isNaN(garantia) || garantia < 0) {
    errors.push('Garantía debe ser un número entero mayor o igual a 0')
  }
  
  if (errors.length > 0) {
    return { valid: false, errors }
  }
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'reacondicionado' | 'grado A'> = {
    'nuevo': 'nuevo',
    'usado': 'usado',
    'reacondicionado': 'reacondicionado',
    'grado a': 'grado A'
  }
  
  const product: Partial<ProductWithStock> = {
    profile_id: profileId,
    sku: row.SKU.trim(),
    nombre: row.Nombre.trim(),
    categoria: row.Categoría.toLowerCase() as 'celular' | 'accesorio',
    marca: row.Marca.trim(),
    modelo: (row.Modelo || '').trim(),
    capacidad: (row.Capacidad || '').trim(),
    condicion: condicionMap[row.Condición.toLowerCase()],
    precio: precio,
    moneda: (row.Moneda || 'HNL').trim(),
    garantia_meses: garantia,
    activo: true,
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
        message: 'El archivo CSV está vacío',
        importedCount: 0,
        errors: [],
        products: []
      }
    }
    
    const headers = rows[0].map(h => h.trim())
    const requiredHeaders = ['SKU', 'Nombre', 'Categoría', 'Marca', 'Condición', 'Precio', 'Stock']
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
    const errors: { row: number; message: string }[] = []
    
    for (let i = 1; i < rows.length; i++) {
      const rowData = rows[i]
      
      if (rowData.every(cell => cell.trim() === '')) {
        continue
      }
      
      const rowObject: Record<string, string> = {}
      headers.forEach((header, index) => {
        rowObject[header] = rowData[index] || ''
      })
      
      const validation = validateProductRow(rowObject, i + 1, profileId)
      
      if (validation.valid && validation.product) {
        products.push(validation.product)
      } else {
        errors.push({
          row: i + 1,
          message: validation.errors.join(', ')
        })
      }
    }
    
    if (products.length === 0) {
      return {
        success: false,
        message: 'No se pudieron importar productos. Verifica los errores.',
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
