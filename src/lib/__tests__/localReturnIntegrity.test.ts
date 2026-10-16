import { describe, expect, it } from 'vitest'
import { validateLocalReturnRequest } from '../localReturnIntegrity'
import type { CreateReturnRequest, Order, OrderItem, Product, ProductIMEI, Stock, Return } from '../types'

const order = { id: 1, estado: 'completada', source_location_id: 10 } as Order
const orderItems = [{ order_id: 1, product_id: 2, cantidad: 1 }] as OrderItem[]
const products = [{ id: 2, is_serialized: true }] as Product[]
const stock = [{ product_id: 2, location_id: 10, cantidad_disponible: 1, cantidad_reservada: 0 }] as Stock[]
const imeis = [
  { imei: 'original', product_id: 2, location_id: 10, vendido: true, order_id: 1 },
  { imei: 'replacement', product_id: 2, location_id: 10, vendido: false },
] as ProductIMEI[]
const refund = (patch: Partial<CreateReturnRequest> = {}): CreateReturnRequest => ({
  order_id: 1, items: [{ product_id: 2, quantity: 1, condition: 'defectuoso', action: 'warranty_exchange', imei: 'original', replacement_imei: 'replacement' }],
  ...patch,
})

describe('local returns never invent stock or recycle defective IMEIs', () => {
  const validate = (p: CreateReturnRequest, history: Return[] = [], serials = imeis) =>
    validateLocalReturnRequest(p, order, orderItems, history, products, serials, stock)

  it('accepts one legitimate warranty exchange', () => {
    expect(() => validate(refund())).not.toThrow()
  })
  it('rejects repeat returns against the same original sale quantity', () => {
    const history = [{ order_id: 1, status: 'completed', items: refund().items }] as Return[]
    expect(() => validate(refund(), history)).toThrow(/supera/)
  })
  it('rejects a serial already returned even if its sold flag is stale', () => {
    expect(() => validate(refund(), [], [
      { ...imeis[0], vendido: false }, imeis[1],
    ])).toThrow(/ya fue devuelto/)
  })
  it('requires available matching replacement serial and non-reserved stock', () => {
    expect(() => validate(refund({ items: [{ ...refund().items[0], replacement_imei: 'other' }] })))
      .toThrow(/no está disponible/)
    expect(() => validateLocalReturnRequest(refund(), order, orderItems, [], products, imeis,
      [{ ...stock[0], cantidad_reservada: 1 }],
    )).toThrow(/stock libre/)
  })
  it('rejects unfinished sales and overreturns', () => {
    expect(() => validateLocalReturnRequest(refund(), { ...order, estado: 'pendiente' }, orderItems, [], products, imeis, stock))
      .toThrow(/completada/)
    expect(() => validate(refund({ items: [{ ...refund().items[0], quantity: 2 }] }))).toThrow(/supera/)
  })
})
