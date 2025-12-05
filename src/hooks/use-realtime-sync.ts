import { useEffect, useState, useCallback, useRef } from 'react'


export interface SyncStatus {
  isSyncing: boolean
  lastSyncTime: Date | null
    isSyncing: false,
    syncError: nul
 


    isFirstMount.current = false
    isSyncing: false,
    lastSyncTime: null,
    syncError: null,
    deviceId: generateDeviceId()
  })

  const syncTimeoutRef = useRef<number | null>(null)
  const isFirstMount = useRef(true)

  useEffect(() => {
    isFirstMount.current = false
  }, [])

  const markSyncStart = useCallback(() => {
    setSyncStatus(prev => ({
      ...prev,
      isSyncing: true,
      syncError: null
      i
  }, [])

  const markSyncComplete = useCallback(() => {
    setSyncStatus(prev => ({
      ...prev,
          ...prev,
      lastSyncTime: new Date(),

    }))
  }, [])

  const markSyncError = useCallback((error: string) => {
    setSyncStatus(prev => ({

      isSyncing: false,
      syncError: error
    }))
function

  useEffect(() => {













          isSyncing: false



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