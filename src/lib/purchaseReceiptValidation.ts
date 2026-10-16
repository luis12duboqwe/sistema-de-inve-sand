import type { PurchaseReceiptInput } from './types'

interface LocalProduct { id: number; nombre: string; activo: boolean; is_serialized?: boolean }
interface LocalLocation { id: number; activo: boolean }
interface LocalSupplier { id: number; activo: boolean }
interface LocalSerial { imei: string }

export function validateLocalPurchaseReceipt(
  payload: PurchaseReceiptInput,
  inventory: {
    products: readonly LocalProduct[]
    locations: readonly LocalLocation[]
    suppliers: readonly LocalSupplier[]
    existingImeis: readonly LocalSerial[]
  },
): void {
  if (!Number.isSafeInteger(payload.location_id) || !inventory.locations.some(
    loc => loc.id === payload.location_id && loc.activo,
  )) throw new Error('Ubicación de recepción inexistente o inactiva')
  if (payload.supplier_id !== undefined && payload.supplier_id !== null && !inventory.suppliers.some(
    supplier => supplier.id === payload.supplier_id && supplier.activo,
  )) throw new Error('Proveedor de recepción inexistente o inactivo')
  if (!Array.isArray(payload.items) || payload.items.length === 0) {
    throw new Error('Una recepción requiere al menos una línea de producto')
  }

  const allImeis = new Set(inventory.existingImeis.map(row => row.imei.trim()))
  for (const [index, row] of payload.items.entries()) {
    if (!Number.isSafeInteger(row.product_id) || row.product_id <= 0) {
      throw new Error(`Producto inválido en línea ${index + 1}`)
    }
    const product = inventory.products.find(item => item.id === row.product_id && item.activo)
    if (!product) throw new Error(`Producto ${row.product_id} inexistente o inactivo`)
    if (!Number.isSafeInteger(row.quantity) || row.quantity <= 0) {
      throw new Error(`Cantidad positiva y entera requerida para ${product.nombre}`)
    }
    if (typeof row.unit_cost !== 'number' || !Number.isFinite(row.unit_cost) || row.unit_cost < 0) {
      throw new Error(`Costo inválido para ${product.nombre}`)
    }
    const imeis = row.imeis || []
    if (!Array.isArray(imeis) || imeis.some(imei => typeof imei !== 'string' || !imei.trim())) {
      throw new Error(`IMEI inválido para ${product.nombre}`)
    }
    if (product.is_serialized && imeis.length !== row.quantity) {
      throw new Error(`Producto ${product.nombre} requiere ${row.quantity} IMEI(s)`)
    }
    if (!product.is_serialized && imeis.length > 0) {
      throw new Error(`Producto no serializado ${product.nombre} no puede registrar IMEIs`)
    }
    for (const raw of imeis) {
      const imei = raw.trim()
      if (allImeis.has(imei)) {
        throw new Error(`El IMEI ${imei} ya aparece en inventario u otra línea de esta recepción`)
      }
      allImeis.add(imei)
    }
  }
}
