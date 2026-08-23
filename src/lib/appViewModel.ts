import type { Location, OrderWithItems, ProductWithStock, User } from './types'

export function hasAppPermission(useAPI: boolean, currentUser: User | null, slug: string): boolean {
  if (!useAPI) return true
  if (currentUser?.is_superuser) return true
  return currentUser?.role?.permissions?.some(permission => permission.slug === slug) ?? false
}

export interface LocationSnapshot {
  id: number
  nombre: string
  tipo: string
  productsAtLocation: number
  unitsAtLocation: number
}

export interface MultiStoreViewModel {
  activeLocations: Location[]
  productsWithLocationTracking: ProductWithStock[]
  totalTrackedUnits: number
  outOfStockProducts: number
  locatedOrders: number
  locationSnapshots: LocationSnapshot[]
}

export function buildMultiStoreViewModel(
  locations: Location[],
  products: ProductWithStock[],
  orders: OrderWithItems[],
): MultiStoreViewModel {
  const activeLocations = locations.filter(location => location.activo)
  const productsWithLocationTracking = products.filter(product => (product.stock_items?.length ?? 0) > 0)
  const totalTrackedUnits = products.reduce(
    (total, product) => total + Number(product.stock_disponible || 0),
    0,
  )
  const outOfStockProducts = products.filter(product => Number(product.stock_disponible || 0) <= 0).length
  const locatedOrders = orders.filter(order => Boolean(order.source_location_id)).length

  const locationSnapshots = activeLocations
    .map(location => {
      const productsAtLocation = products.filter(product =>
        product.stock_items?.some(
          stockItem => stockItem.location_id === location.id && Number(stockItem.cantidad_disponible || 0) > 0,
        ),
      )
      const unitsAtLocation = products.reduce((total, product) => {
        const stockItem = product.stock_items?.find(item => item.location_id === location.id)
        return total + Number(stockItem?.cantidad_disponible || 0)
      }, 0)

      return {
        id: location.id,
        nombre: location.nombre,
        tipo: location.tipo,
        productsAtLocation: productsAtLocation.length,
        unitsAtLocation,
      }
    })
    .sort((a, b) => b.unitsAtLocation - a.unitsAtLocation)
    .slice(0, 4)

  return {
    activeLocations,
    productsWithLocationTracking,
    totalTrackedUnits,
    outOfStockProducts,
    locatedOrders,
    locationSnapshots,
  }
}
