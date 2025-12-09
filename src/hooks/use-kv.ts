import { useState, useEffect, useCallback } from 'react'
import { getKV } from '@/lib/kvStorage'

/**
 * Tipo para la función de actualización que puede recibir un valor o una función
 */
type SetStateAction<T> = T | ((prevValue: T) => T)

/**
 * Hook personalizado que reemplaza useKV de @github/spark/hooks
 * Usa nuestra capa de abstracción kvStorage con fallback a localStorage
 * Soporta el mismo patrón que useState: acepta valores directos o funciones de actualización
 */
export function useKV<T>(
  key: string, 
  defaultValue: T
): [T, (value: SetStateAction<T>) => void] {
  const [value, setValue] = useState<T>(defaultValue)
  const [isInitialized, setIsInitialized] = useState(false)

  // Cargar valor inicial
  useEffect(() => {
    const loadValue = async () => {
      try {
        const kv = getKV()
        const storedValue = await kv.get<T>(key)
        if (storedValue !== undefined) {
          setValue(storedValue)
        }
        setIsInitialized(true)
      } catch (error) {
        console.error(`Error loading KV key "${key}":`, error)
        setIsInitialized(true)
      }
    }

    loadValue()
  }, [key])

  // Función para actualizar el valor (acepta valor directo o función)
  const updateValue = useCallback(
    async (newValue: SetStateAction<T>) => {
      try {
        // Si es una función, ejecutarla con el valor actual
        const valueToSet = typeof newValue === 'function' 
          ? (newValue as (prevValue: T) => T)(value)
          : newValue
        
        const kv = getKV()
        await kv.set(key, valueToSet)
        setValue(valueToSet)
      } catch (error) {
        console.error(`Error saving KV key "${key}":`, error)
        throw error
      }
    },
    [key, value]
  )

  // Escuchar cambios en localStorage (para sincronización entre tabs)
  useEffect(() => {
    if (!isInitialized) return

    const handleStorageChange = async (e: StorageEvent) => {
      if (e.key === `spark-kv-${key}`) {
        try {
          const kv = getKV()
          const newValue = await kv.get<T>(key)
          if (newValue !== undefined) {
            setValue(newValue)
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
