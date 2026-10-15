import { describe, expect, it, vi } from 'vitest'
import { loadAllPages } from '../pagination'

describe('full transfer pagination', () => {
  it('does not stop after the backend first page', async () => {
    const page = vi.fn()
      .mockResolvedValueOnce({ items: [1,2], pages: 3 })
      .mockResolvedValueOnce({ items: [3,4], pages: 3 })
      .mockResolvedValueOnce({ items: [5], pages: 3 })
    expect(await loadAllPages<number>(page)).toEqual([1,2,3,4,5])
    expect(page).toHaveBeenCalledTimes(3)
  })
  it('rejects bounded truncation rather than displaying misleading results', async () => {
    const page = vi.fn().mockResolvedValue({ items: [1], pages: 4 })
    await expect(loadAllPages<number>(page, 2)).rejects.toThrow('Exceeded 2')
  })
})
