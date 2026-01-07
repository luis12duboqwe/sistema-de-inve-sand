import { describe, expect, it } from 'vitest'
import { createTransferStockSchema } from '@/lib/validation/transferStockSchema'
import type { ProductWithStock } from '@/lib/types'

const mockProduct: ProductWithStock = {
  id: 1,
  sku: 'SKU-001',
  nombre: 'Galaxy Demo',
  categoria: 'celular',
  marca: 'Samsung',
  modelo: 'S24',
  condicion: 'nuevo',
  precio: 15000,
  moneda: 'HNL',
  garantia_meses: 12,
  activo: true,
  stock_disponible: 10,
  stock_items: [
    {
      id: 1,
      product_id: 1,
      location_id: 100,
      cantidad_disponible: 8,
      cantidad_reservada: 2
    },
    {
      id: 2,
      product_id: 1,
      location_id: 200,
      cantidad_disponible: 4,
      cantidad_reservada: 0
    }
  ]
}

describe('createTransferStockSchema', () => {
  const schema = createTransferStockSchema(mockProduct)

  it('rechaza cuando faltan ubicaciones', () => {
    const result = schema.safeParse({ cantidad: 1 })
    expect(result.success).toBe(false)
    if (!result.success) {
      const paths = result.error.issues.map(issue => issue.path[0])
      expect(paths).toContain('fromLocationId')
      expect(paths).toContain('toLocationId')
    }
  })

  it('rechaza cuando origen y destino son iguales', () => {
    const result = schema.safeParse({
      fromLocationId: 100,
      toLocationId: 100,
      cantidad: 1
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some(issue => issue.path[0] === 'toLocationId')).toBe(true)
    }
  })

  it('rechaza cuando la cantidad supera el stock libre', () => {
    // En la ubicación 100 hay 8 disponibles y 2 reservados => stock libre = 6
    const result = schema.safeParse({
      fromLocationId: 100,
      toLocationId: 200,
      cantidad: 7
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some(issue => issue.path[0] === 'cantidad')).toBe(true)
    }
  })

  it('acepta transferencias válidas', () => {
    const result = schema.safeParse({
      fromLocationId: 100,
      toLocationId: 200,
      cantidad: 5,
      notas: 'Reabastecimiento semanal'
    })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.cantidad).toBe(5)
      expect(result.data.notas).toBe('Reabastecimiento semanal')
    }
  })
})
