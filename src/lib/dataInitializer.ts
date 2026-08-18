import { getKV } from './kvStorage'

const BACKUP_FORMAT = 'softmobile-browser-backup'
const BACKUP_FORMAT_VERSION = 3

type BrowserBackup = {
  format?: string
  formatVersion?: number
  exportedAt?: string
  kv?: Record<string, unknown>
  // Campos V1 conservados para poder importar backups antiguos y para que
  // herramientas existentes que lean este JSON sigan funcionando.
  profiles?: unknown[]
  products?: unknown[]
  stock?: unknown[]
  orders?: unknown[]
  orderItems?: unknown[]
}

/**
 * Inicializa los datos del sistema si no existen
 */
export async function initializeDefaultData() {
  const kv = getKV()

  try {
    const existingProfiles = await kv.get('inventory-profiles')

    if (!existingProfiles) {
      await kv.set('inventory-profiles', [])
      await kv.set('inventory-products', [])
      await kv.set('inventory-stock', [])
      await kv.set('inventory-orders', [])
      await kv.set('inventory-order-items', [])
      return true
    }

    return false
  } catch (error) {
    console.error('Error initializing default data:', error)
    throw error
  }
}

/**
 * Limpia todos los datos del sistema (usar con precaución)
 */
export async function clearAllData() {
  const kv = getKV()

  try {
    // V1 Keys
    await kv.delete('inventory-profiles')
    await kv.delete('inventory-products')
    await kv.delete('inventory-stock')
    await kv.delete('inventory-orders')
    await kv.delete('inventory-order-items')

    // V2 Keys
    await kv.delete('inventory-locations')
    await kv.delete('inventory-sales-profiles')
    await kv.delete('inventory-suppliers')
    await kv.delete('inventory-stock-transfers')
    await kv.delete('inventory-stock-history')
    await kv.delete('inventory-product-imeis')
    await kv.delete('inventory-returns')
    await kv.delete('inventory-return-items')
    await kv.delete('inventory-imei-history')
    await kv.delete('inventory-trade-ins')

    // Settings
    await kv.delete('v2_reset_complete_final')
  } catch (error) {
    console.error('Error clearing data:', error)
    throw error
  }
}

/**
 * Exporta una instantánea completa del KV del navegador.
 *
 * Las versiones anteriores sólo incluían cinco colecciones V1, por lo que un
 * backup podía omitir IMEIs, transferencias, devoluciones, clientes, usuarios,
 * bancos, FAQs y configuraciones. El formato V3 enumera todas las claves
 * `spark-kv-*` a través de la abstracción KV y conserva además los cinco campos
 * V1 para compatibilidad hacia atrás.
 */
export async function exportAllData(): Promise<BrowserBackup> {
  const kv = getKV()

  try {
    const keys = await kv.keys()
    const entries = await Promise.all(
      keys.map(async key => [key, await kv.get<unknown>(key)] as const)
    )

    const snapshot: Record<string, unknown> = {}
    for (const [key, value] of entries) {
      if (value !== undefined) snapshot[key] = value
    }

    return {
      format: BACKUP_FORMAT,
      formatVersion: BACKUP_FORMAT_VERSION,
      exportedAt: new Date().toISOString(),
      kv: snapshot,
      profiles: (snapshot['inventory-profiles'] as unknown[] | undefined) ?? [],
      products: (snapshot['inventory-products'] as unknown[] | undefined) ?? [],
      stock: (snapshot['inventory-stock'] as unknown[] | undefined) ?? [],
      orders: (snapshot['inventory-orders'] as unknown[] | undefined) ?? [],
      orderItems: (snapshot['inventory-order-items'] as unknown[] | undefined) ?? []
    }
  } catch (error) {
    console.error('Error exporting data:', error)
    throw error
  }
}

/**
 * Restaura backups V3 completos y sigue aceptando el antiguo formato V1.
 * La política runtime de kvStorage sigue aplicándose al restaurar; por ejemplo,
 * `settings_use_api=false` nunca puede desactivar API en un build productivo.
 */
export async function importAllData(data: BrowserBackup) {
  const kv = getKV()

  try {
    if (data.kv && typeof data.kv === 'object' && !Array.isArray(data.kv)) {
      for (const [key, value] of Object.entries(data.kv)) {
        if (value !== undefined) await kv.set(key, value)
      }
      return
    }

    // Compatibilidad con archivos creados por versiones anteriores.
    if (data.profiles) await kv.set('inventory-profiles', data.profiles)
    if (data.products) await kv.set('inventory-products', data.products)
    if (data.stock) await kv.set('inventory-stock', data.stock)
    if (data.orders) await kv.set('inventory-orders', data.orders)
    if (data.orderItems) await kv.set('inventory-order-items', data.orderItems)
  } catch (error) {
    console.error('Error importing data:', error)
    throw error
  }
}

// Exponer funciones globalmente para debugging/recuperación de instalaciones viejas.
if (typeof window !== 'undefined') {
  ;(window as any).inventoryDebug = {
    initializeDefaultData,
    clearAllData,
    exportAllData,
    importAllData
  }
}
