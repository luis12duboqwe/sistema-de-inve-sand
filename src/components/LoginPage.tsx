import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { Sparkle } from '@phosphor-icons/react'
import { apiClient } from '@/lib/apiClient'
import type { User } from '@/lib/types'

interface LoginPageProps {
  onLoginSuccess: (user: User, token: string) => void
}

export function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await apiClient.login(username, password)
      if (response.user) {
        onLoginSuccess(response.user, response.access_token)
        toast.success(`Bienvenido, ${response.user.full_name || response.user.username}`)
      } else {
        throw new Error('No user data received')
      }
    } catch (error) {
      console.error('Login error:', error)
      toast.error('Error al iniciar sesión. Verifique sus credenciales.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-lg border bg-card text-card-foreground shadow-sm p-6">
        <div className="text-center mb-6">
          <Sparkle size={40} className="mx-auto text-primary mb-3" weight="duotone" />
          <h1 className="text-2xl font-bold">Iniciar Sesión</h1>
          <p className="text-sm text-muted-foreground mt-1">Ingrese sus credenciales para continuar</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="login-username">Usuario</Label>
            <Input
              id="login-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="login-password">Contraseña</Label>
            <Input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Ingresando...' : 'Ingresar'}
          </Button>
        </form>
      </div>
    </div>
  )
}
