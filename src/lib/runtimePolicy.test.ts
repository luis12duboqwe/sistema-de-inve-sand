import { describe, expect, it } from 'vitest'

import {
  isProductionApiForced,
  normalizeRuntimeWrite,
  resolveRuntimeDefault,
  resolveRuntimeKVValue,
} from './runtimePolicy'

describe('runtimePolicy', () => {
  it('forces API mode in production even when the stored value is false', () => {
    expect(resolveRuntimeKVValue('settings_use_api', false, true)).toBe(true)
    expect(resolveRuntimeDefault('settings_use_api', false, true)).toBe(true)
    expect(normalizeRuntimeWrite('settings_use_api', false, true)).toBe(true)
  })

  it('preserves local mode in development and tests', () => {
    expect(resolveRuntimeKVValue('settings_use_api', false, false)).toBe(false)
    expect(resolveRuntimeDefault('settings_use_api', false, false)).toBe(false)
    expect(normalizeRuntimeWrite('settings_use_api', false, false)).toBe(false)
  })

  it('does not override unrelated KV keys in production', () => {
    expect(resolveRuntimeKVValue('settings_api_url', 'https://inventory.example/api', true))
      .toBe('https://inventory.example/api')
    expect(normalizeRuntimeWrite('inventory-products', ['p1'], true)).toEqual(['p1'])
  })

  it('reports API forcing only for production builds', () => {
    expect(isProductionApiForced(true)).toBe(true)
    expect(isProductionApiForced(false)).toBe(false)
  })
})
