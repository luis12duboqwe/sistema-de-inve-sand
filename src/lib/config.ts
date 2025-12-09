/**
 * Configuración centralizada del sistema V2.0
 * 
 * Este archivo centraliza todas las configuraciones del frontend,
 * evitando valores hardcodeados en múltiples componentes.
 */

/**
 * Obtiene la URL base de la API desde KV storage o retorna el default
 * @returns URL base de la API (sin trailing slash)
 */
export async function getApiUrl(): Promise<string> {
  try {
    // Intentar obtener desde KV storage
    const { getKV } = await import('./kvStorage')
    const kv = getKV()
    const customUrl = await kv.get<string>('settings_api_url')
    
    if (customUrl && customUrl.trim()) {
      // Remover trailing slash si existe
      return customUrl.trim().replace(/\/$/, '')
    }
  } catch (error) {
    console.warn('No se pudo obtener API URL desde KV, usando default:', error)
  }
  
  // Default: backend en puerto 8000
  return 'http://localhost:8000'
}

/**
 * URL base de la API (valor por defecto)
 * Para uso sincrónico, pero preferir getApiUrl() para uso asíncrono
 */
export const DEFAULT_API_URL = 'http://localhost:8000'

/**
 * Configuración de paginación
 */
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 50,
  MAX_PAGE_SIZE: 100,
  MIN_PAGE_SIZE: 10,
} as const

/**
 * Configuración de stock
 */
export const STOCK = {
  MIN_STOCK_WARNING: 5, // Mostrar advertencia cuando stock < 5
  CRITICAL_STOCK: 2,    // Stock crítico cuando < 2
} as const

/**
 * Configuración de órdenes
 */
export const ORDERS = {
  DEFAULT_STATUS: 'pendiente',
  COMPLETED_STATUS: 'completada',
  CANCELLED_STATUS: 'cancelada',
} as const

/**
 * Configuración de intervalos de sincronización
 */
export const SYNC = {
  HEALTH_CHECK_INTERVAL: 30000,     // 30 segundos
  AUTO_SYNC_INTERVAL: 60000,        // 1 minuto
  RETRY_DELAY: 5000,                // 5 segundos
} as const

/**
 * Configuración de UI
 */
export const UI = {
  TOAST_DURATION: 3000,             // 3 segundos
  DEBOUNCE_DELAY: 300,              // 300ms para búsquedas
  ANIMATION_DURATION: 200,          // 200ms para animaciones
} as const

/**
 * Monedas soportadas
 */
export const CURRENCIES = {
  DEFAULT: 'HNL',
  SUPPORTED: ['HNL', 'USD', 'EUR'] as const,
} as const

/**
 * Canales de venta
 */
export const SALES_CHANNELS = {
  WHATSAPP: 'whatsapp',
  FACEBOOK: 'facebook', 
  INSTAGRAM: 'instagram',
} as const

/**
 * Tipos de ubicación
 */
export const LOCATION_TYPES = {
  TIENDA: 'tienda',
  BODEGA: 'bodega',
  OFICINA: 'oficina',
} as const

/**
 * Tipos de perfil de venta
 */
export const SALES_PROFILE_TYPES = {
  BOT_IA: 'bot_ia',
  VENDEDOR_HUMANO: 'vendedor_humano',
  SISTEMA_AUTOMATICO: 'sistema_automatico',
} as const

/**
 * Estados de transferencia de stock
 */
export const TRANSFER_STATUS = {
  PENDIENTE: 'pendiente',
  CONFIRMADA: 'confirmada',
  RECHAZADA: 'rechazada',
  CANCELADA: 'cancelada',
} as const

/**
 * Validaciones de negocio
 */
export const VALIDATION = {
  MIN_PRODUCT_PRICE: 0.01,
  MAX_PRODUCT_PRICE: 999999.99,
  MIN_ORDER_ITEMS: 1,
  MAX_ORDER_ITEMS: 100,
  MIN_TRANSFER_QUANTITY: 1,
  MAX_TRANSFER_QUANTITY: 9999,
} as const
