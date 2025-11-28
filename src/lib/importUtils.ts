import type { ProductWithStock } from './types'

export interface CSVValidationResult {
  valid: boolean
}
export interface ImportResult {
 

export interface ImportResult {
  success: boolean
  message: string
  products: Partial<ProductWithStock>[]
  errors: { row: number; errors: string[] }[]
  importedCount: number
}

    const char = line[i]
    if (char === '"') {
        current +=
      } else {

      row.push(current.trim())
    } else {
    
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
  
  
  }
  const garantia = parseInt(row['Garan
   
  
  if (isNaN(stock) || stock < 0) {
  }
  i
  
    }
  if (!condicion || !['nuevo', 'usado', 'reacondicionado', 'grado a'].includes(condicion)) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado a"')
   
  
      marca: row.Marca?.trim() || '',
      capacidad: row.Capacidad?.trim
      precio: precio,
   
  
  const garantia = parseInt(row['Garantía (meses)'] || row.Garantía || '0')
}
export function parseProductsCSV(
  p
  
  if (lines.length < 2) {
      success: false,
      products: [],
   
  
  const importErrors: { ro
  
  const headers = p
  for (let i
    i
   
  
      row[
    
    
      products
      sku: row.SKU?.trim() || row.Código?.trim() || '',
        error: validation.errors
    }
  
      modelo: row.Modelo?.trim() || '',
      capacidad: row.Capacidad?.trim() || '',
      condicion: condicion as 'nuevo' | 'usado' | 'reacondicionado' | 'grado A',
      precio: precio,
      moneda: row.Moneda?.trim() || 'HNL',
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
  link.downl
      success: false,
  link.click()
  
      errors: [],
      importedCount: 0

  }

  const importErrors: { row: number; errors: string[] }[] = []
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

    } else {
      importErrors.push({
        row: i + 1,
        errors: validation.errors
      })

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


export function downloadCSVTemplate() {
  const csvContent = [
    'SKU,Nombre,Categoría,Marca,Modelo,Capacidad,Condición,Precio,Moneda,Garantía (meses),Stock',
    'ABC123,iPhone 13,celular,Apple,13,128GB,nuevo,15000,HNL,12,5'





  
  link.href = url

  link.style.visibility = 'hidden'
  document.body.appendChild(link)

  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)

