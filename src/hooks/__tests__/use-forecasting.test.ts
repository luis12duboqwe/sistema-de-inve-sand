import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useForecasting } from '../use-forecasting'

const mockInventoryService = vi.hoisted(() => ({
  getForecasting: vi.fn(async () => ([{ productId: 1, urgency: 'high' }]))
}))

vi.mock('@/hooks/use-kv', async () => {
  const React = await import('react')
  return {
    useKV: <T,>(key: string, initial: T) => React.useState<T>(initial)
  }
})

vi.mock('@/lib/inventoryServiceFactory', () => ({
  inventoryServiceInstance: mockInventoryService
}))

vi.mock('@/lib/aiForecasting', () => ({
  generateForecastingSummary: vi.fn(() => ({ totalDemand: 10 })),
  generateRestockAlerts: vi.fn(async () => ([{ id: '1', productId: 1, urgency: 'high' }]))
}))

describe('useForecasting hook', () => {
  it('generates forecasts and alerts', async () => {
    const products = [{ id: 1, nombre: 'P', categoria: 'accesorio', marca: 'M', modelo: 'X', condicion: 'nuevo', precio: 100, moneda: 'HNL', garantia_meses: 12, activo: true, sku: 'SKU', stock_disponible: 5 }]
    const orders: any[] = [{ id: 1, created_at: new Date().toISOString(), estado: 'completada', items: [] }]
    const profile = { id: 1, name: 'Demo', slug: 'demo', active: true }

    const { result } = renderHook(() => useForecasting(products as any, orders as any, profile as any, false))

    await act(async () => {
      await result.current.generateForecastData()
    })

    expect(result.current.forecasts.length).toBe(1)
    expect(result.current.alerts.length).toBe(1)
    expect(result.current.summary).toEqual({ totalDemand: 10 })
  })
})
