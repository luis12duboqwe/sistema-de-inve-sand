import { useEffect, useRef } from 'react'
import { toast } from 'sonner'

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

  useEffect(() => {
    const checkForChanges = async () => {
      for (const key of keys) {
        try {
          const currentValue = await spark.kv.get(key)
          const lastValue = lastValuesRef.current.get(key)

          if (!isFirstLoadRef.current && currentValue !== lastValue) {
            const event: SyncEvent = {
              key,
              oldValue: lastValue,
              newValue: currentValue,
              timestamp: new Date(),
              source: 'remote'
            }

            onSync?.(event)
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
  }, [keys, onSync])
}
