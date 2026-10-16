import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CustomizeShortcutsDialog } from '../CustomizeShortcutsDialog'

vi.mock('@/hooks/use-kv', () => ({ useKV: () => [{}, vi.fn()] }))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

describe('shortcut recorder cleanup', () => {
  it('releases the global keydown handler when recording is canceled', async () => {
    const user = userEvent.setup()
    render(<CustomizeShortcutsDialog open onOpenChange={vi.fn()} />)
    await user.click(screen.getAllByTitle('Editar atajo')[0])

    const captured = new KeyboardEvent('keydown', { key: 'x', bubbles: true, cancelable: true })
    fireEvent(window, captured)
    expect(captured.defaultPrevented).toBe(true)

    await user.click(screen.getByTitle('Cancelar'))
    const afterwards = new KeyboardEvent('keydown', { key: 'y', bubbles: true, cancelable: true })
    fireEvent(window, afterwards)
    expect(afterwards.defaultPrevented).toBe(false)
  })
})
