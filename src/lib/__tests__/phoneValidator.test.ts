import { describe, it, expect } from 'vitest'

import { validatePhoneNumber } from '../phoneValidator'

describe('phoneValidator', () => {
  it('rechaza números vacíos', () => {
    const result = validatePhoneNumber('   ')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('requerido')
  })

  it('rechaza caracteres no permitidos', () => {
    const result = validatePhoneNumber('ABC12345')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('Formato de teléfono inválido')
  })

  it('rechaza números demasiado largos', () => {
    const result = validatePhoneNumber('+504 1234-5678-9012-3456')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('no puede exceder')
  })

  it('exige al menos 8 dígitos', () => {
    const result = validatePhoneNumber('+504-123')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('al menos 8 dígitos')
  })

  it('acepta números válidos con formato mixto', () => {
    const result = validatePhoneNumber(' +504 (9999) 1111 ')
    expect(result.valid).toBe(true)
    expect(result.phone).toBe('+504 (9999) 1111')
  })
})
