/** Break down real amounts, not the payment method stored as the order label. */
export function calculateDailyCloseBreakdown(
  orders: ReadonlyArray<{
    metodo_pago: string
    total: number
    payment_breakdown?: Array<{ method: string; amount: number }> | null
  }>,
): Record<string, { count: number; total: number }> {
  const result: Record<string, { count: number; total: number }> = {}
  for (const order of orders) {
    // [] explicitly denotes malformed data; don't pretend it was all cash.
    const components = order.payment_breakdown === undefined || order.payment_breakdown === null
      ? [{ method: order.metodo_pago, amount: order.total }]
      : order.payment_breakdown.length === 0
        ? [{ method: 'sin_conciliar', amount: order.total }]
        : order.payment_breakdown
    for (const component of components) {
      const current = result[component.method] ?? { count: 0, total: 0 }
      current.count += 1
      current.total += component.amount
      result[component.method] = current
    }
  }
  return result
}
