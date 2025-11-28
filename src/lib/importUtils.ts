import type { ProductWithStock } from './types'

export interface CSVImportResult {
  success: boolean
  errors: { row: 
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
 

function parseCSV(csvText: string): string[][] {
  const rows: string[][] = []
    let current = ''
  
    for (let i = 0; i < line.
    if (!line.trim()) continue
    
    const row: string[] = []
    let current = ''
    let inQuotes = false
    
    for (let i = 0; i < line.length; i++) {
        current = ''
      
      }
        if (inQuotes && line[i + 1] === '"') {
          current += '"'
          i++
  
          inQuotes = !inQuotes

      } else if (char === ',' && !inQuotes) {
        row.push(current.trim())
        current = ''

        current += char
  rowNu
    }
  co
    row.push(current.trim())
    rows.push(row)
  }
  
  return rows
 

interface ValidationResult {
  valid: boolean
  const categoria 
  product?: Partial<ProductWithStock>
 

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
   
  
  const categoria = row['Categoría']?.toLowerCase()
  if (!categoria || !['celular', 'accesorio'].includes(categoria)) {
    errors.push('Categoría debe ser "celular" o "accesorio"')
  }
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'reacondicionado' | 'grado A'> = {
  }
    'usado': 'usado',
    'reacondicionado': 'reacondicionado',
    'grado a': 'grado A'
  c
):
  const condicion = condicionMap[row['Condición']?.toLowerCase()]
  if (!condicion) {
    errors.push('Condición debe ser "nuevo", "usado", "reacondicionado" o "grado A"')
  }
  
  const precio = parseFloat(row.Precio || '0')
    }
    if (products.length === 0 && importErrors.lengt
   
  
        products: []
    }
    return {
   
  
    }
    return {
   
  
    }
}
export function generate
  const exampleRows = [
    ['IPH-14-128-N', 'iPhone 14', 'celular', 'Apple'
  ]
  const csvRows = [headers, ...exampl
}
export function downloadC
  const blob = new 
  
  link.setAttribute('href', url)
  
  link.click()
  
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



