import { describe, expect, it, vi } from 'vitest'
import { updateOrderStatusWithoutDailyClose } from '../orderStatusActions'

describe('updateOrderStatusWithoutDailyClose', () => {
  it('submits only order id and status for ordinary completion', async () => {
    const updateOrderStatus = vi.fn(async (orderId: number, status: string) => ({ id: orderId, estado: status }))
    const service = { updateOrderStatus }

    const result = await updateOrderStatusWithoutDailyClose(service, 42, 'completada')

    expect(result).toEqual({ id: 42, estado: 'completada' })
    expect(updateOrderStatus).toHaveBeenCalledTimes(1)
    expect(updateOrderStatus).toHaveBeenCalledWith(42, 'completada')
    expect(updateOrderStatus.mock.calls[0]).toHaveLength(2)
  })

  it('preserves non-completion status transitions without credentials', async () => {
    const updateOrderStatus = vi.fn(async (orderId: number, status: string) => ({ id: orderId, estado: status }))

    await updateOrderStatusWithoutDailyClose({ updateOrderStatus }, 7, 'por_entregar')

    expect(updateOrderStatus).toHaveBeenCalledWith(7, 'por_entregar')
    expect(updateOrderStatus.mock.calls[0]).toHaveLength(2)
  })
})
