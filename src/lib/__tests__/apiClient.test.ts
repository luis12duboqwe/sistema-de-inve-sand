import { describe, it, expect, vi, afterEach } from 'vitest'
import { apiClient } from '../apiClient'
import type { PaginatedResponse, Permission, Role, User } from '../types'

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

describe('apiClient pagination loops', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('listUsers paginates until reported pages are exhausted', async () => {
    const responses: PaginatedResponse<User>[] = [
      buildPaginatedResponse(createUsers(100, 1), { total: 250, page: 1, per_page: 100, pages: 3 }),
      buildPaginatedResponse(createUsers(100, 101), { total: 250, page: 2, per_page: 100, pages: 3 }),
      buildPaginatedResponse(createUsers(50, 201), { total: 250, page: 3, per_page: 100, pages: 3 })
    ]

    const requestSpy = vi.spyOn(apiClient as any, 'request')
    responses.forEach(response => requestSpy.mockResolvedValueOnce(response))

    const users = await apiClient.listUsers()

    expect(users).toHaveLength(250)
    expect(requestSpy).toHaveBeenCalledTimes(3)
    expect(requestSpy.mock.calls[0][0]).toContain('page=1')
    expect(requestSpy.mock.calls[1][0]).toContain('page=2')
    expect(requestSpy.mock.calls[2][0]).toContain('page=3')
  })

  it('listRoles relies on derived totalPages when API omits pages field', async () => {
    const responses: PaginatedResponse<Role>[] = [
      buildPaginatedResponse(createRoles(100, 1), { total: 150, page: 1, per_page: 100 }),
      buildPaginatedResponse(createRoles(50, 101), { total: 150, page: 2, per_page: 100 })
    ]

    const requestSpy = vi.spyOn(apiClient as any, 'request')
    responses.forEach(response => requestSpy.mockResolvedValueOnce(response))

    const roles = await apiClient.listRoles()

    expect(roles).toHaveLength(150)
    expect(requestSpy).toHaveBeenCalledTimes(2)
  })

  it('listPermissions stops when API returns fewer items than requested even if pages are inflated', async () => {
    const responses: PaginatedResponse<Permission>[] = [
      buildPaginatedResponse(createPermissions(200, 1), {
        total: 400,
        page: 1,
        per_page: 200,
        pages: 99
      }),
      buildPaginatedResponse([], {
        total: 400,
        page: 2,
        per_page: 200,
        pages: 99
      })
    ]

    const requestSpy = vi.spyOn(apiClient as any, 'request')
    responses.forEach(response => requestSpy.mockResolvedValueOnce(response))

    const permissions = await apiClient.listPermissions()

    expect(permissions).toHaveLength(200)
    expect(requestSpy).toHaveBeenCalledTimes(2)
  })
})

function buildPaginatedResponse<T>(
  items: T[],
  overrides: Partial<PaginatedResponse<T>> = {}
): PaginatedResponse<T> {
  return {
    items,
    total: overrides.total ?? items.length,
    page: overrides.page,
    per_page: overrides.per_page,
    pages: overrides.pages
  }
}

function createUsers(count: number, startId = 1): User[] {
  return Array.from({ length: count }, (_, index) => {
    const id = startId + index
    return {
      id,
      username: `user-${id}`,
      email: `user-${id}@example.com`,
      full_name: `User ${id}`,
      is_active: true,
      is_superuser: false,
      role_id: 1
    }
  })
}

function createRoles(count: number, startId = 1): Role[] {
  return Array.from({ length: count }, (_, index) => {
    const id = startId + index
    return {
      id,
      name: `Role ${id}`,
      description: undefined,
      is_system_role: false,
      permissions: []
    }
  })
}

function createPermissions(count: number, startId = 1): Permission[] {
  return Array.from({ length: count }, (_, index) => {
    const id = startId + index
    return {
      id,
      slug: `perm:${id}`,
      module: 'test'
    }
  })
}
