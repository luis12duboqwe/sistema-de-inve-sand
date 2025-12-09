import { useEffect, useCallback } from 'react'
import { useKV } from './use-kv'
import type { ProductWithStock, OrderWithItems, Profile } from '@/lib/types'
import { calculateOptimizationScore } from '@/lib/optimizationAnalytics'

export interface OptimizationScoreHistory {
  timestamp: number
  score: number
  profileId: number | null
}

export interface OptimizationAlertSettings {
  enabled: boolean
  threshold: number
  checkIntervalMinutes: number
}

export interface OptimizationAlert {
  id: string
  profileId: number | null
  profileName: string
  score: number
  threshold: number
  previousScore: number | null
  trend: 'declining' | 'stable' | 'improving'
  timestamp: number
}

const DEFAULT_SETTINGS: OptimizationAlertSettings = {
  enabled: true,
  threshold: 70,
  checkIntervalMinutes: 5
}

export function useOptimizationAlerts(
  products: ProductWithStock[],
  orders: OrderWithItems[],
  profile: Profile | null
) {
  const [settings, setSettings] = useKV<OptimizationAlertSettings>(
    'optimization-alert-settings',
    DEFAULT_SETTINGS
  )
  const [scoreHistory, setScoreHistory] = useKV<OptimizationScoreHistory[]>(
    'optimization-score-history',
    []
  )
  const [alerts, setAlerts] = useKV<OptimizationAlert[]>(
    'optimization-alerts',
    []
  )
  const [lastCheckTimestamp, setLastCheckTimestamp] = useKV<number>(
    'optimization-last-check',
    0
  )

  // V2.0: Products are global, Orders filter by sales_profile_id
  const profileProducts = products.filter(p => p.activo)
  const profileOrders = orders.filter(o => 
    !profile || o.sales_profile_id === profile.id
  )

  const checkOptimizationScore = useCallback(() => {
    if (!(settings?.enabled)) return
    if (profileProducts.length === 0) return

    const now = Date.now()
    const lastCheck = lastCheckTimestamp ?? 0
    const intervalMs = (settings?.checkIntervalMinutes ?? 5) * 60 * 1000

    if (now - lastCheck < intervalMs) return

    const currentScore = calculateOptimizationScore(profileProducts, profileOrders)
    const profileId = profile?.id ?? null
    const profileName = profile?.name ?? 'Todos los perfiles'

    const recentHistory = (scoreHistory ?? [])
      .filter(h => h.profileId === profileId)
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, 10)

    const previousScore = recentHistory.length > 0 ? recentHistory[0].score : null

    setScoreHistory(current => [
      {
        timestamp: now,
        score: currentScore,
        profileId
      },
      ...(current ?? [])
    ].slice(0, 100))

    setLastCheckTimestamp(now)

    const threshold = settings?.threshold ?? 70
    if (currentScore < threshold) {
      let trend: 'declining' | 'stable' | 'improving' = 'stable'
      
      if (previousScore !== null) {
        if (currentScore < previousScore - 2) {
          trend = 'declining'
        } else if (currentScore > previousScore + 2) {
          trend = 'improving'
        }
      }

      const alertId = `opt-${profileId}-${Math.floor(now / (60 * 60 * 1000))}`
      
      const existingAlert = (alerts ?? []).find(a => a.id === alertId)
      
      if (!existingAlert) {
        const newAlert: OptimizationAlert = {
          id: alertId,
          profileId,
          profileName,
          score: currentScore,
          threshold,
          previousScore,
          trend,
          timestamp: now
        }

        setAlerts(current => [newAlert, ...(current ?? [])].slice(0, 50))
      }
    } else {
      const alertId = `opt-${profileId}-${Math.floor(now / (60 * 60 * 1000))}`
      setAlerts(current => (current ?? []).filter(a => a.id !== alertId))
    }
  }, [settings?.enabled, profileProducts, profileOrders, lastCheckTimestamp, profile?.id, profile?.name, settings?.checkIntervalMinutes, settings?.threshold, scoreHistory, setScoreHistory, setLastCheckTimestamp, setAlerts, alerts])

  useEffect(() => {
    if (!(settings?.enabled)) return

    checkOptimizationScore()

    const interval = setInterval(
      checkOptimizationScore,
      (settings?.checkIntervalMinutes ?? 5) * 60 * 1000
    )

    return () => clearInterval(interval)
  }, [
    products,
    orders,
    profile?.id,
    settings?.enabled,
    settings?.threshold,
    settings?.checkIntervalMinutes
    // checkOptimizationScore removed to prevent infinite loop
  ])

  const updateSettings = (newSettings: Partial<OptimizationAlertSettings>) => {
    setSettings(current => ({ ...(current ?? DEFAULT_SETTINGS), ...newSettings }))
  }

  const dismissAlert = (alertId: string) => {
    setAlerts(current => (current ?? []).filter(a => a.id !== alertId))
  }

  const clearAllAlerts = () => {
    setAlerts([])
  }

  const getScoreTrend = (lookbackCount: number = 5): 'improving' | 'declining' | 'stable' => {
    const profileId = profile?.id ?? null
    const recentScores = (scoreHistory ?? [])
      .filter(h => h.profileId === profileId)
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, lookbackCount)
      .map(h => h.score)

    if (recentScores.length < 2) return 'stable'

    const avgRecent = recentScores.slice(0, Math.ceil(lookbackCount / 2)).reduce((a, b) => a + b, 0) / Math.ceil(lookbackCount / 2)
    const avgOlder = recentScores.slice(Math.ceil(lookbackCount / 2)).reduce((a, b) => a + b, 0) / Math.floor(lookbackCount / 2)

    if (avgRecent > avgOlder + 3) return 'improving'
    if (avgRecent < avgOlder - 3) return 'declining'
    return 'stable'
  }

  const getCurrentScore = (): number => {
    return calculateOptimizationScore(profileProducts, profileOrders)
  }

  return {
    settings: settings ?? DEFAULT_SETTINGS,
    updateSettings,
    alerts: alerts ?? [],
    dismissAlert,
    clearAllAlerts,
    scoreHistory: scoreHistory ?? [],
    checkOptimizationScore,
    getScoreTrend,
    getCurrentScore
  }
}
