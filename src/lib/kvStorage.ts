/**
 * KV Storage Wrapper
 * Proporciona una capa de abstracción sobre spark.kv con fallback a localStorage
 */

interface SparkKV {
  get: <T>(key: string) => Promise<T | undefined>
  set: <T>(key: string, value: T) => Promise<void>
  delete: (key: string) => Promise<void>
  keys: () => Promise<string[]>
}

class LocalStorageKV implements SparkKV {
  private prefix = 'spark-kv-'

  async get<T>(key: string): Promise<T | undefined> {
    try {
      const fullKey = this.prefix + key
      const item = localStorage.getItem(fullKey)
      if (item === null || item === 'undefined') {
        return undefined
      }
      const parsed = JSON.parse(item) as T
      return parsed
    } catch (error) {
      console.error(`LocalStorageKV get error for key "${key}":`, error)
      return undefined
    }
  }

  async set<T>(key: string, value: T): Promise<void> {
    try {
      const fullKey = this.prefix + key
      const serialized = JSON.stringify(value)
      localStorage.setItem(fullKey, serialized)
    } catch (error) {
      console.error(`LocalStorageKV set error for key "${key}":`, error)
      throw new Error(`Failed to save to localStorage: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async delete(key: string): Promise<void> {
    try {
      localStorage.removeItem(this.prefix + key)
    } catch (error) {
      console.error('LocalStorageKV delete error:', error)
      throw new Error(`Failed to delete from localStorage: ${error instanceof Error ? error.message : 'Unknown error'}`)
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

/**
 * Wrapper seguro para Spark KV con fallback automático a localStorage
 */
class SafeSparkKV implements SparkKV {
  private sparkKV: any
  private fallback: LocalStorageKV
  private cache: Map<string, { value: any; timestamp: number }> = new Map()
  private readonly CACHE_DURATION = 60000 // 60 segundos

  constructor(sparkKV: any) {
    this.sparkKV = sparkKV
    this.fallback = new LocalStorageKV()
  }

  async get<T>(key: string): Promise<T | undefined> {
    // Verificar caché en memoria primero
    const cached = this.cache.get(key)
    if (cached && (Date.now() - cached.timestamp) < this.CACHE_DURATION) {
      console.log(`Cache hit for key "${key}"`)
      return cached.value as T
    }

    try {
      const result = await this.sparkKV.get(key)
      // Guardar en caché
      this.cache.set(key, { value: result, timestamp: Date.now() })
      return result
    } catch (error) {
      console.warn(`Spark KV get failed for "${key}", using localStorage:`, error)
      const fallbackResult = await this.fallback.get<T>(key)
      // Guardar en caché el resultado del fallback también
      this.cache.set(key, { value: fallbackResult, timestamp: Date.now() })
      return fallbackResult
    }
  }

  async set<T>(key: string, value: T): Promise<void> {
    // Actualizar caché inmediatamente
    this.cache.set(key, { value, timestamp: Date.now() })
    
    try {
      await this.sparkKV.set(key, value)
      // También guardar en localStorage como backup
      await this.fallback.set(key, value)
    } catch (error) {
      console.warn(`Spark KV set failed for "${key}", using localStorage:`, error)
      await this.fallback.set(key, value)
    }
  }

  async delete(key: string): Promise<void> {
    // Invalidar caché
    this.cache.delete(key)
    
    try {
      await this.sparkKV.delete(key)
    } catch (error) {
      console.warn(`Spark KV delete failed for "${key}", using localStorage:`, error)
      await this.fallback.delete(key)
    }
  }

  async keys(): Promise<string[]> {
    try {
      return await this.sparkKV.keys()
    } catch (error) {
      console.warn('Spark KV keys failed, using localStorage:', error)
      return await this.fallback.keys()
    }
  }
}

/**
 * Obtiene la instancia de KV Storage
 * Usa spark.kv si está disponible, de lo contrario usa localStorage
 */
export function getKVStorage(): SparkKV {
  // Verificar si spark.kv está disponible
  if (typeof window !== 'undefined' && window.spark?.kv) {
    // Validar que spark.kv tenga los métodos necesarios
    const kv = window.spark.kv
    if (typeof kv.get === 'function' && 
        typeof kv.set === 'function' && 
        typeof kv.delete === 'function' && 
        typeof kv.keys === 'function') {
      // DESHABILITADO: Spark KV causa errores 429 (Too Many Requests)
      // console.log('Using Spark KV with localStorage fallback')
      // return new SafeSparkKV(kv)
      console.log('Spark KV disabled due to rate limits, using localStorage')
      return new LocalStorageKV()
    }
  }
  
  // Fallback a localStorage
  console.log('Spark KV not available, using localStorage')
  return new LocalStorageKV()
}

// Instancia singleton
let kvInstance: SparkKV | null = null

/**
 * Obtiene la instancia singleton de KV Storage
 */
export function getKV(): SparkKV {
  if (!kvInstance) {
    kvInstance = getKVStorage()
  }
  return kvInstance
}

/**
 * Resetea la instancia de KV (útil para testing)
 */
export function resetKV(): void {
  kvInstance = null
}
