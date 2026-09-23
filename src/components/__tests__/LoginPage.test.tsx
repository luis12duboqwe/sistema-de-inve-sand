import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LoginPage } from '../LoginPage'
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

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('authenticates and passes the user and access token to App', async () => {
    const browserUser = userEvent.setup()
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

    render(<LoginPage onLoginSuccess={onLoginSuccess} />)

    await browserUser.type(screen.getByLabelText('Usuario'), 'admin')
    await browserUser.type(screen.getByLabelText('Contraseña'), 'StrongPass!2026')
    await browserUser.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(apiClient.login).toHaveBeenCalledWith('admin', 'StrongPass!2026')
      expect(onLoginSuccess).toHaveBeenCalledWith(authenticatedUser, 'token-123')
    })
    expect(toast.success).toHaveBeenCalledWith('Bienvenido, Administrador')
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('does not enter the application when authentication fails', async () => {
    const browserUser = userEvent.setup()
    const onLoginSuccess = vi.fn()
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(apiClient.login).mockRejectedValue(new Error('Unauthorized'))

    render(<LoginPage onLoginSuccess={onLoginSuccess} />)

    await browserUser.type(screen.getByLabelText('Usuario'), 'admin')
    await browserUser.type(screen.getByLabelText('Contraseña'), 'incorrecta')
    await browserUser.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al iniciar sesión. Verifique sus credenciales.')
    })
    expect(onLoginSuccess).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeEnabled()

    consoleSpy.mockRestore()
  })
})
