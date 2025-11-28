import type { ProductWithStock } from './types'

export interface CSVValidationResult {
  valid: boolean
}
export interface CSVImportResult {
 

export interface CSVImportResult {
  success: boolean
  message: string
  importedCount: number
  errors: { row: number; error: string }[]
  products: Partial<ProductWithStock>[]
}

    let current = ''
    
      const char = line[i]
  
          current += '"'
        } else {
        }
        row.push(current
    
      }
    
    ro
  
}
function validateProduct
  rowNumber: 
): CSVValidation
  
    error
  
    errors.push('Nombre e
  
  if (!categor
  }
  const
    '
    
  }
  const condicion 
   
  
  if (isNaN(p
 

    errors.push('Garantía de
  
  if (isNaN(stock) |
  }
  if (errors.length > 0)
      valid: false,
  
  
    valid: true,
   
  
      marca: row.Marca?.trim
      capacidad: row.Capacidad?.trim()
   
  
      activo: true
  }

  t
  
      return {
        message: 'El 
        errors: [],
      }
    
    const products: Partial<ProductWithS
   
  
      headers.forEach((header, index) => {
      })
      const validation = validateProductRow(rowData, i + 1, profileId)
   
  
          row: i + 1,
        })
    }
   
  
        : 'No se encontraron productos válidos',
      errors: importErrors,
    }
   
  
      errors: [],
    }
}
exp
  
  ].join('\n')
  const blob
  const link = docu
  link.download = 'plantilla_p
  lin
  U

export con















































































    'DEMO001,iPhone 13 Pro,celular,Apple,iPhone 13 Pro,128GB,nuevo,15000,HNL,12,5'


  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.download = 'plantilla_productos.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

}
