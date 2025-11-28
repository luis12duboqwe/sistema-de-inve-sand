import type { ProductWithStock } from './types'

export interface CSVValidationResult {
  valid: boolean
  errors: string[]
  product?: Partial<ProductWithStock>
}

  message: string
  products: Partia
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
  }
  
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
    }
  }
  
  return {
    valid: true,
    errors: [],
    product: {
      codigo: row.Código?.trim() || '',
      nombre: row.Nombre.trim(),
      categoria: row.Categoría.toLowerCase() as 'celular' | 'accesorio',
      marca: row.Marca?.trim() || '',
  
    return {
      message: 'El archivo CSV está vacío o no tiene datos',
      products: [],
    }
  
  const importErrors: { row: n
  const headerLine = lines[0
  
    }
   
}

    
      products.push(validation.product)
  
          row: i + 1,
        })
    }
  
    success: products.l
      ? `${products
    importedCoun
    e
}
ex
    'Código,Nombre,Categoría,Marca,Modelo,Capacida
  ].join('\n')
  
  const link = document.creat
  link.download = 'plantilla_productos.csv
  




































    'ABC123,iPhone 13,celular,Apple,13,128GB,nuevo,15000,HNL,12,5'


  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.download = 'plantilla_productos.csv'
  link.click()

}
