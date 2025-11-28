import type { ProductWithStock } from './types'

export interface CSVValidationResult {
  valid: boolean
  errors: string[]
  product?: Partial<ProductWithStock>
}

  message: string
  errors: { row: n
}
function parseCSVLine(l
  let current = ''

 

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

  row: Record<stri
  profileId?
  const errors: strin
  if 
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
  
  if (!row.Nombre?.trim()) {
    errors.push('Nombre es requerido')
  c
  
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
  con
  }
  
  return {
    valid: true,
    errors: [],
    product: {
      codigo: row.Código?.trim() || '',
      nombre: row.Nombre.trim(),
      categoria: row.Categoría.toLowerCase() as 'celular' | 'accesorio',
      marca: row.Marca?.trim() || '',
      modelo: row.Modelo?.trim() || '',
      capacidad: row.Capacidad?.trim() || '',
      condicion: condicion as 'nuevo' | 'usado' | 'reacondicionado',
      precio: precio,
      moneda: (row.Moneda?.toUpperCase() || 'HNL') as 'HNL' | 'USD',
      garantia_meses: garantia,
      stock_disponible: stock,
      profile_id: profileId,
      activo: true
  
  }
 

export function parseCSV(csvContent: string, profileId?: string): CSVImportResult {
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

  ].join('\n')
  



  link.href = url




  URL.revokeObjectURL(url)

