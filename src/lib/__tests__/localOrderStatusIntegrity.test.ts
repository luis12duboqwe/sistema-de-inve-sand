import { describe, expect, it } from 'vitest'
import { validateLocalOrderStatusChange } from '../localOrderStatusIntegrity'

describe('local order status transition invariants', () => {
  it('permits pending -> ready -> completed -> validated', () => {
    expect(() => validateLocalOrderStatusChange('pendiente','por_entregar')).not.toThrow()
    expect(() => validateLocalOrderStatusChange('por_entregar','completada')).not.toThrow()
    expect(() => validateLocalOrderStatusChange('completada','validada')).not.toThrow()
  })
  it('rejects a status-only cancellation without stock release', () => {
    expect(() => validateLocalOrderStatusChange('pendiente','cancelada')).toThrow(/cancelOrder/)
  })
  it('rejects reactivating a cancelled order and downgrading completed or validated sales', () => {
    expect(() => validateLocalOrderStatusChange('cancelada','completada')).toThrow(/cancelada/)
    expect(() => validateLocalOrderStatusChange('completada','pendiente')).toThrow(/completada/)
    expect(() => validateLocalOrderStatusChange('validada','completada')).toThrow(/validada/)
  })
  it('rejects validating before the sale was completed', () => {
    expect(() => validateLocalOrderStatusChange('pendiente','validada')).toThrow(/Primero/)
  })
})
