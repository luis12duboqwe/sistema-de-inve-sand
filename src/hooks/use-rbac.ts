import { useCallback, useEffect, useState } from 'react'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import type { Permission, Role, User, CreateUserRequest } from '@/lib/types'

export type CreateUserPayload = CreateUserRequest

export interface UseRbacResult {
  users: User[]
  roles: Role[]
  permissions: Permission[]
  loading: boolean
  error: string | null
  isForbidden: boolean
  refresh: () => Promise<void>
  createUser: (payload: CreateUserPayload) => Promise<User>
  deleteUser: (userId: number) => Promise<void>
  updateRole: (userId: number, roleId: number) => Promise<User>
  updateUser: (userId: number, updates: Partial<User> & { password?: string; role_id?: number }) => Promise<User>
}

function isPermissionError(error: unknown): error is Error {
  return (
    error instanceof Error &&
    error.message.toLowerCase().includes('permission')
  )
}

export function useRbac(enabled: boolean): UseRbacResult {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isForbidden, setIsForbidden] = useState(false)

  const refresh = useCallback(async () => {
    if (!enabled) {
      setUsers([])
      setRoles([])
      setPermissions([])
      setIsForbidden(false)
      setError(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const [usersData, rolesData, permissionsData] = await Promise.all([
        inventoryServiceInstance.listUsers(),
        inventoryServiceInstance.listRoles(),
        inventoryServiceInstance.listPermissions()
      ])
      setUsers(usersData)
      setRoles(rolesData)
      setPermissions(permissionsData)
      setIsForbidden(false)
    } catch (err) {
      if (isPermissionError(err)) {
        setIsForbidden(true)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Error desconocido al cargar RBAC')
      }
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const createUser = useCallback(async (payload: CreateUserPayload) => {
    const newUser = await inventoryServiceInstance.createUser(payload)
    setUsers(prev => [...prev, newUser])
    return newUser
  }, [])

  const deleteUser = useCallback(async (userId: number) => {
    await inventoryServiceInstance.deleteUser(userId)
    setUsers(prev => prev.filter(user => user.id !== userId))
  }, [])

  const updateRole = useCallback(async (userId: number, roleId: number) => {
    const updated = await inventoryServiceInstance.updateUserRole(userId, roleId)
    setUsers(prev => prev.map(user => (user.id === userId ? updated : user)))
    return updated
  }, [])

  const updateUser = useCallback(async (userId: number, updates: Partial<User> & { password?: string; role_id?: number }) => {
    const updated = await inventoryServiceInstance.updateUser(userId, updates)
    setUsers(prev => prev.map(user => (user.id === userId ? updated : user)))
    return updated
  }, [])

  return {
    users,
    roles,
    permissions,
    loading,
    error,
    isForbidden,
    refresh,
    createUser,
    deleteUser,
    updateRole,
    updateUser
  }
}
