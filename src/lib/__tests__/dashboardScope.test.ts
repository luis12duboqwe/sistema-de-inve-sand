import { describe, expect, it } from 'vitest'
import { filterDashboardOrders, sumScopedRefunds } from '../dashboardScope'

const records = [
  { id: 1, source_location_id: 101, canal: 'whatsapp', sales_profile_id: 7, created_at: '2026-10-14T10:00:00' },
  { id: 2, source_location_id: 202, canal: 'whatsapp', sales_profile_id: 7, created_at: '2026-10-14T10:00:00' },
  { id: 3, source_location_id: 101, canal: 'tienda', sales_profile_id: 7, created_at: '2026-10-14T10:00:00' },
  { id: 4, source_location_id: 101, canal: 'whatsapp', sales_profile_id: 8, created_at: '2026-10-14T10:00:00' },
  { id: 5, source_location_id: 101, canal: 'whatsapp', sales_profile_id: 7, created_at: '2026-09-01T10:00:00' },
]

describe('dashboard filters across all charts', () => {
  it('keeps only the requested store, channel, profile and dates', () => {
    const selected = filterDashboardOrders(records, {
      chartsOnly: true, locationId: '101', channel: 'whatsapp',
      profileId: '7', dateFrom: '2026-10-14', dateTo: '2026-10-14',
    })
    expect(selected.map(x => x.id)).toEqual([1])
  })
  it('uses full business data only when no chart filtering is requested', () => {
    const result = filterDashboardOrders(records, {
      chartsOnly: false, locationId: '101', channel: 'whatsapp',
      profileId: '7', dateFrom: '', dateTo: '',
    })
    expect(result).toHaveLength(5)
  })
  it('excludes refunds belonging to an unrelated location/customer order', () => {
    const list = [
      { id: 11, order_id: 1, created_at: '2026-10-14T12:00:00' },
      { id: 12, order_id: 2, created_at: '2026-10-14T12:00:00' },
    ]
    const value = sumScopedRefunds(
      list, new Set([1]), new Map([[11, 30], [12, 100]]),
      new Date('2026-10-14T00:00:00'), new Date('2026-10-14T23:59:59'),
    )
    expect(value).toBe(30)
  })
})
