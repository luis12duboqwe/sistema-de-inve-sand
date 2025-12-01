import type { Profile, Product, Stock, Order, OrderItem, ProfileSettings } from './types'

const defaultProfileSettings: ProfileSettings = {
  currency: 'HNL',
  taxRate: 15,
  lowStockThreshold: 5,
  enableNotifications: true,
  defaultPaymentMethod: 'efectivo',
  defaultChannel: 'whatsapp',
  autoCalculateTax: false,
  priceFormat: 'standard',
  businessAddress: '',
  businessPhone: '',
  businessEmail: ''
}

export const initialProfiles: Profile[] = [
  {
    id: 1,
    name: 'Softmobile',
    slug: 'softmobile',
    active: true,
    settings: {
      ...defaultProfileSettings,
      businessAddress: 'Honduras',
      businessPhone: '+504 0000-0000'
    }
  }
]

export const initialProducts: Product[] = [
  {
    id: 1,
    profile_id: 1,
    sku: 'IPH13-128-BLK-NEW',
    nombre: 'iPhone 13',
    categoria: 'celular',
    marca: 'Apple',
    modelo: 'iPhone 13',
    capacidad: '128GB',
    condicion: 'nuevo',
    precio: 18500,
    moneda: 'HNL',
    garantia_meses: 12,
    activo: true
  },
  {
    id: 2,
    profile_id: 1,
    sku: 'SAM-S23-256-BLU-NEW',
    nombre: 'Samsung Galaxy S23',
    categoria: 'celular',
    marca: 'Samsung',
    modelo: 'Galaxy S23',
    capacidad: '256GB',
    condicion: 'nuevo',
    precio: 16800,
    moneda: 'HNL',
    garantia_meses: 12,
    activo: true
  },
  {
    id: 3,
    profile_id: 1,
    sku: 'XIA-RED12-128-BLK-NEW',
    nombre: 'Xiaomi Redmi Note 12',
    categoria: 'celular',
    marca: 'Xiaomi',
    modelo: 'Redmi Note 12',
    capacidad: '128GB',
    condicion: 'nuevo',
    precio: 5500,
    moneda: 'HNL',
    garantia_meses: 6,
    activo: true
  },
  {
    id: 4,
    profile_id: 1,
    sku: 'ACC-CASE-IPH13-SIL',
    nombre: 'Funda de Silicona iPhone 13',
    categoria: 'accesorio',
    marca: 'Generic',
    modelo: 'Silicone Case',
    capacidad: 'N/A',
    condicion: 'nuevo',
    precio: 150,
    moneda: 'HNL',
    garantia_meses: 0,
    activo: true
  },
  {
    id: 5,
    profile_id: 1,
    sku: 'ACC-CHARGER-USBC-20W',
    nombre: 'Cargador USB-C 20W',
    categoria: 'accesorio',
    marca: 'Generic',
    modelo: 'Fast Charger',
    capacidad: '20W',
    condicion: 'nuevo',
    precio: 280,
    moneda: 'HNL',
    garantia_meses: 3,
    activo: true
  },
  {
    id: 6,
    profile_id: 1,
    sku: 'IPH14PRO-256-GOLD-REF',
    nombre: 'iPhone 14 Pro',
    categoria: 'celular',
    marca: 'Apple',
    modelo: 'iPhone 14 Pro',
    capacidad: '256GB',
    condicion: 'reacondicionado',
    precio: 24500,
    moneda: 'HNL',
    garantia_meses: 6,
    activo: true
  }
]

export const initialStock: Stock[] = [
  { id: 1, product_id: 1, cantidad_disponible: 15 },
  { id: 2, product_id: 2, cantidad_disponible: 8 },
  { id: 3, product_id: 3, cantidad_disponible: 25 },
  { id: 4, product_id: 4, cantidad_disponible: 50 },
  { id: 5, product_id: 5, cantidad_disponible: 30 },
  { id: 6, product_id: 6, cantidad_disponible: 3 }
]

export const initialOrders: Order[] = []
export const initialOrderItems: OrderItem[] = []
