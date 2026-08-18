const FORCE_API_KEY = 'settings_use_api'

function currentProductionFlag(): boolean {
  return Boolean(import.meta.env?.PROD)
}

export function isProductionBuild(): boolean {
  return currentProductionFlag()
}

export function isProductionApiForced(
  productionBuild = currentProductionFlag()
): boolean {
  return productionBuild
}

export function resolveRuntimeKVValue<T>(
  key: string,
  value: T | undefined,
  productionBuild = currentProductionFlag()
): T | undefined {
  if (productionBuild && key === FORCE_API_KEY) {
    return true as T
  }
  return value
}

export function resolveRuntimeDefault<T>(
  key: string,
  defaultValue: T,
  productionBuild = currentProductionFlag()
): T {
  return resolveRuntimeKVValue(key, defaultValue, productionBuild) as T
}

export function normalizeRuntimeWrite<T>(
  key: string,
  value: T,
  productionBuild = currentProductionFlag()
): T {
  return resolveRuntimeKVValue(key, value, productionBuild) as T
}
