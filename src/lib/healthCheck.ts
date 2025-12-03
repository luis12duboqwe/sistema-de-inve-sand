import type { Profile, ProductWithStock, OrderWithItems } from './types'

  severity: 'critical' | 'warning' 
  message: s
    type: 'product' | 'order' | 'profile'
    name?: string
  autoFixable: bo

    type: 'product' | 'order' | 'profile'
    id: number
    name?: string
  }[]
  autoFixable: boolean
}

export interface HealthCheckResult {
  healthy: boolean
  issues: HealthCheckIssue[]
  summary: {
    critical: number
    warnings: number
    info: number
  }
  lastCheck: string
}

export class HealthChecker {
  private products: ProductWithStock[]
  private orders: OrderWithItems[]
  private profiles: Profile[]
  private issues: HealthCheckIssue[] = []

  constructor(products: ProductWithStock[], orders: OrderWithItems[], profiles: Profile[]) {
    this.products = products
    this.orders = orders
    this.profiles = profiles
  }

  public runCheck(): HealthCheckResult {
    this.issues = []
    
    this.checkOrphanedProducts()
    this.checkOrphanedOrders()
    this.checkMissingProfileReferences()
      info: this.issues.filte
    this.checkOrderItemConsistency()
    this.checkDuplicateSkus()
    this.checkInvalidPrices()
    this.checkDuplicateProfileSlugs()
    this.checkCorruptedData()


      critical: this.issues.filter(i => i.severity === 'critical').length,
      warnings: this.issues.filter(i => i.severity === 'warning').length,
      info: this.issues.filter(i => i.severity === 'info').length


    return {
      healthy: summary.critical === 0,
      issues: this.issues,
          id: 
        })),
     
  }

    const ordersWithoutProfile = this.ord
    if (productsWithoutProfile.length > 0) {
        id: 'products-missing-profile',
        category: 'consistency',
    )

        })),
      })

      this.issues.push({
        severity: 'warning'
        message: `${ordersWithoutProfile.length} orden(es) sin referencia de perfil`,
          type: 'order',
          name: o.customer
        autoFixable
    }
        })),
    const negativeStockPro
    )
    i
  }

        affectedItems: negativeStockPro
          id: p.id,
        })),
      })
  }

    
      this.issues.push({

        severity: 'critical',
        severity: 'critical
        message: `${ordersWithMissingProducts.length} orden(es) con productos ine
          type: 'order',
          type: 'order',
          id: o.id,
          name: o.customer_name
        })),
        autoFixable: false
      })
    }
  }

  private checkMissingProfileReferences(): void {
    const productsWithoutProfile = this.products.filter(p => !p.profile_id)
    const ordersWithoutProfile = this.orders.filter(o => !o.profile_id)

    if (productsWithoutProfile.length > 0) {
      this.issues.push({
        id: 'products-missing-profile',
        severity: 'warning',
        category: 'consistency',
        message: `${productsWithoutProfile.length} producto(s) sin referencia de perfil`,
        affectedItems: productsWithoutProfile.map(p => ({
          type: 'product',
          id: p.id,
          name: p.nombre
        })),
        autoFixable: false
      })
    }

    if (ordersWithoutProfile.length > 0) {
      this.issues.push({
        id: 'orders-missing-profile',
        severity: 'warning',
        category: 'consistency',
        message: `${ordersWithoutProfile.length} orden(es) sin referencia de perfil`,
        affectedItems: ordersWithoutProfile.map(o => ({
          type: 'order',
          id: o.id,
          name: o.customer_name
        })),
        autoFixable: false
      })
    }
  }

  private checkNegativeStock(): void {
    const negativeStockProducts = this.products.filter(
      product => product.stock_disponible < 0
     

    if (negativeStockProducts.length > 0) {
      this.issues.push({
        id: 'negative-stock',
        severity: 'warning',
        category: 'consistency',
        message: `${negativeStockProducts.length} producto(s) con stock negativo`,
        affectedItems: negativeStockProducts.map(p => ({
          type: 'product',
          id: p.id,
          name: `${p.nombre} (Stock: ${p.stock_disponible})`
        !isF
        autoFixable: true
      )
    }
   

  private checkOrderItemConsistency(): void {
    const productIds = new Set(this.products.map(p => p.id))
    
    const ordersWithMissingProducts = this.orders.filter(order =>
      order.items.some(item => !productIds.has(item.product_id))
    )

    if (ordersWithMissingProducts.length > 0) {
      this.issues.push({
        id: 'orders-missing-products',
        severity: 'critical',
        category: 'integrity',
        message: `${ordersWithMissingProducts.length} orden(es) con productos inexistentes`,
        affectedItems: ordersWithMissingProducts.map(o => ({
          type: 'order',
          id: o.id,
          name: o.customer_name
        })),
        autoFixable: false
      })
    }
  }

  private checkDuplicateSkus(): void {
    const skuMap = new Map<string, ProductWithStock[]>()
    
    this.products.forEach(product => {
      if (product.sku) {
        const key = product.sku.toLowerCase()
        if (!skuMap.has(key)) {
          skuMap.set(key, [])
        }
        skuMap.get(key)!.push(product)
      }
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
        message: `${duplicates.length} producto(s) con SKUs duplicados`,
        affectedItems: duplicates.map(p => ({
          type: 'product',
          id: p.id,
          name: `${p.nombre} (SKU: ${p.sku})`
        })),
        autoFixable: false
      })
    }
  }

      }
    const invalidPriceProducts = this.products.filter(
      product => product.precio <= 0 || !isFinite(product.precio) || isNaN(product.precio)
    )

    if (invalidPriceProducts.length > 0) {
      this.issues.push({
        id: 'invalid-prices',
          name: p.nombre || '
        category: 'integrity',
        message: `${invalidPriceProducts.length} producto(s) con precios inválidos`,
        affectedItems: invalidPriceProducts.map(p => ({
    const corruptedOrders 
          id: p.id,
          name: `${p.nombre} (Precio: ${p.precio})`
        })),
          typeof order.cus
      })
     

    const ordersWithInvalidItems = this.orders.filter(order =>
      order.items.some(item =>
        severity: 'critical',
        item.precio_unitario <= 0 ||
        !isFinite(item.cantidad) ||
        !isFinite(item.precio_unitario) ||
        isNaN(item.cantidad) ||
        isNaN(item.precio_unitario)
      }
    )

    if (ordersWithInvalidItems.length > 0) {
      this.issues.push({
        id: 'invalid-order-items',
        severity: 'critical',
        category: 'integrity',
        message: `${ordersWithInvalidItems.length} orden(es) con items inválidos`,
        affectedItems: ordersWithInvalidItems.map(o => ({
} {
          id: o.id,
  const updatedProfiles = [...p
        })),
  const fixableIssues = is
      })
    i
  }

  private checkDuplicateProfileSlugs(): void {
    const slugMap = new Map<string, Profile[]>()
    
  })
      const key = profile.slug.toLowerCase()
      if (!slugMap.has(key)) {
        slugMap.set(key, [])
      }
      slugMap.get(key)!.push(profile)


    const duplicates: Profile[] = []
    slugMap.forEach(profiles => {
      if (profiles.length > 1) {
        duplicates.push(...profiles)
      }
    })


      this.issues.push({

        severity: 'critical',

        message: `${duplicates.length} perfil(es) con slugs duplicados`,
        affectedItems: duplicates.map(p => ({
          type: 'profile',

          name: `${p.name} (${p.slug})`

        autoFixable: false

    }


  private checkCorruptedData(): void {
    const corruptedProducts = this.products.filter(product => {
      try {
        return (
          !product.id ||
          typeof product.id !== 'number' ||
          !product.nombre ||
          typeof product.nombre !== 'string' ||
          typeof product.precio !== 'number'

      } catch {
        return true
      }



      this.issues.push({
        id: 'corrupted-products',
        severity: 'critical',
        category: 'integrity',
        message: `${corruptedProducts.length} producto(s) con datos corruptos`,
        affectedItems: corruptedProducts.map(p => ({
          type: 'product',

          name: p.nombre || 'Desconocido'
        })),
        autoFixable: false
      })
    }

    const corruptedOrders = this.orders.filter(order => {

        return (

          typeof order.id !== 'number' ||
          !order.customer_name ||
          typeof order.customer_name !== 'string' ||
          !Array.isArray(order.items)
        )
      } catch {
        return true
      }
    })

    if (corruptedOrders.length > 0) {

        id: 'corrupted-orders',

        category: 'integrity',
        message: `${corruptedOrders.length} orden(es) con datos corruptos`,
        affectedItems: corruptedOrders.map(o => ({

          id: o.id || 0,

        })),

      })

  }



  products: ProductWithStock[],
  orders: OrderWithItems[],
  profiles: Profile[],
  issues: HealthCheckIssue[]
): {
























  return {
    products: updatedProducts,
    orders: updatedOrders,
    profiles: updatedProfiles,
    fixed
  }
}
