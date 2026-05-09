import { describe, expect, it } from 'vitest'
import { parseProductsCSV } from '../importUtils'

describe('importUtils', () => {
  it('parses product cost and currency from CSV', () => {
    const csv = [
      'SKU,Nombre,Categoría,Marca,Modelo,Capacidad,Condición,Precio,Costo,Moneda,Garantía (meses),Stock',
      'USD-001,Producto USD,accesorio,Marca,Modelo,,nuevo,25,10.5,USD,6,2'
    ].join('\n')

    const result = parseProductsCSV(csv, null)

    expect(result.success).toBe(true)
    expect(result.products[0]).toMatchObject({
      sku: 'USD-001',
      precio: 25,
      costo: 10.5,
      moneda: 'USD',
      stock_disponible: 2
    })
  })

  it('rejects negative product cost', () => {
    const csv = [
      'SKU,Nombre,Categoría,Marca,Modelo,Capacidad,Condición,Precio,Costo,Moneda,Garantía (meses),Stock',
      'BAD-001,Producto Malo,accesorio,Marca,Modelo,,nuevo,25,-1,HNL,6,2'
    ].join('\n')

    const result = parseProductsCSV(csv, null)

    expect(result.success).toBe(false)
    expect(result.errors[0].error).toContain('El costo debe ser un número válido mayor o igual a 0')
  })
})