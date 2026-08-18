/**
 * KV Storage Wrapper
 * Proporciona una capa de abstracción sobre localStorage.
 *
 * Política de producción:
 * - `settings_use_api` siempre se resuelve como `true`.
 * - Un intento de guardar `false` se normaliza a `true`.
 * - Eliminar la clave mantiene el valor productivo en `true`.
 *
 * Esto evita que un error de configuración, una preferencia antigua del navegador
 * o una acción de UI haga que una instalación productiva escriba contra el modo local.
 */

import {
  isProductionApiForced,
  normalizeRuntimeWrite,
  resolveRuntimeKVValue,
} from './runtimePolicy'

interface SparkKV {
  get: <T>(key: string) => Promise<T | undefined>
  set: <T>(key: string, value: T) => Promise<void>
  delete: (key: string) => Promise<void>
  keys: () => Promise<string[]>
}

const FORCE_API_KEY = 'settings_use_api'

class LocalStorageKV implements SparkKV {
  private prefix = 'spark-kv-'

  async get<T>(key: string): Promise<T | undefined> {
    try {
      const fullKey = this.prefix + key
      const item = localStorage.getItem(fullKey)
      const storedValue = item === null || item === 'undefined'
        ? undefined
        : JSON.parse(item) as T

      return resolveRuntimeKVValue<T>(key, storedValue)
    } catch (error) {
      console.error(`LocalStorageKV get error for key "${key}":`, error)
      return resolveRuntimeKVValue<T>(key, undefined)
    }
  }

  async set<T>(key: string, value: T): Promise<void> {
    try {
      const fullKey = this.prefix + key
      const valueToStore = normalizeRuntimeWrite(key, value)
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
      if (isProductionApiForced() && key === FORCE_API_KEY) {
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
