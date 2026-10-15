import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Calendar } from '../ui/calendar'

describe('calendar month navigation', () => {
  it('provides actual keyboard-accessible buttons and changes month', async () => {
    const user = userEvent.setup()
    const onMonthChange = vi.fn()
    render(<Calendar defaultMonth={new Date(2026, 9, 1)} onMonthChange={onMonthChange} />)
    const next = screen.getByRole('button', { name: /next month/i })
    expect(next).not.toBeDisabled()
    await user.click(next)
    expect(onMonthChange).toHaveBeenCalledTimes(1)
    expect(onMonthChange.mock.calls[0][0].getMonth()).toBe(10)
    const previous = screen.getByRole('button', { name: /previous month/i })
    await user.click(previous)
    expect(onMonthChange.mock.calls[1][0].getMonth()).toBe(9)
  })
})
