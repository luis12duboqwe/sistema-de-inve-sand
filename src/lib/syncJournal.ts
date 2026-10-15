import { getKV } from './kvStorage'
import type { SyncEvent, SyncEventInput, SyncJournalSummary } from './types'

const JOURNAL_KEY = 'sync-journal-events'
const PENDING_FLAG_KEY = 'settings_pending_sync'
const LAST_SYNC_KEY = 'settings_last_sync_at'
const MAX_JOURNAL_EVENTS = 5000

/** Serializes every read-modify-write in this tab; local journals must not lose updates. */
let writeTail: Promise<void> = Promise.resolve()
async function serializedWrite<T>(work: () => Promise<T>): Promise<T> {
  let release!: () => void
  const previous = writeTail
  writeTail = new Promise<void>(resolve => { release = resolve })
  await previous
  try {
    return await work()
  } finally {
    release()
  }
}

/** Keep ALL unacknowledged events. Never silently discard unsynced business actions. */
export function retainedJournalEvents<T extends { synced_at?: string }>(items: readonly T[], cap = MAX_JOURNAL_EVENTS): T[] {
  if (items.length <= cap) return [...items]
  const pending = items.filter(item => !item.synced_at)
  if (pending.length > cap) {
    throw new Error(`Diario de sincronización lleno: ${pending.length} cambios pendientes; sincronice o exporte antes de agregar más.`)
  }
  const completed = items.filter(item => item.synced_at)
  return [...completed.slice(-(cap - pending.length)), ...pending]
}

const kv = getKV()
const globalCrypto: Crypto | undefined =
  typeof globalThis !== 'undefined' && 'crypto' in globalThis ? (globalThis.crypto as Crypto) : undefined

function generateEventId(): string {
  if (globalCrypto && typeof globalCrypto.randomUUID === 'function') {
    return globalCrypto.randomUUID()
  }

  return 'evt-' + Math.random().toString(36).substring(2, 11) + Date.now().toString(36)
}

function safeStringify(payload: any): string {
  if (payload === undefined) {
    return 'undefined'
  }

  try {
    return JSON.stringify(payload)
  } catch (error) {
    console.warn('[syncJournal] Failed to stringify payload', error)
    return String(payload)
  }
}

function createChecksum(payload: any): string {
  const serialized = safeStringify(payload)
  let hash = 0

  for (let i = 0; i < serialized.length; i += 1) {
    const char = serialized.charCodeAt(i)
    hash = (hash << 5) - hash + char
    hash |= 0
  }

  return `${(hash >>> 0).toString(16)}-${serialized.length}`
}

async function readEvents(): Promise<SyncEvent[]> {
  try {
    const events = await kv.get<SyncEvent[]>(JOURNAL_KEY)
    return events ?? []
  } catch (error) {
    console.error('[syncJournal] Failed to read journal', error)
    throw error
  }
}

async function writeEvents(events: SyncEvent[]): Promise<void> {
  const trimmedEvents = retainedJournalEvents(events)

  await kv.set(JOURNAL_KEY, trimmedEvents)
  await kv.set(PENDING_FLAG_KEY, trimmedEvents.some(evt => !evt.synced_at))
}

function nowISO(): string {
  return new Date().toISOString()
}

export const syncJournal = {
  async getEvents(includeSynced = true): Promise<SyncEvent[]> {
    await writeTail
    const events = await readEvents()
    if (includeSynced) {
      return events
    }
    return events.filter(evt => !evt.synced_at)
  },

  async getPendingEvents(): Promise<SyncEvent[]> {
    return this.getEvents(false)
  },

  async recordEvent(input: SyncEventInput): Promise<SyncEvent> {
    return serializedWrite(async () => {
      const events = await readEvents()
      const event: SyncEvent = {
        ...input,
        id: generateEventId(),
        checksum: createChecksum(input.payload),
        timestamp: nowISO(),
        retry_count: 0,
        origin: input.origin ?? 'local'
      }

      events.push(event)
      await writeEvents(events)
      return event
    })
  },

  async markSynced(eventId: string, metadata?: Partial<SyncEvent>): Promise<SyncEvent | null> {
    return serializedWrite(async () => {
      const events = await readEvents()
      const index = events.findIndex(evt => evt.id === eventId)
      if (index === -1) {
        return null
      }

      events[index] = {
        ...events[index],
        ...metadata,
        last_error: undefined,
        retry_count: metadata?.retry_count ?? events[index].retry_count,
        synced_at: nowISO()
      }

      await writeEvents(events)
      await kv.set(LAST_SYNC_KEY, events[index].synced_at)
      return events[index]
    })
  },

  async markError(eventId: string, error: string): Promise<SyncEvent | null> {
    return serializedWrite(async () => {
      const events = await readEvents()
      const index = events.findIndex(evt => evt.id === eventId)
      if (index === -1) {
        return null
      }

      events[index] = {
        ...events[index],
        last_error: error,
        retry_count: events[index].retry_count + 1
      }

      await writeEvents(events)
      return events[index]
    })
  },

  async deleteEvent(eventId: string): Promise<void> {
    return serializedWrite(async () => {
      const events = await readEvents()
      const filtered = events.filter(evt => evt.id !== eventId)
      await writeEvents(filtered)
    })
  },

  async clearSyncedEvents(): Promise<void> {
    return serializedWrite(async () => {
      const events = await readEvents()
      const pending = events.filter(evt => !evt.synced_at)
      await writeEvents(pending)
    })
  },

  async reset(): Promise<void> {
    return serializedWrite(async () => {
      await kv.set(JOURNAL_KEY, [])
      await kv.set(PENDING_FLAG_KEY, false)
    })
  },

  async summarize(): Promise<SyncJournalSummary> {
    const events = await readEvents()
    const summary: SyncJournalSummary = {
      pending: events.filter(evt => !evt.synced_at && !evt.last_error).length,
      synced: events.filter(evt => Boolean(evt.synced_at)).length,
      failed: events.filter(evt => Boolean(evt.last_error)).length,
      lastSyncAt: await kv.get<string>(LAST_SYNC_KEY) ?? undefined
    }
    return summary
  }
}

export type { SyncEvent }
export { JOURNAL_KEY }
