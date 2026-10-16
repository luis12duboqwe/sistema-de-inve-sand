import type { Order, OrderItem, ProductIMEI, StockHistory } from './types'

/**
 * Never fabricate replacement stock by hard-deleting a sale or a held order.
 * Only an unused empty draft without any inventory linkage may be discarded.
 */
export function assertLocalOrderDeletionAllowed(
  order: Pick<Order, 'estado'>,
  items: readonly Pick<OrderItem, 'id'>[],
  serials: readonly Pick<ProductIMEI, 'id'>[],
  stockHistory: readonly Pick<StockHistory, 'id'>[],
): void {
  if (order.estado !== 'pendiente') {
    throw new Error('Solo se pueden eliminar borradores vacíos; cancele y conserve el historial de ventas')
  }
  if (items.length || serials.length || stockHistory.length) {
    throw new Error('Orden con artículos o movimientos de inventario: no se permite borrado físico; use cancelación auditada')
  }
}
