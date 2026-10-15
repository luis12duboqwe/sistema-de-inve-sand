import { describe, expect, it, vi } from 'vitest'
import { submitTransferRequestsSequentially } from '../transferBatchSubmission'

describe('transfer batch uncertain responses', () => {
  it('stops on the first uncertain response without duplicating confirmed rows', async () => {
    const create = vi.fn()
      .mockResolvedValueOnce({ id: 100 })
      .mockRejectedValueOnce(new Error('response lost'))
    const result = await submitTransferRequestsSequentially([1, 2, 3], create)
    expect(create).toHaveBeenCalledTimes(2)
    expect(result.confirmed).toEqual([{ request: 1, result: { id: 100 } }])
    expect(result.failure).toMatchObject({ index: 1, request: 2 })
  })

  it('reports each confirmed transfer as a distinct pending request', async () => {
    const create = vi.fn(async (value: number) => ({ id: value + 20 }))
    const result = await submitTransferRequestsSequentially([1, 2], create)
    expect(result.failure).toBeUndefined()
    expect(result.confirmed.map(x => x.result.id)).toEqual([21, 22])
  })
})
