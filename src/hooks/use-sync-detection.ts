import { useEffect, useRef } from 'react'
import { getKV } from '../lib/kvStorage'

export interface SyncEvent {
  key: string
  oldValue: any
  newValue: any
  timestamp: Date
  source: 'local' | 'remote'
}

export function useSyncDetection(
  keys: string[],
  onSync?: (event: SyncEvent) => void
) {
  const lastValuesRef = useRef<Map<string, any>>(new Map())
  const isFirstLoadRef = useRef(true)
  const onSyncRef = useRef(onSync)

  // Actualizar la referencia cuando cambie onSync
  useEffect(() => {
    onSyncRef.current = onSync
  }, [onSync])

  useEffect(() => {
    const checkForChanges = async () => {
      const kv = getKV()
      for (const key of keys) {
        try {
          const currentValue = await kv.get(key)
          const lastValue = lastValuesRef.current.get(key)

          if (!isFirstLoadRef.current && currentValue !== lastValue) {
            const event: SyncEvent = {
              key,
              oldValue: lastValue,
              newValue: currentValue,
              timestamp: new Date(),
              source: 'remote'
            }

            onSyncRef.current?.(event)
          }

          lastValuesRef.current.set(key, currentValue)
        } catch (error) {
          console.error(`Error checking sync for key ${key}:`, error)
        }
      }

      if (isFirstLoadRef.current) {
        isFirstLoadRef.current = false
      }
    }

    checkForChanges()

    const interval = setInterval(checkForChanges, 2000)

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key && keys.some(k => e.key === `spark-kv-${k}`)) {
        checkForChanges()
      }
    }

    window.addEventListener('storage', handleStorageChange)

    return () => {
      clearInterval(interval)
      window.removeEventListener('storage', handleStorageChange)
    }
  }, [keys])
}
