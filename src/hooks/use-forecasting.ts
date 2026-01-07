import { useState, useEffect, useCallback } from 'react'
import { useKV } from './use-kv'
import { ProductWithStock, OrderWithItems, Profile } from '@/lib/types'
import { generateRestockAlerts, generateForecastingSummary, SalesForecast, RestockAlert, ForecastingSummary } from '@/lib/aiForecasting'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'

export function useForecasting(
  products: ProductWithStock[],
  orders: OrderWithItems[],
  profile: Profile | null,
  autoRefresh = false
) {
  const [forecasts, setForecasts] = useKV<SalesForecast[]>('forecasting_data', [])
  const [alerts, setAlerts] = useKV<RestockAlert[]>('forecasting_alerts', [])
  const [summary, setSummary] = useKV<ForecastingSummary | null>('forecasting_summary', null)
  const [lastUpdated, setLastUpdated] = useKV<string | null>('forecasting_last_updated', null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [useAPI] = useKV<boolean>('settings_use_api', false)

  const generateForecastData = useCallback(async () => {
    if (!profile || products.length === 0) return
    if (!useAPI && orders.length === 0) return

    setIsGenerating(true)
    try {
      const newForecasts: SalesForecast[] = await inventoryServiceInstance.getForecasting()
      const newSummary: ForecastingSummary = generateForecastingSummary(newForecasts, products)

      const newAlerts = await generateRestockAlerts(newForecasts, profile)

      setForecasts(newForecasts)
      setSummary(newSummary)
      setAlerts(newAlerts)
      setLastUpdated(new Date().toISOString())

      return { forecasts: newForecasts, alerts: newAlerts, summary: newSummary }
    } catch (error) {
      console.error('Error generating forecasts:', error)
      throw error
    } finally {
      setIsGenerating(false)
    }
  }, [products, orders, profile, setForecasts, setSummary, setAlerts, setLastUpdated, useAPI])

  useEffect(() => {
    if (autoRefresh && profile && products.length > 0) {
      const shouldRefresh = !lastUpdated || 
        (new Date().getTime() - new Date(lastUpdated).getTime()) > 24 * 60 * 60 * 1000

      if (shouldRefresh) {
        generateForecastData()
      }
    }
  }, [autoRefresh, profile, products.length, lastUpdated, generateForecastData])

  const getCriticalAlerts = useCallback(() => {
    return (alerts ?? []).filter((a) => a.urgency === 'critical' || a.urgency === 'high')
  }, [alerts])

  const getProductForecast = useCallback(
    (productId: number) => {
      return (forecasts ?? []).find((f) => f.productId === productId)
    },
    [forecasts]
  )

  const needsUpdate = useCallback(() => {
    if (!lastUpdated) return true
    const hoursSinceUpdate = (new Date().getTime() - new Date(lastUpdated).getTime()) / (1000 * 60 * 60)
    return hoursSinceUpdate > 24
  }, [lastUpdated])

  return {
    forecasts: forecasts ?? [],
    alerts: alerts ?? [],
    summary,
    lastUpdated,
    isGenerating,
    generateForecastData,
    getCriticalAlerts,
    getProductForecast,
    needsUpdate,
  }
}
