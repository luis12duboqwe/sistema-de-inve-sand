import { describe, expect, it } from 'vitest'
import { validateLocalTransferRequest } from '../localTransferIntegrity'
import type { CreateStockTransferRequest } from '../types'

const transfer = (patch: Partial<CreateStockTransferRequest> = {}): CreateStockTransferRequest => ({
  product_id: 1, from_location_id: 1, to_location_id: 2, cantidad: 1,
  ...patch,
})

describe('legacy local transfer input invariants', () => {
  it('accepts a positive transfer between distinct locations', () => {
    expect(() => validateLocalTransferRequest(transfer())).not.toThrow()
  })
  it.each([0, -1, 0.5, Infinity, NaN])('rejects quantity %s', cantidad => {
    expect(() => validateLocalTransferRequest(transfer({ cantidad }))).toThrow(/cantidad/)
  })
  it('rejects same origin and destination and invalid IDs', () => {
    expect(() => validateLocalTransferRequest(transfer({ to_location_id: 1 }))).toThrow(/diferente/)
    expect(() => validateLocalTransferRequest(transfer({ product_id: 0 }))).toThrow(/Identificador/)
  })
  it('rejects duplicated and malformed serials before stock reservation', () => {
    expect(() => validateLocalTransferRequest(transfer({
      cantidad: 2, imeis: ['111111111111111', '111111111111111'],
    }))).toThrow(/duplicado/)
    expect(() => validateLocalTransferRequest(transfer({ imeis: [' 111111111111111'] }))).toThrow(/espacios/)
    expect(() => validateLocalTransferRequest(transfer({ cantidad: 2, imeis: ['111111111111111'] }))).toThrow(/no coincide/)
  })
})
