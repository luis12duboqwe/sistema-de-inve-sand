import type { OrderWithItems, ProductWithStock, AdvancedSearchFilters, ReportData } from './types'
import { startOfMonth, endOfMonth, isWithinInterval, format } from 'date-fns'
import { isFinalSaleStatus } from './orderStatus'

export function filterOrdersByAdvancedSearch(
  orders: OrderWithItems[],
  filters: AdvancedSearchFilters
): OrderWithItems[] {
  return orders.filter(order => {
    if (filters.dateRange) {
      const orderDate = new Date(order.created_at)
      const isInRange = isWithinInterval(orderDate, {
        start: filters.dateRange.from,
        end: filters.dateRange.to
      })
      if (!isInRange) return false
    }

    if (filters.minAmount !== undefined && order.total < filters.minAmount) {
      return false
    }

    if (filters.maxAmount !== undefined && order.total > filters.maxAmount) {
      return false
    }

    if (filters.customerName) {
      const searchTerm = filters.customerName.toLowerCase()
      if (!order.customer_name.toLowerCase().includes(searchTerm)) {
        return false
      }
    }

    if (filters.customerPhone) {
      const searchTerm = filters.customerPhone.toLowerCase()
      if (!order.customer_phone.toLowerCase().includes(searchTerm)) {
        return false
      }
    }

    if (filters.productId !== undefined) {
      const hasProduct = order.items.some(item => item.product_id === filters.productId)
      if (!hasProduct) return false
    }

    return true
  })
}

export function generateMonthlyTrends(orders: OrderWithItems[], months: number = 12): Array<{
  month: string
  revenue: number
  orders: number
}> {
  const now = new Date()
  const trends: Array<{ month: string; revenue: number; orders: number }> = []

  for (let i = months - 1; i >= 0; i--) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const monthStart = startOfMonth(date)
    const monthEnd = endOfMonth(date)

    const monthOrders = orders.filter(order => {
      const orderDate = new Date(order.created_at)
      return isWithinInterval(orderDate, { start: monthStart, end: monthEnd }) &&
             isFinalSaleStatus(order.estado)
    })

    const revenue = monthOrders.reduce((sum, order) => sum + order.total, 0)

    trends.push({
      month: format(date, 'MMM yyyy'),
      revenue,
      orders: monthOrders.length
    })
  }

  return trends
}

export function generateReportData(
  orders: OrderWithItems[],
  products: ProductWithStock[]
): ReportData {
  const completedOrders = orders.filter(o => isFinalSaleStatus(o.estado))
  const totalRevenue = completedOrders.reduce((sum, order) => sum + order.total, 0)

  const productSales = new Map<number, { quantity: number; revenue: number }>()
  
  completedOrders.forEach(order => {
    order.items.forEach(item => {
      if (!item.es_regalo_promocion) {
        const current = productSales.get(item.product_id) || { quantity: 0, revenue: 0 }
        productSales.set(item.product_id, {
          quantity: current.quantity + item.cantidad,
          revenue: current.revenue + (item.cantidad * item.precio_unitario)
        })
      }
    })
  })

  const topProducts = Array.from(productSales.entries())
    .map(([productId, sales]) => {
      const product = products.find(p => p.id === productId)
      return product ? {
        product,
        quantity: sales.quantity,
        revenue: sales.revenue
      } : null
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, 10)

  const monthlyTrends = generateMonthlyTrends(orders)

  const totalCost = topProducts.reduce((sum, item) => {
    return sum + (item.product.precio * 0.6 * item.quantity)
  }, 0)
  const profitMargin = totalRevenue > 0 ? ((totalRevenue - totalCost) / totalRevenue) * 100 : 0

  return {
    totalRevenue,
    totalOrders: completedOrders.length,
    topProducts,
    monthlyTrends,
    profitMargin
  }
}

export function searchOrdersByCustomer(
  orders: OrderWithItems[],
  searchTerm: string
): OrderWithItems[] {
  const term = searchTerm.toLowerCase()
  return orders.filter(order => {
    const nameMatch = order.customer_name.toLowerCase().includes(term)
    const phoneMatch = order.customer_phone.includes(term)
    return nameMatch || phoneMatch
  })
}

export function getCustomerHistory(
  orders: OrderWithItems[],
  customerPhone: string
): {
  orders: OrderWithItems[]
  totalSpent: number
  averageOrderValue: number
  orderCount: number
} {
  const customerOrders = orders
    .filter(o => o.customer_phone === customerPhone)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  const completedOrders = customerOrders.filter(o => isFinalSaleStatus(o.estado))
  const totalSpent = completedOrders.reduce((sum, order) => sum + order.total, 0)
  const averageOrderValue = completedOrders.length > 0 ? totalSpent / completedOrders.length : 0

  return {
    orders: customerOrders,
    totalSpent,
    averageOrderValue,
    orderCount: customerOrders.length
  }
}

export function getProductProfitability(
  product: ProductWithStock,
  orders: OrderWithItems[]
): {
  unitsSold: number
  revenue: number
  estimatedCost: number
  estimatedProfit: number
  profitMargin: number
} {
  const completedOrders = orders.filter(o => isFinalSaleStatus(o.estado))
  
  let unitsSold = 0
  let revenue = 0

  completedOrders.forEach(order => {
    order.items.forEach(item => {
      if (item.product_id === product.id && !item.es_regalo_promocion) {
        unitsSold += item.cantidad
        revenue += item.cantidad * item.precio_unitario
      }
    })
  })

  const estimatedCost = product.precio * 0.6 * unitsSold
  const estimatedProfit = revenue - estimatedCost
  const profitMargin = revenue > 0 ? (estimatedProfit / revenue) * 100 : 0

  return {
    unitsSold,
    revenue,
    estimatedCost,
    estimatedProfit,
    profitMargin
  }
}
