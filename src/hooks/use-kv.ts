import { useState, useEffect, useCallback, useRef } from 'react'
import { getKV } from '@/lib/kvStorage'
import { normalizeRuntimeWrite, resolveRuntimeDefault } from '@/lib/runtimePolicy'

/**
 * Tipo para la función de actualización que puede recibir un valor o una función
 */
type SetStateAction<T> = T | ((prevValue: T) => T)

/**
 * Hook personalizado que reemplaza useKV de @github/spark/hooks.
 * Usa nuestra capa de abstracción kvStorage sobre localStorage y soporta el mismo
 * patrón que useState: acepta valores directos o funciones de actualización.
 *
 * En producción `settings_use_api` se resuelve como `true` desde el primer render.
 * Esto evita una ventana transitoria en modo local antes de que termine la lectura KV.
 */
export function useKV<T>(
  key: string,
  defaultValue: T
): [T, (value: SetStateAction<T>) => void] {
  const runtimeDefault = resolveRuntimeDefault(key, defaultValue)
  const [value, setValue] = useState<T>(runtimeDefault)
  const [isInitialized, setIsInitialized] = useState(false)
  const valueRef = useRef<T>(runtimeDefault)

  useEffect(() => {
    valueRef.current = value
  }, [value])

  useEffect(() => {
    const loadValue = async () => {
      try {
        const kv = getKV()
        const storedValue = await kv.get<T>(key)
        if (storedValue !== undefined) {
          const runtimeValue = normalizeRuntimeWrite(key, storedValue)
          setValue(runtimeValue)
          valueRef.current = runtimeValue
        }
        setIsInitialized(true)
      } catch (error) {
        console.error(`Error loading KV key "${key}":`, error)
        setIsInitialized(true)
      }
    }

    void loadValue()
  }, [key])

  const updateValue = useCallback(
    async (newValue: SetStateAction<T>) => {
      try {
        const requestedValue = typeof newValue === 'function'
          ? (newValue as (prevValue: T) => T)(valueRef.current)
          : newValue
        const valueToSet = normalizeRuntimeWrite(key, requestedValue)

        const kv = getKV()
        await kv.set(key, valueToSet)
        setValue(valueToSet)
        valueRef.current = valueToSet
      } catch (error) {
        console.error(`Error saving KV key "${key}":`, error)
        throw error
      }
    },
    [key]
  )

  useEffect(() => {
    if (!isInitialized) return

    const handleStorageChange = async (e: StorageEvent) => {
      if (e.key === `spark-kv-${key}`) {
        try {
          const kv = getKV()
          const newValue = await kv.get<T>(key)
          if (newValue !== undefined) {
            const runtimeValue = normalizeRuntimeWrite(key, newValue)
            setValue(runtimeValue)
            valueRef.current = runtimeValue
          }
        } catch (error) {
          console.error(`Error syncing KV key "${key}":`, error)
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [key, isInitialized])

  return [value, updateValue]
}
