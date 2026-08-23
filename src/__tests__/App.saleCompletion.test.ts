import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const appSource = readFileSync(join(process.cwd(), 'src', 'App.tsx'), 'utf8')

describe('sale completion state-machine separation', () => {
  it('never requests the daily-close validation code while completing an order', () => {
    expect(appSource).not.toContain('getCompletionValidationCode')
    expect(appSource).not.toContain('getDailyCloseConfig()')
    expect(appSource).not.toContain("title: 'Validar venta'")
    expect(appSource).not.toContain('Ingrese el código configurado para completar y validar esta venta.')
  })

  it('keeps both single and bulk completion on the ordinary status endpoint', () => {
    const directStatusUpdates = appSource.match(/updateOrderStatus\(orderId, newStatus\)/g) ?? []
    expect(directStatusUpdates.length).toBeGreaterThanOrEqual(2)
  })

  it('keeps daily-close validation as an explicit separate action', () => {
    expect(appSource).toContain('<DailyCloseDialog')
    expect(appSource).toContain('onValidated={() =>')
    expect(appSource).toContain("title=\"Cierre de Día — Validar Ventas\"")
  })
})
