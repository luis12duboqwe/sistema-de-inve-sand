import { getKV } from './kvStorage'
import { apiClient } from './apiClient'
import { 
  Profile, Location, SalesProfile, ProductWithStock 
} from './types'

export const syncService = {
  async syncLocalToRemote() {
    const kv = getKV()
    
    // 1. Load Local Data
    const profiles = await kv.get<Profile[]>('inventory-profiles') || []
    const locations = await kv.get<Location[]>('inventory-locations') || []
    const salesProfiles = await kv.get<SalesProfile[]>('inventory-sales-profiles') || []
    const products = await kv.get<ProductWithStock[]>('inventory-products') || []
    
    const syncedCount = {
      profiles: 0,
      locations: 0,
      salesProfiles: 0,
      products: 0
    }

    try {
      // 2. Sync Profiles (Legacy)
      for (const p of profiles) {
        try {
          await apiClient.createProfile(p.name, p.slug)
          syncedCount.profiles++
        } catch (e) {
          console.warn(`Skipping profile ${p.slug}:`, e)
        }
      }

      // 3. Sync Locations
      for (const l of locations) {
        try {
          await apiClient.createLocation({
            nombre: l.nombre,
            tipo: l.tipo,
            direccion: l.direccion,
            telefono: l.telefono,
            activo: l.activo
          })
          syncedCount.locations++
        } catch (e) {
           console.warn(`Skipping location ${l.nombre}:`, e)
        }
      }

      // 4. Sync Sales Profiles
      for (const sp of salesProfiles) {
        try {
          await apiClient.createSalesProfile({
            name: sp.name,
            slug: sp.slug,
            tipo: sp.tipo,
            canales: sp.canales,
            configuracion: sp.configuracion,
            active: sp.active
          })
          syncedCount.salesProfiles++
        } catch (e) {
          console.warn(`Skipping sales profile ${sp.slug}:`, e)
        }
      }

      // 5. Sync Products
      for (const p of products) {
        try {
          // Find primary stock
          const primaryStock = p.stock_items?.[0]
          const initialStock = primaryStock?.cantidad_disponible || 0
          const locationId = primaryStock?.location_id
          
          // Prepare product object (omit id, activo)
          const { id: _id, activo: _activo, stock_items: _stock_items, stock_disponible: _stock_disponible, ...productData } = p
          
          await apiClient.createProduct(
            productData,
            initialStock,
            locationId
          )
          syncedCount.products++
        } catch (e) {
          console.warn(`Skipping product ${p.sku}:`, e)
        }
      }

      return { success: true, counts: syncedCount }
      
    } catch (error) {
      console.error('Sync failed:', error)
      throw error
    }
  }
}
