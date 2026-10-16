import type { CreateStockTransferRequest } from './types'

/** Client-side validation for legacy local-only stock transfers. */
export function validateLocalTransferRequest(request: CreateStockTransferRequest): void {
  for (const id of [request.product_id, request.from_location_id, request.to_location_id]) {
    if (!Number.isSafeInteger(id) || id <= 0) throw new Error('Identificador de producto o sede inválido')
  }
  if (request.from_location_id === request.to_location_id) {
    throw new Error('La sede de origen debe ser diferente del destino')
  }
  if (!Number.isSafeInteger(request.cantidad) || request.cantidad <= 0) {
    throw new Error('La cantidad a transferir debe ser entera y positiva')
  }
  const imeis = request.imeis ?? []
  if (!Array.isArray(imeis)) throw new Error('Lista de IMEIs inválida')
  const seen = new Set<string>()
  for (const imei of imeis) {
    if (typeof imei !== 'string' || !imei.trim() || imei !== imei.trim()) {
      throw new Error('IMEI vacío o con espacios inválidos')
    }
    if (seen.has(imei)) throw new Error(`IMEI duplicado en transferencia: ${imei}`)
    seen.add(imei)
  }
  if (imeis.length && imeis.length !== request.cantidad) {
    throw new Error('Cantidad de IMEIs no coincide con unidades a transferir')
  }
}
