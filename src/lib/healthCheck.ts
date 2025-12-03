import type { Profile, ProductWithStock, OrderWithItems } from './types'

export interface HealthCheckIssue {
  id: string
  severity: 'critical' | 'warning' | 'info'
  category: 'orphan' | 'duplicate' | 'integrity' | 'consistency'
  message: string
  affectedItems: {
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

    this.check
    this.checkMissingProfileRefer
    this.checkNegativeStock()
    this.checkOrderItem
    t
    const summary = {
      warnings: this.iss
    }
   

      lastCheck: new Date().toISOString()
  }

    const orphanedProducts = thi
    )
    if (orphanedProducts.length > 
        id: 'orphaned-products',
        category: 'orphan',
        affectedItems: orphan
          id: p.id,
        })),
      })
  }

    const orphanedOrd
    )
    if (orphanedOrders.length > 0) {
        id: 'orphaned-orders',
     

          id
        })),
      })
      summary,
      lastCheck: new Date().toISOString()
    }
  }

  private checkOrphanedProducts(): void {
    const validProfileIds = new Set(this.profiles.map(p => p.id))
    const orphanedProducts = this.products.filter(
      product => !validProfileIds.has(product.profile_id)
    i

    if (orphanedProducts.length > 0) {
      this.issues.push({
        id: 'orphaned-products',
        severity: 'critical',
        category: 'orphan',
        message: `${orphanedProducts.length} producto(s) sin perfil asociado válido`,
        affectedItems: orphanedProducts.map(p => ({
          type: 'product',
          id: p.id,
          name: p.nombre
      ...thi
        autoFixable: false
      })
    }
   

  private checkOrphanedOrders(): void {
    const validProfileIds = new Set(this.profiles.map(p => p.id))
    const orphanedOrders = this.orders.filter(
      order => !validProfileIds.has(order.profile_id)
    )

    if (orphanedOrders.length > 0) {
      })
        id: 'orphaned-orders',

        category: 'orphan',
        message: `${orphanedOrders.length} orden(es) sin perfil asociado válido`,
        affectedItems: orphanedOrders.map(o => ({
      if (!skuMap.has(ke

    const negativeStockProducts
    )
    if (negativeStockProdu
        
     
   

        })),
      })
  }
  private checkInvalidPrices(): void {
      product => product.precio <= 0 || !isFinite(product.precio) || 


        severity: 'critical',
        message: `${inva
          type: 'product',
          name: `${p.nombre} 
        autoFixable: false
    }

    const ordersWithInva
      
        item.cantidad <= 0 || 
        !isF
        isNaN(item.cantida
      )

   

        message: `${ordersWithInvalidItems.length
          type: 'order',
          name: o.customer_name
        autoFixable: false
    }

    const duplicateSlugs = new Map<string, Profi
    this.profiles.forEach(profile => {
     


    duplicateSlugs.forEa
        duplicates.push(...pro
    })
    if (duplicates.length > 0) {
        id: 'duplicate-profile-slugs',
        category: 'duplicate',
        affectedItems: dup
          id: p.id,
        })),
      })
  }
  privat
     
   

          typeof product.nombre !== 's
        )
    
    })
    if (corruptedProducts.length > 0) {
        id: 'corrupted-produc
        category: 'integrit
       
          id: p.id || 0,
      


      try {
          !order.id ||
          typeof order.id !== 'numbe
       
      


      this.issues.push({
        severity: 'critical',
        message: `${corrupte
          type: 'order',
          name: o.customer_name || 'Desconocido'
        autoFixable: false
    }
}
export function autoFixIssues(
  products: 
  profiles: Profile[]
  produc
  pro
} {

  const fixed: string[] = []
  const fixableIssues = issues.filter(i => i.autoFixabl
  fixableIssues.forEach(issue => {
     

          fixed.push(`Corregido stock negat
      })
  })
  return {
    orders: updatedOrders,
    fixed
}

































































































































































  products: ProductWithStock[]
  orders: OrderWithItems[]
  profiles: Profile[]
  fixed: string[]
} {
  const updatedProducts = [...products]
  const updatedOrders = [...orders]
  const updatedProfiles = [...profiles]
  const fixed: string[] = []

  const fixableIssues = issues.filter(i => i.autoFixable)

  fixableIssues.forEach(issue => {
    if (issue.id === 'negative-stock') {
      issue.affectedItems.forEach(item => {
        const productIndex = updatedProducts.findIndex(p => p.id === item.id)
        if (productIndex !== -1 && updatedProducts[productIndex].stock_disponible < 0) {
          updatedProducts[productIndex].stock_disponible = 0
          fixed.push(`Corregido stock negativo para "${item.name}"`)
        }
      })
    }
  })








