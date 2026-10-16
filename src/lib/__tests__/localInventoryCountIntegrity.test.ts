import { describe, expect, it } from 'vitest'
import { assertLocalInventoryCountIsFresh } from '../localInventoryCountIntegrity'

const product = [{ id: 1, is_serialized: false }, { id: 2, is_serialized: true }]
const count = (line: { product_id: number; expected_quantity: number; counted_quantity: number; imeis?: string[] }) => ({
  location_id: 5, items: [line],
})

describe('local stale count approval guard', () => {
  it('allows an unchanged snapshot and a genuine physical shortage', () => {
    expect(() => assertLocalInventoryCountIsFresh(
      count({ product_id: 1, expected_quantity: 4, counted_quantity: 2 }),
      [{ product_id: 1, location_id: 5, cantidad_disponible: 4, cantidad_reservada: 0 }],
      product, [],
    )).not.toThrow()
  })
  it('blocks approval after a later sale even when the scanned count is higher', () => {
    expect(() => assertLocalInventoryCountIsFresh(
      count({ product_id: 1, expected_quantity: 4, counted_quantity: 4 }),
      [{ product_id: 1, location_id: 5, cantidad_disponible: 3, cantidad_reservada: 0 }],
      product, [],
    )).toThrow(/obsoleto/)
  })
  it('does not overwrite a reservation from a concurrent transfer', () => {
    expect(() => assertLocalInventoryCountIsFresh(
      count({ product_id: 1, expected_quantity: 4, counted_quantity: 4 }),
      [{ product_id: 1, location_id: 5, cantidad_disponible: 4, cantidad_reservada: 1 }],
      product, [],
    )).toThrow(/reservadas/)
  })
  it('blocks a count after the original IMEI was sold', () => {
    expect(() => assertLocalInventoryCountIsFresh(
      count({ product_id: 2, expected_quantity: 1, counted_quantity: 1, imeis: ['111'] }),
      [{ product_id: 2, location_id: 5, cantidad_disponible: 0 }],
      product, [{ imei: '111', product_id: 2, location_id: 5, vendido: true }],
    )).toThrow(/obsoleto/)
  })
  it('rejects unknown serials even without later stock change', () => {
    expect(() => assertLocalInventoryCountIsFresh(
      count({ product_id: 2, expected_quantity: 1, counted_quantity: 1, imeis: ['fake'] }),
      [{ product_id: 2, location_id: 5, cantidad_disponible: 1 }],
      product, [{ imei: '111', product_id: 2, location_id: 5, vendido: false }],
    )).toThrow(/no coinciden/)
  })
})
