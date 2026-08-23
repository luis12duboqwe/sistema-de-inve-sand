import { describe, expect, it } from 'vitest'
import type { Location, OrderWithItems, ProductWithStock, User } from '../types'
import { buildMultiStoreViewModel, hasAppPermission } from '../appViewModel'

describe('hasAppPermission', () => {
  it('allows local mode and superusers while enforcing role permissions in API mode', () => {
    const regularUser = {
      is_superuser: false,
      role: { permissions: [{ slug: 'orders:view' }] },
    } as unknown as User
    const superUser = { is_superuser: true } as unknown as User

    expect(hasAppPermission(false, null, 'anything')).toBe(true)
    expect(hasAppPermission(true, superUser, 'anything')).toBe(true)
    expect(hasAppPermission(true, regularUser, 'orders:view')).toBe(true)
    expect(hasAppPermission(true, regularUser, 'inventory:delete')).toBe(false)
    expect(hasAppPermission(true, null, 'orders:view')).toBe(false)
  })
})

describe('buildMultiStoreViewModel', () => {
  it('calculates active locations, stock aggregates and sorted location snapshots', () => {
    const locations = [
      { id: 1, nombre: 'Tienda Centro', tipo: 'tienda', activo: true },
      { id: 2, nombre: 'Bodega', tipo: 'bodega', activo: true },
      { id: 3, nombre: 'Cerrada', tipo: 'tienda', activo: false },
    ] as unknown as Location[]
    const products = [
      {
        id: 10,
        stock_disponible: 5,
        stock_items: [
          { location_id: 1, cantidad_disponible: 2 },
          { location_id: 2, cantidad_disponible: 3 },
        ],
      },
      {
        id: 11,
        stock_disponible: 0,
        stock_items: [{ location_id: 1, cantidad_disponible: 0 }],
      },
      {
        id: 12,
        stock_disponible: 4,
        stock_items: [{ location_id: 2, cantidad_disponible: 4 }],
      },
    ] as unknown as ProductWithStock[]
    const orders = [
      { id: 1, source_location_id: 1 },
      { id: 2, source_location_id: null },
      { id: 3, source_location_id: 2 },
    ] as unknown as OrderWithItems[]

    const model = buildMultiStoreViewModel(locations, products, orders)

    expect(model.activeLocations.map(location => location.id)).toEqual([1, 2])
    expect(model.productsWithLocationTracking).toHaveLength(3)
    expect(model.totalTrackedUnits).toBe(9)
    expect(model.outOfStockProducts).toBe(1)
    expect(model.locatedOrders).toBe(2)
    expect(model.locationSnapshots).toEqual([
      { id: 2, nombre: 'Bodega', tipo: 'bodega', productsAtLocation: 2, unitsAtLocation: 7 },
      { id: 1, nombre: 'Tienda Centro', tipo: 'tienda', productsAtLocation: 1, unitsAtLocation: 2 },
    ])
  })
})
