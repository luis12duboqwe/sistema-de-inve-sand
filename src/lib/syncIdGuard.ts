import type { SyncEntityType, SyncEvent } from './types'

export function getPendingLocalCreateKeys(events: readonly SyncEvent[]): Set<string> {
  const keys = new Set<string>()
  for (const event of events) {
    if (event.action !== 'create' || event.origin === 'remote') continue
    const payload = event.payload ?? {}
    const entityRecord: Record<string, unknown> | undefined =
      event.entity === 'location' ? payload.location :
      event.entity === 'sales_profile' ? payload.profile :
      event.entity === 'profile' ? payload.profile :
      event.entity === 'product' ? payload.product :
      event.entity === 'order' ? payload.order :
      event.entity === 'stock_transfer' ? payload.transfer :
      event.entity === 'return' ? payload.return : undefined
    const id = event.entityId ?? entityRecord?.id
    if (id !== undefined && id !== null) keys.add(`${event.entity}:${id}`)
  }
  return keys
}

/**
 * A local entity waiting for creation must never be mistaken for the remote
 * entity with the coincidentally identical numeric ID.
 */
export function resolveGuardedSyncId(
  map: Record<string, string | number>,
  pendingLocalCreates: ReadonlySet<string>,
  entity: SyncEntityType,
  localId: number | string,
): number | string {
  const key = `${entity}:${localId}`
  const remote = map[key]
  if (remote !== undefined && remote !== null) return remote
  if (pendingLocalCreates.has(key)) {
    throw new Error(`No puede usarse ${key}: su creación remota aún no se confirmó. Reintente después de conciliar la creación.`)
  }
  return localId
}
