import { describe, expect, it } from 'vitest'
import { assertLocalOrderDeletionAllowed } from '../localOrderDeletionIntegrity'

describe('local order deletion preserves inventory and accounting history', () => {
  it('permits only a never-used empty draft', () => {
    expect(() => assertLocalOrderDeletionAllowed({ estado: 'pendiente' }, [], [], [])).not.toThrow()
  })
  it('rejects a pending order with reserved items instead of fabricating stock', () => {
    expect(() => assertLocalOrderDeletionAllowed({ estado: 'pendiente' }, [{ id: 1 }], [], []))
      .toThrow(/no se permite borrado/)
  })
  it('rejects completed or cancelled sales even after serials are released', () => {
    expect(() => assertLocalOrderDeletionAllowed({ estado: 'completada' }, [], [], [])).toThrow(/Solo/)
    expect(() => assertLocalOrderDeletionAllowed({ estado: 'cancelada' }, [], [], [])).toThrow(/Solo/)
  })
  it('rejects an IMEI or stock-history linkage even without order items', () => {
    expect(() => assertLocalOrderDeletionAllowed({ estado: 'pendiente' }, [], [{ id: 2 }], []))
      .toThrow(/no se permite/)
    expect(() => assertLocalOrderDeletionAllowed({ estado: 'pendiente' }, [], [], [{ id: 3 }]))
      .toThrow(/no se permite/)
  })
})
