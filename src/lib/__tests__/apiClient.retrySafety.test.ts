import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../apiClient'

// A lost response after the server commits a sale must not trigger a second POST.
describe('apiClient retry safety for business mutations', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends a POST only once even when the response is lost', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(
      (apiClient as any).request('/orders', { method: 'POST', body: '{}' }, 3)
    ).rejects.toThrow('No se puede conectar al backend')

    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it('continues to retry safe GET requests after a transient network failure', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    const result = await (apiClient as any).request('/api-readiness', { method: 'GET' }, 2)

    expect(result).toEqual({})
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })
})
