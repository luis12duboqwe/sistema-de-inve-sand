import { afterEach, describe, expect, it, vi } from 'vitest'
import { accountingSaleDate, generateMonthlyTrends, generateReportData } from '../reportUtils'
import type { OrderWithItems, ProductWithStock } from '../types'

const fixture = (input: Partial<OrderWithItems>): OrderWithItems => ({
  id: 1, customer_name: 'Cliente', customer_phone: '50400000000',
  canal: 'tienda', metodo_pago: 'efectivo', estado: 'completada',
  total: 1000, created_at: '2026-09-29T12:00:00',
  items: [], ...input,
}) as OrderWithItems

describe('accounting reports preserve sale dates and promotion costs', () => {
  afterEach(() => vi.useRealTimers())

  it('recognizes the sale completion month rather than draft creation month', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-15T12:00:00'))
    const order = fixture({ completed_at: '2026-10-04T14:00:00' })
    expect(accountingSaleDate(order).getMonth()).toBe(9)
    const months = generateMonthlyTrends([order], 2)
    expect(months.map(x => x.revenue)).toEqual([0, 1000])
  })

  it('includes gifted accessory historical cost in the gross margin', () => {
    const order = fixture({
      items: [
        {id:1,order_id:1,product_id:1,cantidad:1,precio_unitario:1000,costo_unitario:600,es_regalo_promocion:false},
        {id:2,order_id:1,product_id:2,cantidad:1,precio_unitario:0,costo_unitario:100,es_regalo_promocion:true},
      ],
    })
    const products = [{id:1,nombre:'Teléfono',precio:1000,activo:true}] as ProductWithStock[]
    const result = generateReportData([order], products)
    expect(result.totalRevenue).toBe(1000)
    expect(result.profitMargin).toBe(30)
  })
})
