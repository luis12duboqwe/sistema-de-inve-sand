import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { ValidationCodeDialog } from '../ValidationCodeDialog'

describe('ValidationCodeDialog', () => {
  it('does not prompt for the obsolete sale-completion code', async () => {
    const onConfirm = vi.fn()

    render(
      <ValidationCodeDialog
        open
        title="Validar venta"
        description="Flujo legado de completar venta"
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />
    )

    await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1))
    expect(onConfirm).toHaveBeenCalledWith('')
    expect(screen.queryByLabelText('Código de validación')).not.toBeInTheDocument()
  })

  it('keeps requiring a code for normal protected operations', async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()

    render(
      <ValidationCodeDialog
        open
        title="Confirmar transferencia"
        description="Ingrese el código autorizado"
        confirmLabel="Validar"
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />
    )

    expect(onConfirm).not.toHaveBeenCalled()
    const input = screen.getByLabelText('Código de validación')
    await user.type(input, ' 1234 ')
    await user.click(screen.getByRole('button', { name: 'Validar' }))

    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(onConfirm).toHaveBeenCalledWith('1234')
  })
})
