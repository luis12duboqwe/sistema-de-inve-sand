import { useEffect, useState, useCallback, useRef } from 'react'
import { toast } from 'sonner'

export interface SyncStatus {
  isSyncing: boolean
  lastSyncTime: Date | null
  syncError: string | null
  deviceId: string
}

export function useRealtimeSync() {
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    isSyncing: false,
    lastSyncTime: null,
    syncError: null,
    deviceId: generateDeviceId()
  })

  const syncTimeoutRef = useRef<number | null>(null)
  const isFirstMount = useRef(true)


    isFirstMount.current = false
  }, [])

  const markSyncStart = useCallback(() => {
    setSyncStatus(prev => ({
      ...prev,
      isSyncing: true,
      syncError: null
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

  useEffect(() => {
        ...prev,
        lastSyncTime: new Date()

        clearTimeout(syncTimeo

        setSyncStatus(pr
          isSyncing: false
      }, 

        toast.info(`Cambio detectad
          duration: 2000
      }


      window.removeEventListener
        clearTimeo
    }

    syncStatu

  }

  const stored = localStorage.getItem('stellar-devic
          description: 'Datos sincronizados desde otro dispositivo',
          duration: 2000
        })
      }
    }

    window.addEventListener('storage', handleStorageChange)

    return () => {
      window.removeEventListener('storage', handleStorageChange)
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current)
      }
    }
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

  const id = `device-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  localStorage.setItem('stellar-device-id', id)
  return id
}
  if (stored) return stored

  const id = `device-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  localStorage.setItem('stellar-device-id', id)
  return id
}
