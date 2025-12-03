import type { Profile, ProductWithStock, OrderWithItems } from './types'

  severity: 'critical' | 'warning' 
  message: s
    type: 'product' | 'order' | 'profile' |
    name?: string
  autoFixable: bo
}
export interface HealthCheckResult {
  issues: Heal
    critical: num
    i
  lastCheck: string

 


    products: Prod
    profiles: Profile[]
    this.pro
    this.profiles = 

    this.issues 
   
    this.checkOrpha
 

    this.checkProfileConsistency()

      critical: this.issues.filter
      info: this.issues.filte


  constructor(
    products: ProductWithStock[],
    orders: OrderWithItems[],
    profiles: Profile[]
  ) {
    this.products = products
    this.orders = orders
    this.profiles = profiles
  }

  async runFullCheck(): Promise<HealthCheckResult> {
    this.issues = []

    this.checkOrphanedProducts()
    this.checkOrphanedOrders()
    this.checkOrphanedOrderItems()
    this.checkMissingProfileReferences()
    this.checkDuplicateSKUs()
    this.checkNegativeStock()
    this.checkInvalidPrices()
    this.checkOrderItemIntegrity()
    this.checkProfileConsistency()
    this.checkDataCorruption()

    const summary = {
      critical: this.issues.filter(i => i.severity === 'critical').length,
      warnings: this.issues.filter(i => i.severity === 'warning').length,
      info: this.issues.filter(i => i.severity === 'info').length
    }

    return {
      healthy: summary.critical === 0 && summary.warnings === 0,
      issues: this.issues,
    )
    if (orphanedOrders.length > 0) {
     
   

          id: o.id,
        })),
    
  }
  private checkOrphanedOrderItems(): void {
    


      this.issues.push({
        severity: 'critical',
        message: `${ordersWit
          type: 'order',
          name: o.customer_name
        autoFixable: false
    }

    const usedProfileIds
      ...thi

      pr

   

        message: `${unusedProfiles.leng
          type: 'profile',
    
        autoFixable: false
    }


    this.products.forEach(product =>
      if (!skuMap.has(ke
      }
    })
    const duplicates: Produ
      if (products.length > 1) {
      }

          id: o.id,
          name: o.customer_name
        })),
        autoFixable: false
      })
    }
  }

  private checkOrphanedOrderItems(): void {
    const validProductIds = new Set(this.products.map(p => p.id))
    
    const ordersWithOrphanedItems = this.orders.filter(order =>
      order.items.some(item => !validProductIds.has(item.product_id))
    )

    if (ordersWithOrphanedItems.length > 0) {
      this.issues.push({
        id: 'orphaned-order-items',
        severity: 'critical',
        category: 'orphan',
        message: `${ordersWithOrphanedItems.length} orden(es) contiene(n) items que referencian productos eliminados`,
        affectedItems: ordersWithOrphanedItems.map(o => ({
          type: 'order',
          id: o.id,
          name: o.customer_name
        })),
        autoFixable: false
      })
    }
  }

  private checkMissingProfileReferences(): void {
    const usedProfileIds = new Set([
      ...this.products.map(p => p.profile_id),
      ...this.orders.map(o => o.profile_id)
    ])

    const unusedProfiles = this.profiles.filter(
      profile => !usedProfileIds.has(profile.id) && profile.active
    )

    if (unusedProfiles.length > 0) {
      this.issues.push({
        id: 'unused-profiles',
        severity: 'info',
        category: 'consistency',
        message: `${unusedProfiles.length} perfil(es) activo(s) sin productos u órdenes asociadas`,
        affectedItems: unusedProfiles.map(p => ({
          type: 'profile',
          id: p.id,
          name: p.name
        })),
        autoFixable: false
      })
    }
  }

  private checkDuplicateSKUs(): void {
    const skuMap = new Map<string, ProductWithStock[]>()
    
    this.products.forEach(product => {
      const key = `${product.profile_id}-${product.sku}`
      if (!skuMap.has(key)) {
        skuMap.set(key, [])
      }
      skuMap.get(key)!.push(product)
    })

    const duplicates: ProductWithStock[] = []
    skuMap.forEach(products => {
      if (products.length > 1) {
        duplicates.push(...products)
      }
    })

    if (duplicates.length > 0) {
      this.issues.push({
        id: 'duplicate-skus',
        severity: 'warning',
        category: 'duplicate',
        message: `${duplicates.length} producto(s) con SKU duplicado en el mismo perfil`,
        affectedItems: duplicates.map(p => ({
          type: 'product',
          id: p.id,
          name: `${p.nombre} (SKU: ${p.sku})`
        })),
        autoFixable: false
      })
    }
  }

  private checkNegativeStock(): void {
    const negativeStockProducts = this.products.filter(
      product => product.stock_disponible < 0
    )

    if (negativeStockProducts.length > 0) {
      this.issues.push({
        id: 'negative-stock',
        severity: 'critical',
        category: 'integrity',
        message: `${negativeStockProducts.length} producto(s) con stock negativo`,
        affectedItems: negativeStockProducts.map(p => ({
          type: 'product',
          id: p.id,
          name: `${p.nombre} (Stock: ${p.stock_disponible})`
        })),
        autoFixable: true
      })
    }
  }

  private checkInvalidPrices(): void {
    const invalidPriceProducts = this.products.filter(
      product => product.precio <= 0 || !isFinite(product.precio) || isNaN(product.precio)
    )

    if (invalidPriceProducts.length > 0) {
      this.issues.push({
        id: 'invalid-prices',
        severity: 'critical',
        category: 'integrity',
        message: `${invalidPriceProducts.length} producto(s) con precio inválido`,
        affectedItems: invalidPriceProducts.map(p => ({
          type: 'product',
          id: p.id,
          name: `${p.nombre} (Precio: ${p.precio})`
        })),
        autoFixable: false
      })
    }
  }

  private checkOrderItemIntegrity(): void {
    const ordersWithInvalidItems = this.orders.filter(order => {
      if (!order.items || order.items.length === 0) return true
      
      return order.items.some(item => 
        item.cantidad <= 0 || 
        item.precio_unitario < 0 ||
        !isFinite(item.cantidad) ||
        !isFinite(item.precio_unitario) ||
        isNaN(item.cantidad) ||
        isNaN(item.precio_unitario)
      )
    })

    if (ordersWithInvalidItems.length > 0) {
      this.issues.push({
        id: 'invalid-order-items',
        severity: 'critical',
        category: 'integrity',
        message: `${ordersWithInvalidItems.length} orden(es) con items inválidos o vacíos`,
        affectedItems: ordersWithInvalidItems.map(o => ({
          type: 'order',
          id: o.id,
          name: o.customer_name
        })),
        autoFixable: false
      })
    }
  }

  private checkProfileConsistency(): void {
    const duplicateSlugs = new Map<string, Profile[]>()
    
    this.profiles.forEach(profile => {
      if (!duplicateSlugs.has(profile.slug)) {
        duplicateSlugs.set(profile.slug, [])
      }
      duplicateSlugs.get(profile.slug)!.push(profile)
    })

    const duplicates: Profile[] = []
    duplicateSlugs.forEach(profiles => {
      if (profiles.length > 1) {
        duplicates.push(...profiles)
      }
    })

    if (duplicates.length > 0) {
      this.issues.push({
        id: 'duplicate-profile-slugs',
        severity: 'critical',
        category: 'duplicate',
        message: `${duplicates.length} perfil(es) con slug duplicado`,
        affectedItems: duplicates.map(p => ({
          type: 'profile',
          id: p.id,
          name: `${p.name} (${p.slug})`
        })),
        autoFixable: false
      })
    }
  }

  private checkDataCorruption(): void {
    const corruptedProducts = this.products.filter(product => {
      try {
        return (
          !product.id ||
          !product.nombre ||
          !product.sku ||
          typeof product.id !== 'number' ||
          typeof product.nombre !== 'string' ||
          typeof product.sku !== 'string'
        )
      } catch {
        return true
      }
    })

    if (corruptedProducts.length > 0) {
      this.issues.push({
        id: 'corrupted-products',
        severity: 'critical',
        category: 'integrity',
        message: `${corruptedProducts.length} producto(s) con datos corruptos`,
        affectedItems: corruptedProducts.map(p => ({
          type: 'product',
          id: p.id || 0,
          name: p.nombre || 'Desconocido'
        })),
        autoFixable: false
      })
    }

    const corruptedOrders = this.orders.filter(order => {
      try {
        return (
          !order.id ||
          !order.customer_name ||
          typeof order.id !== 'number' ||
          typeof order.customer_name !== 'string' ||
          !Array.isArray(order.items)
        )
      } catch {
        return true
      }
    })

    if (corruptedOrders.length > 0) {
      this.issues.push({
        id: 'corrupted-orders',
        severity: 'critical',
        category: 'integrity',
        message: `${corruptedOrders.length} orden(es) con datos corruptos`,
        affectedItems: corruptedOrders.map(o => ({
          type: 'order',
          id: o.id || 0,
          name: o.customer_name || 'Desconocido'
        })),
        autoFixable: false
      })
    }
  }
}

export function autoFixIssues(
  issues: HealthCheckIssue[],
  products: ProductWithStock[],
  orders: OrderWithItems[],
  profiles: Profile[]
): {
























  return {
    products: updatedProducts,
    orders: updatedOrders,
    profiles: updatedProfiles,
    fixed
  }
}
