import { describe, expect, it } from 'vitest'
import { validateLocalPurchaseReceipt } from '../purchaseReceiptValidation'
import type { PurchaseReceiptInput } from '../types'

const inventory = {
  locations: [{ id: 1, activo: true }, { id: 2, activo: false }],
  suppliers: [{ id: 10, activo: true }],
  products: [
    { id: 1, nombre: 'iPhone', activo: true, is_serialized: true },
    { id: 2, nombre: 'Cargador', activo: true, is_serialized: false },
    { id: 3, nombre: 'Antiguo', activo: false, is_serialized: false },
  ],
  existingImeis: [{ imei: '333333333333333' }],
}

const receipt = (overrides: Partial<PurchaseReceiptInput> = {}): PurchaseReceiptInput => ({
  location_id: 1, supplier_id: 10,
  items: [{ product_id: 1, quantity: 1, unit_cost: 1250, imeis: ['111111111111111'] }],
  ...overrides,
})

describe('local purchase intake validation before any stock write', () => {
  it('accepts valid serialized and non-serialized purchases', () => {
    expect(() => validateLocalPurchaseReceipt(receipt({
      items: [
        { product_id: 1, quantity: 2, unit_cost: 100, imeis: ['111111111111111', '222222222222222'] },
        { product_id: 2, quantity: 4, unit_cost: 0 },
      ],
    }), inventory)).not.toThrow()
  })
  it.each([0, -1, 1.2, Number.NaN, Infinity])('rejects quantity %s', quantity => {
    expect(() => validateLocalPurchaseReceipt(receipt({
      items: [{ product_id: 2, quantity, unit_cost: 1 }],
    }), inventory)).toThrow(/Cantidad/)
  })
  it.each([-1, Number.NaN, Infinity])('rejects invalid cost %s', unit_cost => {
    expect(() => validateLocalPurchaseReceipt(receipt({
      items: [{ product_id: 2, quantity: 1, unit_cost }],
    }), inventory)).toThrow(/Costo/)
  })
  it('rejects duplicate IMEIs even within a line and across lines', () => {
    const duplicate = [
      { product_id: 1, quantity: 1, unit_cost: 50, imeis: ['111111111111111'] },
      { product_id: 1, quantity: 1, unit_cost: 50, imeis: ['111111111111111'] },
    ]
    expect(() => validateLocalPurchaseReceipt(receipt({ items: duplicate }), inventory)).toThrow(/ya aparece/)
    expect(() => validateLocalPurchaseReceipt(receipt({
      items: [{ product_id: 1, quantity: 2, unit_cost: 50, imeis: ['111111111111111', '111111111111111'] }],
    }), inventory)).toThrow(/ya aparece/)
  })
  it('rejects previously sold or reserved serial already in inventory', () => {
    expect(() => validateLocalPurchaseReceipt(receipt({
      items: [{ product_id: 1, quantity: 1, unit_cost: 50, imeis: ['333333333333333'] }],
    }), inventory)).toThrow(/ya aparece/)
  })
  it('rejects non-existent or inactive locations, products and suppliers', () => {
    expect(() => validateLocalPurchaseReceipt(receipt({ location_id: 2 }), inventory)).toThrow(/Ubicación/)
    expect(() => validateLocalPurchaseReceipt(receipt({ supplier_id: 11 }), inventory)).toThrow(/Proveedor/)
    expect(() => validateLocalPurchaseReceipt(receipt({
      items: [{ product_id: 3, quantity: 1, unit_cost: 1 }],
    }), inventory)).toThrow(/inactivo/)
  })
  it('rejects IMEIs on non-serialized lines', () => {
    expect(() => validateLocalPurchaseReceipt(receipt({
      items: [{ product_id: 2, quantity: 1, unit_cost: 1, imeis: ['111111111111111'] }],
    }), inventory)).toThrow(/no puede registrar IMEIs/)
  })
})
