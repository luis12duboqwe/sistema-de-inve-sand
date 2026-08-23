export type OrderStatusUpdater<TStatus, TResult> = {
  updateOrderStatus: (orderId: number, status: TStatus) => Promise<TResult>
}

/**
 * Ordinary order transitions deliberately accept only order id + status.
 * Daily-close validation is a separate workflow and must never leak a
 * validation code into normal completion calls.
 */
export function updateOrderStatusWithoutDailyClose<TStatus, TResult>(
  service: OrderStatusUpdater<TStatus, TResult>,
  orderId: number,
  status: TStatus,
): Promise<TResult> {
  return service.updateOrderStatus(orderId, status)
}
