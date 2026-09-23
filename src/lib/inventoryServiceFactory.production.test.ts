import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiClientMock = vi.hoisted(() => ({
  fetchProducts: vi.fn(),
}))

const localServiceMock = vi.hoisted(() => ({
  fetchProducts: vi.fn(),
}))

vi.mock('./apiClient', () => ({ apiClient: apiClientMock }))
vi.mock('./inventoryService', () => ({ inventoryService: localServiceMock }))
vi.mock('./kvStorage', () => ({
  getKV: () => {
    throw new Error('simulated service-selection failure')
  },
}))
vi.mock('./runtimePolicy', () => ({
  isProductionApiForced: () => true,
}))

import { inventoryServiceInstance } from './inventoryServiceFactory'

describe('inventoryServiceFactory production fail-closed policy', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClientMock.fetchProducts.mockResolvedValue([])
  })

  it('keeps using the API when service selection fails in production', async () => {
    await inventoryServiceInstance.fetchProducts(undefined, undefined, true)

    expect(apiClientMock.fetchProducts).toHaveBeenCalledWith(undefined, undefined, true)
    expect(localServiceMock.fetchProducts).not.toHaveBeenCalled()
  })
})
