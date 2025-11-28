import type { ProductWithStock } from './types'

  message: string
  errors: { row: n
  message: string
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
 

  const lines = csvText.split('\n').f
  
    const row: st
 

      
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
  
    errors.push('Garantía debe ser un n
  
  if (!categoria || !['celular', 'accesorio'].includes
  }
  
    'usado': 'usado',
    'grado a': 'grado A',
  }
  c
  
  
    return { valid: false, errors }
  
   
  
    categoria: categoria as 'celular' | 'accesorio'
    sku: row.SKU.trim(),
    precio: precio,
   
  
  return { valid: true, errors: [], product }

  csvText: string,
): CSVImportResult {
    const rows = parseCSV
    if (rows.length === 
   
  
        products: []
    }
    const headers = rows[0]
   
  
        success: false,
        importedCount: 0,
   
  
    const products: Partial<ProductWithStock>[
    
      const row = rows[i]
        continue
      
      headers.forEach((header, index) => {
      })
      const validation =
      if (validation.vali
      } else {
          errors.push({
            error: error
        })
   
  
        success: false,
 

    }
    return {
      message: `${p
      errors,
    }
    return {
    
      errors: [],
    }
}
export function generateCSVTemplate(): st
  const exampleRows = [
    ['SAM-S23-256-U
  ]
  const
}
expo
  const blob = new Blob([cs
  const url = URL.createObjectURL(blob)
  li
  link.style.visibility = 'hidden'
  link.click()
}

























































































