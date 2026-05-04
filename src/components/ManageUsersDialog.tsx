import { Fragment, useEffect, useMemo, useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { RoleSelect } from '@/components/forms/RoleSelect'
import { useKV } from '@/hooks/use-kv'
import { useRbac, type CreateUserPayload } from '@/hooks/use-rbac'
import type { Permission, User } from '@/lib/types'
import { ArrowClockwise, Key, LockSimple, MagnifyingGlass, ShieldCheck, ShieldSlash, Trash, UserPlus, Wrench } from '@phosphor-icons/react'

interface ManageUsersDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface PasswordEditorState {
  user: User
  password: string
  confirm: string
}

export function ManageUsersDialog({ open, onOpenChange }: ManageUsersDialogProps) {
  const [useApiMode] = useKV<boolean>('settings_use_api', false)
  const featureEnabled = open
  const { users, roles, permissions, loading, error, isForbidden, refresh, createUser, deleteUser, updateRole, updateUser } = useRbac(featureEnabled)
  const [filter, setFilter] = useState('')
  const [showNewUserForm, setShowNewUserForm] = useState(false)
  const [passwordEditor, setPasswordEditor] = useState<PasswordEditorState | null>(null)
  const [creatingUser, setCreatingUser] = useState(false)
  const [pendingUser, setPendingUser] = useState<CreateUserPayload>({ username: '', email: '', full_name: '', password: '', role_id: 0 })
  const [currentUserId, setCurrentUserId] = useState<number | null>(null)

  useEffect(() => {
    if (!open) return
    const stored = localStorage.getItem('auth_user')
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as Partial<User>
        if (parsed?.id) {
          setCurrentUserId(parsed.id)
        }
      } catch (err) {
        console.warn('No se pudo parsear auth_user', err)
      }
    }
  }, [open])

  const filteredUsers = useMemo(() => {
    if (!filter.trim()) return users
    return users.filter(user => {
      const haystack = `${user.username} ${user.email ?? ''} ${user.full_name ?? ''}`.toLowerCase()
      return haystack.includes(filter.toLowerCase())
    })
  }, [users, filter])

  const permissionsByModule = useMemo(() => {
    return permissions.reduce<Record<string, Permission[]>>((acc, permission) => {
      if (!acc[permission.module]) acc[permission.module] = []
      acc[permission.module].push(permission)
      return acc
    }, {})
  }, [permissions])

  const handleCreateUser = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!pendingUser.role_id) {
      toast.error('Selecciona un rol para el nuevo usuario')
      return
    }
    if ((pendingUser.password || "").length < 6) {
      toast.error('La contraseña debe tener al menos 6 caracteres')
      return
    }
    setCreatingUser(true)
    try {
      await createUser(pendingUser)
      toast.success('Usuario creado correctamente')
      setPendingUser({ username: '', email: '', full_name: '', password: '', role_id: 0 })
      setShowNewUserForm(false)
    } catch (err) {
      console.error('Error creando usuario', err)
      toast.error(err instanceof Error ? err.message : 'No se pudo crear el usuario')
    } finally {
      setCreatingUser(false)
    }
  }

  const handleDeleteUser = async (user: User) => {
    if (user.is_superuser) {
      toast.error('No puedes eliminar un Super Admin')
      return
    }
    if (!confirm(`¿Eliminar la cuenta ${user.username}?`)) return
    try {
      await deleteUser(user.id)
      toast.success('Usuario eliminado')
    } catch (err) {
      console.error('Error eliminando usuario', err)
      toast.error(err instanceof Error ? err.message : 'No se pudo eliminar el usuario')
    }
  }

  const handleRoleChange = async (user: User, roleId: number) => {
    try {
      await updateRole(user.id, roleId)
      toast.success('Rol actualizado')
    } catch (err) {
      console.error('Error actualizando rol', err)
      toast.error(err instanceof Error ? err.message : 'No se pudo actualizar el rol')
    }
  }

  const handleToggleActive = async (user: User, nextState: boolean) => {
    if (currentUserId === user.id && !nextState) {
      toast.error('No puedes desactivar tu propia cuenta')
      return
    }
    try {
      await updateUser(user.id, { is_active: nextState })
      toast.success(`Usuario ${nextState ? 'activado' : 'desactivado'}`)
    } catch (err) {
      console.error('Error actualizando estado', err)
      toast.error(err instanceof Error ? err.message : 'No se pudo actualizar el estado')
    }
  }

  const handleRepairRbac = async () => {
    try {
      await refresh()
      toast.success('RBAC reparado y sincronizado correctamente')
    } catch (err) {
      console.error('Error reparando RBAC', err)
      toast.error(err instanceof Error ? err.message : 'No se pudo reparar RBAC')
    }
  }

  const openPasswordEditor = (user: User) => {
    setPasswordEditor({ user, password: '', confirm: '' })
  }

  const handlePasswordSave = async () => {
    if (!passwordEditor) return
    if (passwordEditor.password.length < 6) {
      toast.error('La nueva contraseña debe tener al menos 6 caracteres')
      return
    }
    if (passwordEditor.password !== passwordEditor.confirm) {
      toast.error('Las contraseñas no coinciden')
      return
    }
    try {
      await updateUser(passwordEditor.user.id, { password: passwordEditor.password })
      toast.success('Contraseña actualizada')
      setPasswordEditor(null)
    } catch (err) {
      console.error('Error actualizando contraseña', err)
      toast.error(err instanceof Error ? err.message : 'No se pudo actualizar la contraseña')
    }
  }

  const resetPasswordEditor = () => setPasswordEditor(null)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full max-w-[1100px]">
        <DialogHeader>
          <DialogTitle>Consola RBAC</DialogTitle>
          <DialogDescription>
            Gestiona usuarios, roles y permisos del sistema. En modo local los cambios se guardan en Spark KV y se sincronizan con el backend cuando esté disponible.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {!useApiMode && (
            <Alert>
              <AlertTitle>Modo local activo</AlertTitle>
              <AlertDescription>
                Los cambios se almacenan en tu navegador hasta que el backend API esté disponible. Úsalo para preparar roles y usuarios sin conexión.
              </AlertDescription>
            </Alert>
          )}

          {isForbidden && (
            <Alert variant="destructive">
              <ShieldSlash className="h-5 w-5" />
              <AlertTitle>Permiso insuficiente</AlertTitle>
              <AlertDescription>
                Tu cuenta no cuenta con el permiso <strong>users:manage</strong>. Pide a un administrador que te conceda acceso.
              </AlertDescription>
            </Alert>
          )}

          {error && !isForbidden && (
            <Alert>
              <AlertTitle>No se pudo cargar RBAC</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col gap-4 lg:flex-row">
            <div className="flex-1 space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => refresh()} disabled={!featureEnabled || loading}>
                    <ArrowClockwise className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    Actualizar
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRepairRbac}
                    disabled={!featureEnabled || loading || isForbidden}
                  >
                    <Wrench className="mr-2 h-4 w-4" />
                    Reparar RBAC
                  </Button>
                  <Button size="sm" onClick={() => setShowNewUserForm((prev) => !prev)} disabled={!featureEnabled || isForbidden}>
                    <UserPlus className="mr-2 h-4 w-4" />
                    {showNewUserForm ? 'Cerrar formulario' : 'Nuevo usuario'}
                  </Button>
                </div>
                <div className="relative">
                  <MagnifyingGlass className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    className="pl-9"
                    placeholder="Buscar por usuario, email o nombre"
                    value={filter}
                    onChange={(event) => setFilter(event.target.value)}
                    disabled={!featureEnabled}
                  />
                </div>
              </div>

              {showNewUserForm && (
                <form onSubmit={handleCreateUser} className="space-y-4 rounded-lg border p-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Usuario</Label>
                      <Input
                        value={pendingUser.username}
                        onChange={(event) => setPendingUser((prev) => ({ ...prev, username: event.target.value }))}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Nombre completo</Label>
                      <Input
                        value={pendingUser.full_name ?? ''}
                        onChange={(event) => setPendingUser((prev) => ({ ...prev, full_name: event.target.value }))}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Email</Label>
                      <Input
                        type="email"
                        value={pendingUser.email ?? ''}
                        onChange={(event) => setPendingUser((prev) => ({ ...prev, email: event.target.value }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Contraseña</Label>
                      <Input
                        type="password"
                        value={pendingUser.password}
                        onChange={(event) => setPendingUser((prev) => ({ ...prev, password: event.target.value }))}
                        required
                      />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label>Rol asignado</Label>
                      <RoleSelect
                        roles={roles}
                        value={pendingUser.role_id || undefined}
                        onChange={(roleId) => setPendingUser((prev) => ({ ...prev, role_id: roleId }))}
                        disabled={!featureEnabled || isForbidden}
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="ghost" onClick={() => setShowNewUserForm(false)}>
                      Cancelar
                    </Button>
                    <Button type="submit" disabled={creatingUser || !featureEnabled || isForbidden}>
                      {creatingUser ? 'Guardando…' : 'Crear usuario'}
                    </Button>
                  </div>
                </form>
              )}

              <div className="rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Usuario</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Rol</TableHead>
                      <TableHead>Creado</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredUsers.map((user) => (
                      <Fragment key={user.id}>
                        <TableRow>
                          <TableCell>
                            <div className="flex flex-col">
                              <span className="font-semibold">{user.username}</span>
                              <span className="text-xs text-muted-foreground">{user.email || 'Sin email'}</span>
                              {user.is_superuser && (
                                <span className="mt-1 inline-flex items-center gap-1 text-xs text-primary">
                                  <ShieldCheck className="h-3.5 w-3.5" /> Super Admin
                                </span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={user.is_active}
                                onCheckedChange={(checked) => handleToggleActive(user, checked)}
                                disabled={!featureEnabled || isForbidden || user.is_superuser}
                              />
                              <Badge variant={user.is_active ? 'default' : 'secondary'}>
                                {user.is_active ? 'Activo' : 'Inactivo'}
                              </Badge>
                            </div>
                          </TableCell>
                          <TableCell>
                            <RoleSelect
                              roles={roles}
                              value={user.role_id}
                              onChange={(roleId) => handleRoleChange(user, roleId)}
                              disabled={!featureEnabled || isForbidden || user.is_superuser}
                            />
                          </TableCell>
                          <TableCell>
                            <span className="text-sm text-muted-foreground">
                              {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
                            </span>
                          </TableCell>
                          <TableCell className="flex items-center justify-end gap-2">
                            <Button
                              variant="secondary"
                              size="icon"
                              onClick={() => openPasswordEditor(user)}
                              disabled={!featureEnabled || isForbidden}
                              title="Restablecer contraseña"
                            >
                              <Key className="h-4 w-4" />
                            </Button>
                            {!user.is_superuser && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-destructive"
                                onClick={() => handleDeleteUser(user)}
                                disabled={!featureEnabled || isForbidden}
                              >
                                <Trash className="h-4 w-4" />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                        {passwordEditor?.user.id === user.id && (
                          <TableRow>
                            <TableCell colSpan={5}>
                              <div className="grid gap-4 rounded-md bg-muted/40 p-4 sm:grid-cols-2">
                                <div className="space-y-2">
                                  <Label>Nueva contraseña</Label>
                                  <Input
                                    type="password"
                                    value={passwordEditor.password}
                                    onChange={(event) => setPasswordEditor((prev) => prev ? { ...prev, password: event.target.value } : prev)}
                                  />
                                </div>
                                <div className="space-y-2">
                                  <Label>Confirmar contraseña</Label>
                                  <Input
                                    type="password"
                                    value={passwordEditor.confirm}
                                    onChange={(event) => setPasswordEditor((prev) => prev ? { ...prev, confirm: event.target.value } : prev)}
                                  />
                                </div>
                                <div className="flex gap-2 sm:col-span-2">
                                  <Button type="button" variant="ghost" onClick={resetPasswordEditor}>
                                    Cancelar
                                  </Button>
                                  <Button type="button" onClick={handlePasswordSave}>
                                    <LockSimple className="mr-2 h-4 w-4" /> Guardar contraseña
                                  </Button>
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    ))}
                    {!filteredUsers.length && (
                      <TableRow>
                        <TableCell colSpan={5} className="py-6 text-center text-sm text-muted-foreground">
                          {loading ? 'Cargando usuarios…' : 'No hay usuarios que coincidan con la búsqueda.'}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>

            <div className="w-full space-y-4 lg:w-80">
              <div className="rounded-lg border p-4">
                <h3 className="font-semibold">Resumen</h3>
                <p className="text-sm text-muted-foreground">{users.length} usuarios · {roles.length} roles · {permissions.length} permisos</p>
                <Separator className="my-3" />
                <div className="space-y-3">
                  {Object.entries(permissionsByModule).map(([module, modulePermissions]) => (
                    <div key={module}>
                      <p className="text-sm font-medium capitalize">{module}</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {modulePermissions.map((permission) => (
                          <Badge key={permission.id} variant="outline" className="text-xs">
                            {permission.slug}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                  {!permissions.length && (
                    <p className="text-sm text-muted-foreground">
                      Sin información de permisos todavía. Usa el botón "Actualizar" cuando haya conexión o tras inicializar el modo local.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
