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
    syncError: null,
  }))
  const syncTimeoutR

    
  
          isSyncing: true,
        }))

        }
        syncTimeoutRef.current = setTimeout(() => {
            ...prev,
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

     

      window.removeEventListener('storage'
      if (syncTimeoutRef.curr
      }
  }, [])
  const markSyncStart = useCallbac
      ...pr
    }))


      isSyncing: false,
      syncError: null

  const markSyncError 
      ...prev,
      syncEr

  return {
    markSyncStart,
    markSyncError
}
function generateDeviceId(): string {
  if (s
  con
  return





















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

  const id = `device-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  localStorage.setItem('stellar-device-id', id)
  return id
}
