import { describe, expect, it } from 'vitest'
import { validatedLocalFinancingRate, originalLocalSaleTotal } from '../localFinancingIntegrity'

describe('legacy local bank rates and original amount', () => {
  it('preserves an explicitly configured 0% card surcharge', () => {
    expect(validatedLocalFinancingRate(0)).toBe(0)
    expect(validatedLocalFinancingRate(0.04)).toBe(0.04)
  })
  it.each([-0.01, NaN, Infinity, 1.2])('rejects unsafe rate %s', value => {
    expect(() => validatedLocalFinancingRate(value)).toThrow(/Tasa/)
  })
  it('records original sale before financing surcharge and before trade-in discount', () => {
    // 1000 retail - 200 trade-in = 800 financed, 10% fee -> 880 charged.
    expect(originalLocalSaleTotal(800, 200)).toBe(1000)
  })
})
