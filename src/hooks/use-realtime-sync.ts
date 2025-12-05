import { useEffect, useState, useCallback, useRef } from 'react'
import { toast } from 'sonner'

export interface SyncStatus {
  isSyncing: boolean
  lastSyncTime: Date | null
  syncError: string | null
  deviceId: string
}

export function useRealtimeSync() {
  const [syncStatus, setSyncStatus] = useState<SyncStatus>(() => ({
    isSyncing: false,
    lastSyncTime: null,
    syncError: null,
    deviceId: generateDeviceId()
  }))
  
  const syncTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)
  const isFirstMount = useRef(true)

  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key && e.key.startsWith('spark-kv-')) {
        setSyncStatus(prev => ({
          ...prev,
          isSyncing: true,
          lastSyncTime: new Date()
        }))

        if (syncTimeoutRef.current) {
          clearTimeout(syncTimeoutRef.current)
        }

        syncTimeoutRef.current = setTimeout(() => {
          setSyncStatus(prev => ({
            ...prev,
            isSyncing: false
          }))
        }, 500)

        if (!isFirstMount.current) {
          const keyName = e.key.replace('spark-kv-', '')
          toast.info(`Cambio detectado: ${keyName}`, {
            description: 'Datos sincronizados desde otro dispositivo',
            duration: 2000
          })
        }
      }
    }

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        setSyncStatus(prev => ({
          ...prev,
          lastSyncTime: new Date()
        }))
      }
    }

    window.addEventListener('storage', handleStorageChange)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    setTimeout(() => {
      isFirstMount.current = false
    }, 1000)

    return () => {
      window.removeEventListener('storage', handleStorageChange)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current)
      }
    }
  }, [])

  const markSyncStart = useCallback(() => {
    setSyncStatus(prev => ({
      ...prev,
      isSyncing: true
    }))
  }, [])

  const markSyncComplete = useCallback(() => {
    setSyncStatus(prev => ({
      ...prev,
      isSyncing: false,
      lastSyncTime: new Date(),
      syncError: null
    }))
  }, [])

  const markSyncError = useCallback((error: string) => {
    setSyncStatus(prev => ({
      ...prev,
      isSyncing: false,
      syncError: error
    }))
  }, [])

  return {
    syncStatus,
    markSyncStart,
    markSyncComplete,
    markSyncError
  }
}

function generateDeviceId(): string {
  const stored = localStorage.getItem('stellar-device-id')
  if (stored) return stored

  const id = `device-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`
  localStorage.setItem('stellar-device-id', id)
  return id
}
