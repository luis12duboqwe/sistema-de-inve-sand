import type { ProductWithStock } from './types'

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
}
function parseCSV(csvText: string): str
}

function parseCSV(csvText: string): string[][] {
        if (inQuotes && line[i + 1] === '"') {
          i++
  
      } else if (char === ','
        current = ''
        current += c
    }
    
  }
  return rows

  row: Record<string, str
  profileId: number
  const errors: string[]
  if (!row.SK
  }
  if (!row.Nombre || row.Nombr
  }
  const garantiaMeses = parseInt(row['Garantí
    errors.push('Garantía debe s
  
  if (!categor
  }
  const
    '
    
  const condicion = condicio
    errors.push('C
  
  
  }
 

  
    return { valid: false, err
  
    profile_id: pro
    sku: row.SKU.trim(),
    marca: row.Marca?.trim() 
  
    precio: precio,
    garantia_meses: garantiaMeses,
   
  
}
export function importProductsFromCSV(
  p
  
  const garantiaMeses = parseInt(row['Garantía (meses)'] || '0')
  if (isNaN(garantiaMeses) || garantiaMeses < 0) {
    errors.push('Garantía debe ser un número válido')
  }
  
  const categoria = row['Categoría']?.toLowerCase()
  if (!categoria || !['celular', 'accesorio'].includes(categoria)) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
   
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'reacondicionado' | 'grado A'> = {
    'nuevo': 'nuevo',
        success: fals
    'reacondicionado': 'reacondicionado',
        errors: [],
   
  const condicion = condicionMap[row['Condición']?.toLowerCase()]
  if (!condicion) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado A"')
  }
  
  const precio = parseFloat(row.Precio || '0')
  if (isNaN(precio) || precio < 0) {
    errors.push('Precio debe ser un número válido')
  }
  
  const stock = parseInt(row.Stock || '0')
  if (isNaN(stock) || stock < 0) {
    errors.push('Stock debe ser un número entero válido')
  }
  
  if (errors.length > 0) {
      } else {
  }
  
  const product: Partial<ProductWithStock> = {
    profile_id: profileId,
    categoria: categoria as 'celular' | 'accesorio',
      return {
    nombre: row.Nombre.trim(),
    marca: row.Marca?.trim() || '',
    modelo: row.Modelo?.trim() || '',
    capacidad: row.Capacidad?.trim() || '',
    condicion: condicion,
    }
    moneda: row.Moneda?.trim() || 'HNL',
    garantia_meses: garantiaMeses,
    stock_disponible: stock,
    activo: true,
  }
  
    return {
}

export function importProductsFromCSV(
    }
  profileId: number

  try {
    const rows = parseCSV(csvText)
    
    if (rows.length === 0) {
      return {
        success: false,
        message: 'El archivo CSV está vacío',
        importedCount: 0,
        errors: [],
  const blob = new B
      }
  lin
    
  document.body.appendChild
    const requiredHeaders = ['SKU', 'Nombre', 'Categoría', 'Precio', 'Stock']
    const missingHeaders = requiredHeaders.filter(h => !headers.includes(h))
    
    if (missingHeaders.length > 0) {
      return {

        message: `Faltan las siguientes columnas requeridas: ${missingHeaders.join(', ')}`,

        errors: [],
        products: []
      }
    }

    const products: Partial<ProductWithStock>[] = []
    const importErrors: { row: number; error: string }[] = []
    
    for (let i = 1; i < rows.length; i++) {

      if (row.length === 0 || row.every(cell => !cell.trim())) {

      }

      const rowData: Record<string, string> = {}

        rowData[header] = row[index] || ''

      
      const validation = validateProductRow(rowData, i + 1, profileId)
      
      if (validation.valid && validation.product) {
        products.push(validation.product)

        validation.errors.forEach(error => {
          importErrors.push({
            row: i + 1,

          })

      }
    }
    
    if (products.length === 0 && importErrors.length > 0) {
      return {

        message: 'No se pudo importar ningún producto debido a errores de validación',
        importedCount: 0,
        errors: importErrors,
        products: []
      }

    

      success: true,
      message: `${products.length} productos listos para importar`,
      importedCount: products.length,
      errors: importErrors,
      products

  } catch (error) {

      success: false,
      message: `Error al procesar el archivo CSV: ${error instanceof Error ? error.message : 'Error desconocido'}`,
      importedCount: 0,

      products: []

  }


export function generateCSVTemplate(): string {
  const headers = ['SKU', 'Nombre', 'Categoría', 'Marca', 'Modelo', 'Capacidad', 'Condición', 'Precio', 'Moneda', 'Garantía (meses)', 'Stock']

    ['SAM-S23-256-U', 'Samsung Galaxy S23', 'celular', 'Samsung', 'Galaxy S23', '256GB', 'usado', '15000', 'HNL', '6', '3'],
    ['IPH-14-128-N', 'iPhone 14', 'celular', 'Apple', 'iPhone 14', '128GB', 'nuevo', '22000', 'HNL', '12', '5'],
    ['CASE-IPH-14', 'Funda iPhone 14', 'accesorio', 'Generic', 'Funda Protectora', '', 'nuevo', '250', 'HNL', '3', '20']

  
  const csvRows = [headers, ...exampleRows]
  return csvRows.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')


export function downloadCSVTemplate() {
  const csvContent = generateCSVTemplate()
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })

  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', 'plantilla_productos.csv')

  document.body.appendChild(link)

  document.body.removeChild(link)

