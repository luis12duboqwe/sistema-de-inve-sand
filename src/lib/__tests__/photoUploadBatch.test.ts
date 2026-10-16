import { describe, expect, it, vi } from 'vitest'
import { uploadPhotosSequentially } from '../photoUploadBatch'
describe('safe photo upload batches', () => {
  it('stops on uncertain network response and never uploads remaining files', async () => {
    const first = vi.fn().mockResolvedValue({ id: 10 })
    const second = vi.fn().mockRejectedValue(new Error('response lost'))
    const third = vi.fn().mockResolvedValue({ id: 12 })
    const result = await uploadPhotosSequentially([first, second, third])
    expect(result.confirmed).toBe(1)
    expect(result.failure).toBeInstanceOf(Error)
    expect(first).toHaveBeenCalledTimes(1)
    expect(second).toHaveBeenCalledTimes(1)
    expect(third).not.toHaveBeenCalled()
  })
  it('reports completed uploads without falsely claiming delivery', async () => {
    const result = await uploadPhotosSequentially([async () => 1, async () => 2])
    expect(result).toEqual({ confirmed: 2 })
  })
})
