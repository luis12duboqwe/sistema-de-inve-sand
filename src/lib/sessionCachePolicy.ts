import { isProductionBuild } from './runtimePolicy'

const BUSINESS_KEY_PREFIX = 'inventory-'

/** Remove historical per-user datasets and auth material from shared tabs. */
export function clearLegacyBusinessStorage(
  storage: Pick<Storage, 'length' | 'key' | 'removeItem'> = localStorage,
  productionBuild = isProductionBuild(),
): void {
  if (!productionBuild) return
  const oldKeys: string[] = []
  for (let index = 0; index < storage.length; index++) {
    const key = storage.key(index)
    if (key?.startsWith('spark-kv-' + BUSINESS_KEY_PREFIX)) oldKeys.push(key)
  }
  for (const key of oldKeys) storage.removeItem(key)
  storage.removeItem('auth_user')
  storage.removeItem('auth_token')
}

/** Persist display preferences, never production customer/order/inventory datasets. */
export function isSessionOnlyBusinessKey(
  key: string,
  productionBuild = isProductionBuild(),
): boolean {
  return productionBuild && key.startsWith(BUSINESS_KEY_PREFIX)
}
