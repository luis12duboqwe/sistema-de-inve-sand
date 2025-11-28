import type { ProductWithStock } from './types'

  error?: string
}
export interface
  message: string
 

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
 

function parseCSV(csvText: string): string[][] {
  const lines = csvText.split('\n')
  const rows: string[][] = []
  
  for (const line of lines) {
    if (!line.trim()) continue
    
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

  
    errors.push('Nombre es req
  
  if (!categoria ||
  }
  const condicionMap: Record<
  
    'grado a': 'grado A'
  
  }
  
  const precio = parseFloat(row.Precio || 
    errors.push('Precio debe ser un nú
  }
  
  }
  const stock = parseInt(row.Stock || '0')
    errors.push('Stock debe ser un número válido')
  
  
      error: errors.join(', ')
    'nuevo': 'nuevo',
  const product: Part
    sku: row.SKU.trim(),
    categoria: categoria
  }
  
    moneda: (row.Moneda?.trim() || 'HNL') as 'HNL' | 'USD',
    stock_disponibl
  }
  r
  
}
  if (isNaN(precio) || precio < 0) {
    errors.push('Precio debe ser un número válido')
): 
  
      }
    
    const requiredHeaders = ['SKU', 'Nombre', 'Catego
   
  
  const stock = parseInt(row.Stock || '0')
  if (isNaN(stock) || stock < 0) {
    errors.push('Stock debe ser un número válido')
  }
  
  if (errors.length > 0) {
    const pr
      valid: false,
      error: errors.join(', ')
     
  }
  
  const product: Partial<ProductWithStock> = {
    profile_id: profileId,
    sku: row.SKU.trim(),
    nombre: row.Nombre.trim(),
    categoria: categoria as 'celular' | 'accesorio',
    marca: row.Marca?.trim() || '',
    modelo: row.Modelo?.trim() || '',
    capacidad: row.Capacidad?.trim() || '',
    condicion: condicion,
    precio: precio,
    moneda: (row.Moneda?.trim() || 'HNL') as 'HNL' | 'USD',
    garantia_meses: garantiaMeses,
    stock_disponible: stock,
    activo: true
  }
  
  return {
    valid: true,
    product
  }
}

export function parseProductsCSV(
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
    const requiredHeaders = ['SKU', 'Nombre', 'Categoría', 'Precio', 'Stock']
    const missingHeaders = requiredHeaders.filter(h => !headers.includes(h))
    
    if (missingHeaders.length > 0) {
      return {
        success: false,
        message: `Faltan las siguientes columnas: ${missingHeaders.join(', ')}`,
        importedCount: 0,
        errors: [],
        products: []
      }
    }
    
    const products: Partial<ProductWithStock>[] = []
    const importErrors: { row: number; error: string }[] = []
    
    for (let i = 1; i < rows.length; i++) {
      const row = rows[i]
      if (row.length === 0 || row.every(cell => !cell.trim())) continue
      
  link.setAttribute('download', 'plantilla_produ
      headers.forEach((header, index) => {
        rowData[header] = row[index]?.trim() || ''
      })
  URL.
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
  




  

}




  const url = URL.createObjectURL(blob)
  




  

  link.click()

  URL.revokeObjectURL(url)
}
