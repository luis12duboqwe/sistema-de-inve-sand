import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { toast } from 'sonner'
import { apiClient } from '@/lib/apiClient'
import { User, Role } from '@/lib/types'
import { Trash, UserPlus, ShieldCheck } from '@phosphor-icons/react'

interface ManageUsersDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ManageUsersDialog({ open, onOpenChange }: ManageUsersDialogProps) {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [_isLoading, setIsLoading] = useState(false)
  const [showNewUserForm, setShowNewUserForm] = useState(false)
  
  // New User Form State
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role_id: ''
  })

  useEffect(() => {
    if (open) {
      loadData()
    }
  }, [open])

  const loadData = async () => {
    setIsLoading(true)
    try {
      const [usersData, rolesData] = await Promise.all([
        apiClient.listUsers(),
        apiClient.listRoles()
      ])
      setUsers(usersData)
      setRoles(rolesData)
    } catch (error) {
      console.error('Error loading users:', error)
      toast.error('Error al cargar usuarios')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await apiClient.createUser({
        ...newUser,
        role_id: parseInt(newUser.role_id)
      })
      toast.success('Usuario creado exitosamente')
      setShowNewUserForm(false)
      setNewUser({ username: '', email: '', full_name: '', password: '', role_id: '' })
      loadData()
    } catch {
      toast.error('Error al crear usuario')
    }
  }

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('¿Está seguro de eliminar este usuario?')) return
    try {
      await apiClient.deleteUser(userId)
      toast.success('Usuario eliminado')
      loadData()
    } catch {
      toast.error('Error al eliminar usuario')
    }
  }

  const handleRoleChange = async (userId: number, roleId: string) => {
    try {
      await apiClient.updateUserRole(userId, parseInt(roleId))
      toast.success('Rol actualizado')
      loadData()
    } catch {
      toast.error('Error al actualizar rol')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px]">
        <DialogHeader>
          <DialogTitle>Gestión de Usuarios y Roles</DialogTitle>
          <DialogDescription>
            Administre los usuarios del sistema y sus niveles de acceso.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {!showNewUserForm ? (
            <div className="space-y-4">
              <div className="flex justify-end">
                <Button onClick={() => setShowNewUserForm(true)}>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Nuevo Usuario
                </Button>
              </div>

              <div className="border rounded-md">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Usuario</TableHead>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Rol</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">{user.username}</TableCell>
                        <TableCell>{user.full_name}</TableCell>
                        <TableCell>{user.email}</TableCell>
                        <TableCell>
                          <Select 
                            defaultValue={user.role_id?.toString()} 
                            onValueChange={(val) => handleRoleChange(user.id, val)}
                            disabled={user.is_superuser} // Prevent changing superuser role easily
                          >
                            <SelectTrigger className="w-[140px]">
                              <SelectValue placeholder="Seleccionar rol" />
                            </SelectTrigger>
                            <SelectContent>
                              {roles.map((role) => (
                                <SelectItem key={role.id} value={role.id.toString()}>
                                  {role.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell className="text-right">
                          {!user.is_superuser && (
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              onClick={() => handleDeleteUser(user.id)}
                              className="text-destructive hover:text-destructive/90"
                            >
                              <Trash className="h-4 w-4" />
                            </Button>
                          )}
                          {user.is_superuser && (
                            <span title="Super Admin">
                              <ShieldCheck className="h-5 w-5 text-primary inline-block ml-2" />
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          ) : (
            <form onSubmit={handleCreateUser} className="space-y-4 border p-4 rounded-md">
              <h3 className="font-medium">Crear Nuevo Usuario</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Usuario</Label>
                  <Input
                    id="username"
                    value={newUser.username}
                    onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="full_name">Nombre Completo</Label>
                  <Input
                    id="full_name"
                    value={newUser.full_name}
                    onChange={(e) => setNewUser({...newUser, full_name: e.target.value})}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={newUser.email}
                    onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Contraseña</Label>
                  <Input
                    id="password"
                    type="password"
                    value={newUser.password}
                    onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                    required
                  />
                </div>
                <div className="space-y-2 col-span-2">
                  <Label htmlFor="role">Rol</Label>
                  <Select 
                    value={newUser.role_id} 
                    onValueChange={(val) => setNewUser({...newUser, role_id: val})}
                    required
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar rol" />
                    </SelectTrigger>
                    <SelectContent>
                      {roles.map((role) => (
                        <SelectItem key={role.id} value={role.id.toString()}>
                          {role.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={() => setShowNewUserForm(false)}>
                  Cancelar
                </Button>
                <Button type="submit">
                  Crear Usuario
                </Button>
              </div>
            </form>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
