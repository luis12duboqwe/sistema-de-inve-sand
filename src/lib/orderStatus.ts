import type { Order } from './types'

export const FINAL_SALE_STATUSES: ReadonlySet<Order['estado']> = new Set(['completada', 'validada'])

export function isFinalSaleStatus(status: Order['estado']): boolean {
  return FINAL_SALE_STATUSES.has(status)
}

export function canEditOrderStatus(status: Order['estado']): boolean {
  return !isFinalSaleStatus(status) && status !== 'cancelada'
}