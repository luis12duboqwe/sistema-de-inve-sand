import type { CreateReturnRequest, Order, OrderItem, Return, Product, ProductIMEI, Stock } from './types'

/** Validate cumulative returned quantities, ownership and replacement stock before writing. */
export function validateLocalReturnRequest(
  request: CreateReturnRequest,
  order: Pick<Order, 'id' | 'estado' | 'source_location_id'>,
  orderItems: readonly Pick<OrderItem, 'order_id' | 'product_id' | 'cantidad'>[],
  previousReturns: readonly Pick<Return, 'order_id' | 'status' | 'items'>[],
  products: readonly Pick<Product, 'id' | 'is_serialized'>[],
  imeis: readonly Pick<ProductIMEI, 'imei' | 'product_id' | 'location_id' | 'vendido' | 'order_id' | 'transfer_id'>[],
  stocks: readonly Pick<Stock, 'product_id' | 'location_id' | 'cantidad_disponible' | 'cantidad_reservada'>[],
): void {
  if (order.estado !== 'completada' && order.estado !== 'validada') {
    throw new Error('Sólo una venta completada admite devoluciones o garantías')
  }
  if (!order.source_location_id) throw new Error('La venta no tiene sede de origen')
  if (!Array.isArray(request.items) || !request.items.length) throw new Error('Devolución sin artículos')
  const prior = previousReturns.filter(x => x.order_id === order.id && x.status === 'completed')
  const requested = new Map<number, number>()
  const serialClaims = new Set<string>()

  for (const line of request.items) {
    if (!Number.isSafeInteger(line.quantity) || line.quantity <= 0) {
      throw new Error('Cantidad de devolución inválida')
    }
    const purchased = orderItems.filter(item => item.order_id === order.id && item.product_id === line.product_id)
      .reduce((total, item) => total + item.cantidad, 0)
    const previouslyReturned = prior.flatMap(x => x.items).filter(x => x.product_id === line.product_id)
      .reduce((total, item) => total + item.quantity, 0)
    const cumulative = (requested.get(line.product_id) || 0) + line.quantity
    if (!purchased || previouslyReturned + cumulative > purchased) {
      throw new Error('La cantidad devuelta supera la cantidad vendida o ya fue devuelta')
    }
    requested.set(line.product_id, cumulative)
    const serialized = products.find(product => product.id === line.product_id)?.is_serialized
    if (!serialized) {
      if (line.imei || line.replacement_imei) throw new Error('IMEI no corresponde al producto no serializado')
      continue
    }
    if (line.quantity !== 1 || !line.imei || serialClaims.has(line.imei)) {
      throw new Error('Cada devolución serializada requiere un IMEI original distinto')
    }
    serialClaims.add(line.imei)
    const original = imeis.find(i => i.imei === line.imei)
    if (!original || original.product_id !== line.product_id || !original.vendido || original.order_id !== order.id) {
      throw new Error('El IMEI original no pertenece a la venta o ya fue devuelto')
    }
    if (prior.some(ret => ret.items.some(i => i.imei === line.imei))) {
      throw new Error('El IMEI ya fue devuelto anteriormente')
    }
    if (line.action === 'warranty_exchange') {
      if (!line.replacement_imei || line.replacement_imei === line.imei ||
          serialClaims.has(line.replacement_imei)) {
        throw new Error('Garantía serializada requiere un IMEI de reemplazo distinto')
      }
      serialClaims.add(line.replacement_imei)
      const replacement = imeis.find(i => i.imei === line.replacement_imei)
      if (!replacement || replacement.product_id !== line.product_id ||
          replacement.vendido || replacement.order_id || replacement.transfer_id ||
          !replacement.location_id) {
        throw new Error('IMEI de reemplazo no está disponible')
      }
      const stock = stocks.find(item =>
        item.product_id === replacement.product_id && item.location_id === replacement.location_id)
      if (!stock || stock.cantidad_disponible - (stock.cantidad_reservada || 0) < 1) {
        throw new Error('No hay stock libre para entregar el reemplazo')
      }
    } else if (line.replacement_imei) {
      throw new Error('Sólo una garantía puede seleccionar IMEI de reemplazo')
    }
  }
}
