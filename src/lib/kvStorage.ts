/**
 * KV Storage Wrapper
 * Proporciona una capa de abstracción sobre spark.kv con fallback a localStorage.
 */

interface SparkKV {
  get: <T>(key: string) => Promise<T | undefined>
  set: <T>(key: string, value: T) => Promise<void>
  delete: (key: string) => Promise<void>
  keys: () => Promise<string[]>
}

const IS_PRODUCTION_BUILD = Boolean(import.meta.env?.PROD)
const FORCE_API_KEY = 'settings_use_api'

function productionOverride<T>(key: string): T | undefined {
  if (IS_PRODUCTION_BUILD && key === FORCE_API_KEY) {
    return true as T
  }
  return undefined
}

class LocalStorageKV implements SparkKV {
  private prefix = 'spark-kv-'

  async get<T>(key: string): Promise<T | undefined> {
    const forcedValue = productionOverride<T>(key)
    if (forcedValue !== undefined) {
      return forcedValue
    }

    try {
      const fullKey = this.prefix + key
      const item = localStorage.getItem(fullKey)
      if (item === null || item === 'undefined') {
        return undefined
      }
      return JSON.parse(item) as T
    } catch (error) {
      console.error(`LocalStorageKV get error for key "${key}":`, error)
      return undefined
    }
  }

  async set<T>(key: string, value: T): Promise<void> {
    try {
      const fullKey = this.prefix + key
      const valueToStore = IS_PRODUCTION_BUILD && key === FORCE_API_KEY
        ? true
        : value
      localStorage.setItem(fullKey, JSON.stringify(valueToStore))
    } catch (error) {
      console.error(`LocalStorageKV set error for key "${key}":`, error)
      throw new Error(
        `Failed to save to localStorage: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    }
  }

  async delete(key: string): Promise<void> {
    try {
      if (IS_PRODUCTION_BUILD && key === FORCE_API_KEY) {
        localStorage.setItem(this.prefix + key, JSON.stringify(true))
        return
      }
      localStorage.removeItem(this.prefix + key)
    } catch (error) {
      console.error('LocalStorageKV delete error:', error)
      throw new Error(
        `Failed to delete from localStorage: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    }
  }

  async keys(): Promise<string[]> {
    try {
      const allKeys: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key?.startsWith(this.prefix)) {
          allKeys.push(key.substring(this.prefix.length))
        }
      }
      return allKeys
    } catch (error) {
      console.error('LocalStorageKV keys error:', error)
      return []
    }
  }
}

export function getKVStorage(): SparkKV {
  return new LocalStorageKV()
}

let kvInstance: SparkKV | null = null

export function getKV(): SparkKV {
  if (!kvInstance) {
    kvInstance = getKVStorage()
  }
  return kvInstance
}

export function resetKV(): void {
  kvInstance = null
}
