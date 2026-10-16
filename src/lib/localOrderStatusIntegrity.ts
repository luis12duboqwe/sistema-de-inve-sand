import type { Order } from './types'

type LocalOrderStatus = Order['estado']

/** Prevent status-only cancellation and downgrades of legally finalized sales. */
export function validateLocalOrderStatusChange(
  previous: LocalOrderStatus,
  next: LocalOrderStatus,
): void {
  if (previous === 'cancelada') throw new Error('No se puede reactivar una orden cancelada')
  if (next === 'cancelada') {
    throw new Error('Cancelar requiere liberar stock mediante cancelOrder')
  }
  if (previous === 'validada' && next !== 'validada') {
    throw new Error('Una venta validada no puede cambiar de estado sin reversión auditada')
  }
  if (previous === 'completada' && next !== 'completada' && next !== 'validada') {
    throw new Error('Una venta completada no puede regresar a pendiente')
  }
  if (next === 'validada' && previous !== 'completada' && previous !== 'validada') {
    throw new Error('Primero debe completar la venta antes de validarla')
  }
}
