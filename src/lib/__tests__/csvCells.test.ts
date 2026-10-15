import { describe, expect, it } from 'vitest'
import { formatCsvCell } from '../exportUtils'
describe('safe CSV cell', () => {
  it('doubles quotes and retains Unicode and newlines', () => {
    expect(formatCsvCell('hola "SPS",\nMóvil')).toBe('"hola ""SPS"",\nMóvil"')
  })
  it('neutralizes formulas without altering true numeric values', () => {
    expect(formatCsvCell('=SUM(1,2)')).toBe('"\'=SUM(1,2)"')
    expect(formatCsvCell('  +CMD')).toBe('"\'  +CMD"')
    expect(formatCsvCell(-5)).toBe('"-5"')
  })
  it('renders nulls as empty cells', () => {
    expect(formatCsvCell(undefined)).toBe('""')
  })
})
