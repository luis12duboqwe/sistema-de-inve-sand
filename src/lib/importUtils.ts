import type { ProductWithStock } from './types'

  message: string
  errors: { row: n
}
function parseCSV(csvTe
  const rows: string[][] = []
  for (const line of lines) {
}

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
    }
        }
  }
  return rows

      } else {
  product?: Partial<Pro
      }
  row
    
  const errors: string[] = [
  if (!row.SKU || 
  }
  
  }
}

  
  if (!categoria
  error?: string
  const condicionMap: Record<string, 
}

  
  if (!condicion) {
  }
  const precio = pa
    errors.push('Prec
  
  
  }
  if (errors.length > 0) {
   
  
  
    sku: row.SKU.trim(),
   
  
    condicion: condicion,
    moneda: (row.Moneda?.trim() || 'HNL') as 'HNL'
    stock_disponible: stock,
  }
  
    valid: true,
  }

  c
):
    const rows = parseCSV(csvText)
    'nuevo': 'nuevo',
        success: fals
        importedCount: 0,
        products: []
  }
  
    const missingHeaders = requiredHeaders.filter(h => !headers.i
    if (missingHead
        success: false,
   
  
    }
  if (isNaN(precio) || precio <= 0) {
    errors.push('Precio debe ser un número válido mayor a 0')
  }
  
  const stock = parseInt(row.Stock || '0')
  if (isNaN(stock) || stock < 0) {
    errors.push('Stock debe ser un número válido')
  }
  
  if (errors.length > 0) {
        })
      valid: false,
      error: errors.join(', ')
     
  }
  
  const product: Partial<ProductWithStock> = {
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
    profile_id: profileId,
    activo: true
  }
  
  return {
    valid: true,
    product
  }
e

export function parseCSVFile(
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
    
    const headers = rows[0].map(h => h.replace(/^"|"$/g, '').trim())
    const requiredHeaders = ['SKU', 'Nombre', 'Categoría', 'Precio']
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
      
      const rowData: Record<string, string> = {}
      headers.forEach((header, index) => {
        rowData[header] = row[index]?.replace(/^"|"$/g, '').trim() || ''
      })
      
      const validation = validateProductRow(rowData, i + 1, profileId)
      
      if (validation.valid && validation.product) {
        products.push(validation.product)
      } else if (validation.error) {
        importErrors.push({
          row: i + 1,
          error: validation.error
        })
      }
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
