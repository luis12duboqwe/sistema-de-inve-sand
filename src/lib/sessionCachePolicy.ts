import { isProductionBuild } from './runtimePolicy'

const SESSION_ONLY_BUSINESS_KEYS = new Set([
  'inventory-products',
  'inventory-orders',
  'inventory-profiles',
  'inventory-locations',
])

/** Remove historical per-user datasets and auth material from shared tabs. */
export function clearLegacyBusinessStorage(
  storage: Pick<Storage, 'removeItem'> = localStorage,
  productionBuild = isProductionBuild(),
): void {
  if (!productionBuild) return
  for (const key of SESSION_ONLY_BUSINESS_KEYS) storage.removeItem(`spark-kv-${key}`)
  storage.removeItem('auth_user')
  storage.removeItem('auth_token')
}

/** Persist display preferences, never production customer/order/inventory datasets. */
export function isSessionOnlyBusinessKey(
  key: string,
  productionBuild = isProductionBuild(),
): boolean {
  return productionBuild && SESSION_ONLY_BUSINESS_KEYS.has(key)
}
