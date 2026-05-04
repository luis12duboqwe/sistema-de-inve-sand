import { useCallback, useEffect, useState } from 'react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { AIStatusResponse } from '@/lib/types'
import { useKV } from './use-kv'

interface UseAIStatusResult {
  status: AIStatusResponse | null
  isLoading: boolean
  error: string | null
  lastFetchedAt: string | null
  refresh: () => Promise<void>
  isApiMode: boolean
}

export function useAIStatus(autoRefreshMs: number = 0, enabled: boolean = true): UseAIStatusResult {
  const [status, setStatus] = useState<AIStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastFetchedAt, setLastFetchedAt] = useState<string | null>(null)
  const [useAPI] = useKV<boolean>('settings_use_api', false)

  const refresh = useCallback(async () => {
    if (!enabled || !useAPI) {
      setStatus(null)
      setError(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    try {
      const data = await inventoryServiceInstance.getAIStatus()
      setStatus(data)
      setLastFetchedAt(new Date().toISOString())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setIsLoading(false)
    }
  }, [enabled, useAPI])

  useEffect(() => {
    if (!enabled) {
      setStatus(null)
      setError(null)
      setIsLoading(false)
      return
    }
    refresh()
  }, [useAPI, enabled, refresh])

  useEffect(() => {
    if (!enabled || !autoRefreshMs || autoRefreshMs <= 0) {
      return
    }

    const id = setInterval(() => {
      refresh().catch(() => null)
    }, autoRefreshMs)

    return () => clearInterval(id)
  }, [autoRefreshMs, refresh, useAPI, enabled])

  return {
    status,
    isLoading,
    error,
    lastFetchedAt,
    refresh,
    isApiMode: Boolean(useAPI),
  }
}
