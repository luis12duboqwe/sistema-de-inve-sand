import { isProductionBuild } from './runtimePolicy'

const SESSION_ONLY_BUSINESS_KEYS = new Set([
  'inventory-products',
  'inventory-orders',
  'inventory-profiles',
  'inventory-locations',
])

/** Persist display preferences, never production customer/order/inventory datasets. */
export function isSessionOnlyBusinessKey(
  key: string,
  productionBuild = isProductionBuild(),
): boolean {
  return productionBuild && SESSION_ONLY_BUSINESS_KEYS.has(key)
}
