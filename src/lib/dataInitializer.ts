import { getKV } from './kvStorage'

/**
 * Inicializa los datos del sistema si no existen
 */
export async function initializeDefaultData() {
  const kv = getKV()
  
  try {
    // Verificar si ya existen perfiles
    const existingProfiles = await kv.get('inventory-profiles')
    
    if (!existingProfiles) {
      console.log('No profiles found, initializing with empty array...')
      await kv.set('inventory-profiles', [])
      await kv.set('inventory-products', [])
      await kv.set('inventory-stock', [])
      await kv.set('inventory-orders', [])
      await kv.set('inventory-order-items', [])
      console.log('✅ Default data initialized successfully')
      return true
    }
    
    console.log('Data already initialized')
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
    await kv.delete('inventory-profiles')
    await kv.delete('inventory-products')
    await kv.delete('inventory-stock')
    await kv.delete('inventory-orders')
    await kv.delete('inventory-order-items')
    console.log('✅ All data cleared successfully')
  } catch (error) {
    console.error('Error clearing data:', error)
    throw error
  }
}

/**
 * Exporta todos los datos del sistema
 */
export async function exportAllData() {
  const kv = getKV()
  
  try {
    const [profiles, products, stock, orders, orderItems] = await Promise.all([
      kv.get('inventory-profiles'),
      kv.get('inventory-products'),
      kv.get('inventory-stock'),
      kv.get('inventory-orders'),
      kv.get('inventory-order-items')
    ])
    
    return {
      profiles: profiles || [],
      products: products || [],
      stock: stock || [],
      orders: orders || [],
      orderItems: orderItems || [],
      exportedAt: new Date().toISOString()
    }
  } catch (error) {
    console.error('Error exporting data:', error)
    throw error
  }
}

/**
 * Importa datos al sistema
 */
export async function importAllData(data: {
  profiles?: any[]
  products?: any[]
  stock?: any[]
  orders?: any[]
  orderItems?: any[]
}) {
  const kv = getKV()
  
  try {
    if (data.profiles) await kv.set('inventory-profiles', data.profiles)
    if (data.products) await kv.set('inventory-products', data.products)
    if (data.stock) await kv.set('inventory-stock', data.stock)
    if (data.orders) await kv.set('inventory-orders', data.orders)
    if (data.orderItems) await kv.set('inventory-order-items', data.orderItems)
    
    console.log('✅ Data imported successfully')
  } catch (error) {
    console.error('Error importing data:', error)
    throw error
  }
}

// Exponer funciones globalmente para debugging
if (typeof window !== 'undefined') {
  (window as any).inventoryDebug = {
    initializeDefaultData,
    clearAllData,
    exportAllData,
    importAllData
  }
}
