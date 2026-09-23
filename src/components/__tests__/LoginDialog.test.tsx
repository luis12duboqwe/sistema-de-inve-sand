import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LoginDialog } from '../LoginDialog'
import { apiClient } from '@/lib/apiClient'
import { toast } from 'sonner'

vi.mock('@/lib/apiClient', () => ({
  apiClient: {
    login: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('LoginDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('submits credentials and hands the authenticated user/token to the app', async () => {
    const user = userEvent.setup()
    const onLoginSuccess = vi.fn()
    const authenticatedUser = {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      full_name: 'Administrador',
      is_active: true,
      is_superuser: true,
      role_id: 1,
    }

    vi.mocked(apiClient.login).mockResolvedValue({
      access_token: 'token-123',
      token_type: 'bearer',
      user: authenticatedUser,
    } as Awaited<ReturnType<typeof apiClient.login>>)

    render(<LoginDialog open onLoginSuccess={onLoginSuccess} />)

    await user.type(screen.getByLabelText('Usuario'), 'admin')
    await user.type(screen.getByLabelText('Contraseña'), 'StrongPass!2026')
    await user.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(apiClient.login).toHaveBeenCalledWith('admin', 'StrongPass!2026')
      expect(onLoginSuccess).toHaveBeenCalledWith(authenticatedUser, 'token-123')
    })
    expect(toast.success).toHaveBeenCalledWith('Bienvenido, Administrador')
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('keeps the user logged out and reports invalid credentials on login failure', async () => {
    const user = userEvent.setup()
    const onLoginSuccess = vi.fn()
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(apiClient.login).mockRejectedValue(new Error('Unauthorized'))

    render(<LoginDialog open onLoginSuccess={onLoginSuccess} />)

    await user.type(screen.getByLabelText('Usuario'), 'admin')
    await user.type(screen.getByLabelText('Contraseña'), 'incorrecta')
    await user.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al iniciar sesión. Verifique sus credenciales.')
    })
    expect(onLoginSuccess).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeEnabled()

    consoleSpy.mockRestore()
  })
})
