import { describe, it, expect, beforeEach, vi } from 'vitest'
import { inventoryService } from '../inventoryService'
import type { Product, Stock, Location, Profile } from '../types'

const store = vi.hoisted(() => new Map<string, any>())

vi.mock('../kvStorage', () => {
  const kv = {
    async get<T>(key: string): Promise<T | undefined> {
      return store.get(key)
    },
    async set<T>(key: string, value: T): Promise<void> {
      store.set(key, value)
    },
    async delete(key: string): Promise<void> {
      store.delete(key)
    },
    async keys(): Promise<string[]> {
      return Array.from(store.keys())
    }
  }
  return { getKV: () => kv, __kvStore: store }
})

const PROFILES_KEY = 'inventory-profiles'
const PRODUCTS_KEY = 'inventory-products'
const STOCK_KEY = 'inventory-stock'
const ORDERS_KEY = 'inventory-orders'
const ORDER_ITEMS_KEY = 'inventory-order-items'
const LOCATIONS_KEY = 'inventory-locations'
const SALES_PROFILES_KEY = 'inventory-sales-profiles'
const STOCK_HISTORY_KEY = 'inventory-stock-history'
const PRODUCT_IMEIS_KEY = 'inventory-product-imeis'
const TRADE_INS_KEY = 'inventory-trade-ins'
const RETURNS_KEY = 'inventory-returns'
const RETURN_ITEMS_KEY = 'inventory-return-items'
const STOCK_TRANSFERS_KEY = 'inventory-stock-transfers'
const IMEI_HISTORY_KEY = 'inventory-imei-history'
const SUPPLIERS_KEY = 'inventory-suppliers'
const BANKS_KEY = 'inventory-banks'

describe('inventoryService local mode', () => {
  beforeEach(async () => {
    store.clear()
    const profile: Profile = { id: 1, name: 'Demo', slug: 'demo', active: true }
    const location: Location = { id: 1, nombre: 'Tienda', tipo: 'tienda', activo: true, created_at: new Date().toISOString() }
    const product: Product = {
      id: 1,
      profile_id: 1,
      sku: 'SKU-1',
      nombre: 'Accesorio',
      categoria: 'accesorio',
      marca: 'X',
      modelo: 'Y',
      condicion: 'nuevo',
      precio: 1000,
      moneda: 'HNL',
      garantia_meses: 12,
      activo: true,
      is_serialized: false
    }
    const stock: Stock = { id: 1, product_id: 1, location_id: 1, cantidad_disponible: 5, cantidad_reservada: 0 }

    store.set(PROFILES_KEY, [profile])
    store.set(LOCATIONS_KEY, [location])
    store.set(SALES_PROFILES_KEY, [])
    store.set(PRODUCTS_KEY, [product])
    store.set(STOCK_KEY, [stock])
    store.set(ORDERS_KEY, [])
    store.set(ORDER_ITEMS_KEY, [])
    store.set(TRADE_INS_KEY, [])
    store.set(STOCK_HISTORY_KEY, [])
    store.set(PRODUCT_IMEIS_KEY, [])
    store.set(RETURNS_KEY, [])
    store.set(RETURN_ITEMS_KEY, [])
    store.set(STOCK_TRANSFERS_KEY, [])
    store.set(IMEI_HISTORY_KEY, [])
    store.set(SUPPLIERS_KEY, [])
    store.set(BANKS_KEY, [
      {
        id: 123,
        name: 'Banco Demo',
        active: true,
        normal_card_rate: 0.04,
        financing_options: [
          { id: 1, bank_id: 123, months: 2, rate: 0, active: true }
        ]
      }
    ])
  })

  it('creates order, excludes gifts from total, stores financing details and updates stock', async () => {
    const order = await inventoryService.createOrder({
      profile_slug: 'demo',
      customer_name: 'Cliente',
      customer_phone: '+50499999999',
      canal: 'whatsapp',
      metodo_pago: 'financiamiento',
      source_location_id: 1,
      items: [
        { product_id: 1, cantidad: 1, es_regalo_promocion: true }
      ],
      financing_data: {
        bank_id: 123,
        months: 2,
        down_payment: 0
      }
    })

    expect(order.total).toBe(0)
    expect(order.financing_details).toBeTruthy()

    const parsed = JSON.parse(order.financing_details || '{}')
    expect(parsed.financed_amount).toBe(0)
    expect(parsed.monthly_payment).toBe(0)

    const stockAfter = store.get(STOCK_KEY) as Stock[]
    expect(stockAfter[0].cantidad_disponible).toBe(4)
  })
})
