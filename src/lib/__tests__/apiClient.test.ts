import { describe, it, expect, vi } from 'vitest'
import { apiClient } from '../apiClient'

// MSW handlers are configured in global setup

describe('apiClient with MSW', () => {
  it('fetches orders successfully', async () => {
    const orders = await apiClient.fetchOrders()
    expect(orders.length).toBeGreaterThan(0)
    expect(orders[0].customer_name).toBe('Test')
  })

  it('throws on invalid stock transfer payload', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    await expect(apiClient.createStockTransfer({} as any)).rejects.toThrow()
    errorSpy.mockRestore()
  })
})
