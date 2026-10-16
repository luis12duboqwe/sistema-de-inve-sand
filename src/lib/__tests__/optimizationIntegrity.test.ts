import { describe, expect, it } from 'vitest'
import { analyzeCustomers, analyzeProductMix, calculateOptimizationScore, finalSaleTimestamp } from '../optimizationAnalytics'
import type { ProductWithStock, OrderWithItems } from '../types'

const product = {
  id: 1, nombre: 'Teléfono', marca: 'Apple', modelo: 'Test',
  activo: true, precio: 1500, stock_disponible: 12,
} as ProductWithStock

function order(state: OrderWithItems['estado'], price: number, cost?: number, phone = '70123456'): OrderWithItems {
  return {
    id: 1, estado: state, customer_name: 'Cliente', customer_phone: phone,
    created_at: new Date(Date.now() - 100 * 24 * 3600_000).toISOString(),
    completed_at: new Date().toISOString(), total: price,
    items: [{ id: 1, order_id: 1, product_id: 1, cantidad: 1,
              precio_unitario: price, costo_unitario: cost, es_regalo_promocion: false }],
  } as OrderWithItems
}

describe('optimization uses finalized sales only', () => {
  it('counts a sale on completion date rather than original creation', () => {
    const completed = order('completada', 100)
    expect(Date.now() - finalSaleTimestamp(completed).getTime()).toBeLessThan(3600_000)
    expect(analyzeProductMix([product], [completed]).some(x => x.type === 'best_seller')).toBe(true)
  })

  it('never counts pending or cancelled orders as sales revenue or demand', () => {
    const pending = order('pendiente', 9999)
    const cancelled = order('cancelada', 9999)
    expect(analyzeProductMix([product], [pending, cancelled])).toEqual([])
    expect(calculateOptimizationScore([product], [pending, cancelled]))
      .toBe(calculateOptimizationScore([product], []))
  })

  it('does not falsely declare losses from current price or missing historical costs', () => {
    expect(analyzeProductMix([product], [order('completada', 100, 50)])
      .some(x => x.type === 'poor_performer')).toBe(false)
    expect(analyzeProductMix([product], [order('completada', 100)])
      .some(x => x.type === 'poor_performer')).toBe(false)
    expect(analyzeProductMix([product], [order('completada', 100, 125)])
      .some(x => x.type === 'poor_performer')).toBe(true)
  })

  it('does not combine unknown-phone orders into a fictitious VIP', () => {
    const anonymous = [order('completada', 5000, 100, ''), order('completada', 5000, 100, ''),
                       order('completada', 5000, 100, '')]
    expect(analyzeCustomers(anonymous)).toEqual([])
  })
})
