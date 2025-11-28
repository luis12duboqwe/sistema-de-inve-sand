import type { ProductWithStock } from './types'

export interface CSVValidationResult {
  valid: boolean
  product?: Partial<ProductWithStock>
  errors: string[]
}

export interface ImportResult {
  success: boolean
  message: string
  products: Partial<ProductWithStock>[]
  errors: { row: number; error: string }[]
  importedCount: number
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
  profileId?: string
): CSVValidationResult {
  const errors: string[] = []
  
  const nombre = row.Nombre?.trim() || row.nombre?.trim()
  if (!nombre) {
    errors.push('El nombre del producto es requerido')
  }
  
  const categoria = row.Categoría?.trim().toLowerCase() || row.categoria?.trim().toLowerCase() || row.Category?.trim().toLowerCase()
  if (!categoria || !['celular', 'accesorio'].includes(categoria)) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  const condicion = row.Condición?.trim().toLowerCase() || row.condicion?.trim().toLowerCase() || row.Condition?.trim().toLowerCase()
  if (!condicion || !['nuevo', 'usado', 'reacondicionado', 'grado a'].includes(condicion)) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado a"')
  }
  
  const precio = parseFloat(row.Precio || row.precio || row.Price || '0')
  if (isNaN(precio) || precio < 0) {
    errors.push('El precio debe ser un número válido mayor o igual a 0')
  }
  
  const stock = parseInt(row.Stock || row.stock || '0')
  if (isNaN(stock) || stock < 0) {
    errors.push('El stock debe ser un número entero mayor o igual a 0')
  }
  
  const garantia = parseInt(row['Garantía (meses)'] || row.Garantía || row.garantia || '0')
  
  if (errors.length > 0) {
    return { valid: false, errors }
  }
  
  return {
    valid: true,
    errors: [],
    product: {
      sku: row.SKU?.trim() || row.sku?.trim() || row.Código?.trim() || '',
      nombre: nombre,
      categoria: categoria as 'celular' | 'accesorio',
      marca: row.Marca?.trim() || row.marca?.trim() || row.Brand?.trim() || '',
      modelo: row.Modelo?.trim() || row.modelo?.trim() || row.Model?.trim() || '',
      capacidad: row.Capacidad?.trim() || row.capacidad?.trim() || row.Capacity?.trim() || '',
      condicion: condicion as 'nuevo' | 'usado' | 'reacondicionado' | 'grado A',
      precio: precio,
      moneda: row.Moneda?.trim() || row.moneda?.trim() || row.Currency?.trim() || 'HNL',
      garantia_meses: garantia,
      stock_disponible: stock,
      activo: true,
      profile_id: profileId ? parseInt(profileId) : 0
    }
  }
}

export function parseCSV(
  csvContent: string,
  profileId?: string
): ImportResult {
  const lines = csvContent.split('\n').filter(line => line.trim())
  
  if (lines.length < 2) {
    return {
      success: false,
      message: 'El archivo CSV debe contener al menos una fila de encabezados y una fila de datos',
      products: [],
      errors: [],
      importedCount: 0
    }
  }

  const importErrors: { row: number; error: string }[] = []
  const products: Partial<ProductWithStock>[] = []

  const headerLine = lines[0]
  const headers = parseCSVLine(headerLine).map(h => h.replace(/^"|"$/g, ''))
  
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    if (!line.trim()) continue

    const values = parseCSVLine(line).map(v => v.replace(/^"|"$/g, ''))
    const row: Record<string, string> = {}
    
    headers.forEach((header, index) => {
      row[header] = values[index] || ''
    })
    
    const validation = validateProductRow(row, i + 1, profileId)
    
    if (validation.valid && validation.product) {
      products.push(validation.product)
    } else {
      importErrors.push({
        row: i + 1,
        error: validation.errors.join(', ')
      })
    }
  }

  return {
    success: products.length > 0,
    message: products.length > 0
      ? `${products.length} productos importados exitosamente`
      : 'No se pudo importar ningún producto',
    products,
    errors: importErrors,
    importedCount: products.length
  }
}

export function parseProductsCSV(csvContent: string, profileId: number) {
  return parseCSV(csvContent, profileId.toString())
}

export function downloadCSVTemplate() {
  const csvContent = [
    'SKU,Nombre,Categoría,Marca,Modelo,Capacidad,Condición,Precio,Moneda,Garantía (meses),Stock',
    'ABC123,iPhone 13,celular,Apple,13,128GB,nuevo,15000,HNL,12,5'
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  
  link.href = url
  link.download = 'plantilla_productos.csv'
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
}
