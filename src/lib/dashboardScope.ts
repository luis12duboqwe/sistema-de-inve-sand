import type { OrderWithItems } from './types'

export interface DashboardScope {
  chartsOnly: boolean
  locationId: string
  channel: string
  profileId: string
  dateFrom: string
  dateTo: string
}

/** One shared UI predicate for charts, ranking tables and refund reconciliation. */
export function filterDashboardOrders<T extends Pick<OrderWithItems,
  'id' | 'source_location_id' | 'canal' | 'sales_profile_id' | 'created_at'>>(
  orders: readonly T[],
  scope: DashboardScope,
): T[] {
  if (!scope.chartsOnly) return [...orders]
  const from = scope.dateFrom ? new Date(scope.dateFrom + 'T00:00:00') : null
  const to = scope.dateTo ? new Date(scope.dateTo + 'T23:59:59.999') : null
  return orders.filter(order => {
    if (scope.locationId !== 'all' && order.source_location_id !== Number(scope.locationId)) return false
    if (scope.channel !== 'all' && order.canal !== scope.channel) return false
    if (scope.profileId !== 'all' && order.sales_profile_id !== Number(scope.profileId)) return false
    const created = new Date(order.created_at)
    if (from && created < from) return false
    if (to && created > to) return false
    return true
  })
}

/** A refund from store B must never reduce the filtered store A sales chart. */
export function sumScopedRefunds<T extends { id: number; order_id: number; created_at: string }>(
  refunds: readonly T[],
  scopedOrderIds: ReadonlySet<number>,
  amountsByReturnId: ReadonlyMap<number, number>,
  start: Date,
  end: Date,
): number {
  return refunds.reduce((sum, refund) => {
    if (!scopedOrderIds.has(refund.order_id)) return sum
    const time = new Date(refund.created_at)
    if (time < start || time > end) return sum
    return sum + (amountsByReturnId.get(refund.id) || 0)
  }, 0)
}
