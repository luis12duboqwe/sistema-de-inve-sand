import { describe, expect, it } from 'vitest'
import { getPendingLocalCreateKeys, resolveGuardedSyncId } from '../syncIdGuard'
import type { SyncEvent } from '../types'

const makeEvent = (entity: SyncEvent['entity'], action: SyncEvent['action'], record: object): SyncEvent => ({
  entity, action, payload: record, id: 'evt-local', checksum: '', timestamp: new Date(0).toISOString(), retry_count: 0, origin: 'local',
})

describe('sync local/remote identity safety', () => {
  it('refuses writes with same numeric id when a local creation was never synced', () => {
    const events = [makeEvent('product', 'create', { product: { id: 7 } })]
    const pending = getPendingLocalCreateKeys(events)
    expect(() => resolveGuardedSyncId({}, pending, 'product', 7)).toThrow(/creación remota/)
    expect(resolveGuardedSyncId({ 'product:7': 1007 }, pending, 'product', 7)).toBe(1007)
  })
  it('maps location foreign keys instead of reusing local IDs', () => {
    const pending = getPendingLocalCreateKeys([makeEvent('location', 'create', { location: { id: 1 } })])
    expect(() => resolveGuardedSyncId({}, pending, 'location', 1)).toThrow()
    expect(resolveGuardedSyncId({ 'location:1': 100 }, pending, 'location', 1)).toBe(100)
  })
  it('does not turn an unrelated remote-origin event into local create dependency', () => {
    const remote = { ...makeEvent('product', 'create', { product: { id: 5 } }), origin: 'remote' as const }
    expect(getPendingLocalCreateKeys([remote]).size).toBe(0)
  })
})
