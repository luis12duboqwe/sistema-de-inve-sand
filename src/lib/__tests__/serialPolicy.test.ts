import { describe, expect, it } from 'vitest'
import { isValidWarrantySerial, requiresSerialTracking } from '../serialPolicy'

describe('serialized devices in sale editing and returns', () => {
  it('includes serialized accessories alongside phones', () => {
    expect(requiresSerialTracking({ categoria: 'accesorio', is_serialized: true })).toBe(true)
    expect(requiresSerialTracking({ categoria: 'accesorio', is_serialized: false })).toBe(false)
    expect(requiresSerialTracking({ categoria: 'celular', is_serialized: false })).toBe(true)
  })
  it('validates numeric serial lengths according to backend warranty contract', () => {
    expect(isValidWarrantySerial('12345678901234', false)).toBe(true)
    expect(isValidWarrantySerial('12345678901234567', false)).toBe(true)
    expect(isValidWarrantySerial('123456789012345', true)).toBe(true)
    expect(isValidWarrantySerial('12345678901234', true)).toBe(false)
    expect(isValidWarrantySerial('ALPHANUMERIC', false)).toBe(false)
  })
})
