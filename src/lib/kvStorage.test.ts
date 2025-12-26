import { describe, it, expect } from 'vitest'

// Test mínimo: verificamos que el módulo exporta `getKV` y que al menos
// los métodos básicos existen (sin depender de Spark KV en Vitest).
describe('kvStorage', () => {
  it('exports getKV with basic methods', async () => {
    const mod = await import('./kvStorage')
    expect(typeof mod.getKV).toBe('function')

    const kv = mod.getKV()
    expect(kv).toBeTruthy()
    expect(typeof kv.get).toBe('function')
    expect(typeof kv.set).toBe('function')
    expect(typeof kv.delete).toBe('function')
    expect(typeof kv.keys).toBe('function')
  })
})
