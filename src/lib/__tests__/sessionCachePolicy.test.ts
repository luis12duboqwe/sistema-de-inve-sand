import { describe, expect, it } from 'vitest'
import { isSessionOnlyBusinessKey } from '../sessionCachePolicy'

describe('business cache isolation', () => {
  it('keeps all four business datasets ephemeral in production', () => {
    for (const key of ['inventory-products','inventory-orders','inventory-profiles','inventory-locations']) {
      expect(isSessionOnlyBusinessKey(key, true)).toBe(true)
      expect(isSessionOnlyBusinessKey(key, false)).toBe(false)
    }
  })

  it('preserves non-sensitive preferences in storage', () => {
    expect(isSessionOnlyBusinessKey('inventory_product_view_mode', true)).toBe(false)
    expect(isSessionOnlyBusinessKey('settings_use_api', true)).toBe(false)
  })
})
