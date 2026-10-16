interface CountLine {
  product_id: number
  expected_quantity: number
  counted_quantity: number
  imeis?: string[]
}
interface CountSnapshot {
  location_id: number
  items: CountLine[]
}
interface LocalStockRow { product_id: number; location_id: number; cantidad_disponible: number; cantidad_reservada?: number }
interface LocalProduct { id: number; is_serialized?: boolean }
interface LocalSerial { imei: string; product_id: number; location_id?: number; vendido: boolean; transfer_id?: number; order_id?: number }

/**
 * Reject a stale snapshot in its entirety, BEFORE mutating any inventory rows.
 * Local count approval cannot re-introduce units sold after a count was started.
 */
export function assertLocalInventoryCountIsFresh(
  count: CountSnapshot,
  stocks: readonly LocalStockRow[],
  products: readonly LocalProduct[],
  imeis: readonly LocalSerial[],
): void {
  const seen = new Set<number>()
  for (const line of count.items) {
    if (seen.has(line.product_id)) throw new Error('El conteo contiene el mismo producto dos veces')
    seen.add(line.product_id)
    const product = products.find(x => x.id === line.product_id)
    if (!product) throw new Error(`Producto no encontrado en conteo: ${line.product_id}`)
    if (!Number.isSafeInteger(line.counted_quantity) || line.counted_quantity < 0 ||
        !Number.isSafeInteger(line.expected_quantity) || line.expected_quantity < 0) {
      throw new Error('Cantidad inválida de conteo físico')
    }
    const stock = stocks.find(x => x.product_id === line.product_id && x.location_id === count.location_id)
    const current = stock?.cantidad_disponible ?? 0
    const reserved = stock?.cantidad_reservada ?? 0
    if (!Number.isSafeInteger(current) || !Number.isSafeInteger(reserved) || reserved < 0) {
      throw new Error('Estado de existencias inconsistente; requiere conciliación')
    }
    if (reserved > 0) {
      throw new Error(`El producto ${line.product_id} tiene unidades reservadas; no aprobar conteo hasta conciliación`)
    }
    if (product.is_serialized) {
      const available = imeis.filter(x =>
        x.product_id === line.product_id && x.location_id === count.location_id &&
        !x.vendido && !x.transfer_id && !x.order_id,
      )
      if (current !== line.expected_quantity || available.length !== line.expected_quantity) {
        throw new Error(`Conteo de IMEIs obsoleto para producto ${line.product_id}: hubo movimientos posteriores`)
      }
      const existing = new Set(available.map(x => x.imei))
      const scanned = line.imeis || []
      if (new Set(scanned).size !== scanned.length || scanned.length !== line.counted_quantity ||
          scanned.some(x => !existing.has(x))) {
        throw new Error(`Los IMEIs del conteo no coinciden con el inventario vigente del producto ${line.product_id}`)
      }
    } else if (current !== line.expected_quantity) {
      throw new Error(`Conteo obsoleto para producto ${line.product_id}: stock cambió de ${line.expected_quantity} a ${current}`)
    }
    if (line.counted_quantity < reserved) {
      throw new Error(`El conteo no puede dejar menos unidades que las reservadas`)
    }
  }
}
