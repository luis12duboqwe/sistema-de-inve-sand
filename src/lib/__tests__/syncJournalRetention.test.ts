import { describe, expect, it } from 'vitest'
import { retainedJournalEvents } from '../syncJournal'

describe('unsynced journal retention', () => {
  it('never discards a pending sale when trimming successful events', () => {
    const entries = [
      { id: 1, synced_at: undefined },
      { id: 2, synced_at: '2026-01-01' },
      { id: 3, synced_at: '2026-01-02' },
      { id: 4, synced_at: '2026-01-03' },
      { id: 5, synced_at: undefined },
    ]
    expect(retainedJournalEvents(entries, 3).map(x => x.id)).toEqual([4, 1, 5])
  })

  it('rejects writing when every slot contains a pending operation', () => {
    expect(() => retainedJournalEvents([
      { id: 1 }, { id: 2 }, { id: 3 },
    ], 2)).toThrow('Diario de sincronización lleno')
  })
})
