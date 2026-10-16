import { describe, expect, it } from 'vitest'
import { calculateDailyCloseBreakdown } from '../dailyCloseBreakdown'

describe('daily close mixed payments', () => {
  it('does not attribute all of a mixed order to its primary method', () => {
    const totals = calculateDailyCloseBreakdown([{
      metodo_pago: 'efectivo',
      total: 100,
      payment_breakdown: [
        { method: 'efectivo', amount: 40 },
        { method: 'transferencia', amount: 60 },
      ],
    }])
    expect(totals.efectivo.total).toBe(40)
    expect(totals.transferencia.total).toBe(60)
  })
  it('marks inconsistent historical breakdown as unclassified', () => {
    expect(calculateDailyCloseBreakdown([
      { metodo_pago: 'tarjeta', total: 300, payment_breakdown: [] },
    ]).sin_conciliar.total).toBe(300)
  })
})
