import type { ProductWithStock } from './types'

  product?: Partial<ProductWithStock>
}
export interface CSVImportResult {
  message: strin
 

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
}

    
      const char = line[i]
      if (char === '"') {
  
        } else {
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
    
  if (!row.SKU?.trim(
  }
  i
  
  return rows
}

    'nuevo': 'nuevo',
    'grado a': 'grado A',
    'reacondicionado
  
  const condicion = cond
  const precio = parseFloat(r
  
  
  if (isNaN(garantiaMeses) || garan
  }
  
    errors.push('Stock debe 
  
  }
  
  }
  return {
    product: {
  }
  
  const condicionMap: Record<string, 'nuevo' | 'usado' | 'grado A' | 'reacondicionado'> = {
    'nuevo': 'nuevo',
      moneda: row.Mon
      stock_disponible: s
    'grado b': 'grado A',
    'reacondicionado': 'reacondicionado'
  }
  
    
      return {
  
        errors: [],
  if (isNaN(precio) || precio <= 0) {
    errors.push('Precio debe ser un número válido mayor a 0')
   
  
      const rowData: Record<string, string> = {}
      headers.forEach((header, index) => {
      })
   
  
  const stock = parseInt(row.Stock || '0')
  if (isNaN(stock) || stock < 0) {
    errors.push('Stock debe ser un número válido')
  }
  
  if (errors.length > 0) {
        impo
      valid: false,
      error: errors.join(', ')
    r
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
  con
  }
}

export function parseCSVFile(csvText: string, profileId: number): CSVImportResult {
  try {
    const rows = parseCSV(csvText)
    
    if (rows.length === 0) {
      return {
  document.body.appendC
        message: 'El archivo CSV está vacío',
  document.body.removeChi
        errors: [],

      }

    
    const headers = rows[0]
    const products: Partial<ProductWithStock>[] = []
    const importErrors: { row: number; error: string }[] = []
    
    for (let i = 1; i < rows.length; i++) {


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



        success: false,





    }
    
    return {





    }

    return {



      errors: [],

    }

}



  const exampleRows = [


  ]
  




  

  const url = URL.createObjectURL(blob)
  





  link.click()


  URL.revokeObjectURL(url)
}
