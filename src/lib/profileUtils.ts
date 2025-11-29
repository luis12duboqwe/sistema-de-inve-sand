import type { ProfileSettings } from './types'

export function formatPrice(price: number, settings?: ProfileSettings): string {
  const currency = settings?.currency || 'USD'
  const format = settings?.priceFormat || 'standard'
  
  let formattedNumber: string

  switch (format) {
    case 'comma':
      formattedNumber = price.toFixed(2).replace('.', ',')
      break
    case 'space':
      formattedNumber = price.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
      break
    default:
      formattedNumber = price.toFixed(2)
  }

  const currencySymbols: Record<string, string> = {
    'USD': '$',
    'EUR': '€',
    'MXN': '$',
    'ARS': '$',
    'COP': '$',
    'CLP': '$',
    'PEN': 'S/',
    'BRL': 'R$'
  }

  const symbol = currencySymbols[currency] || currency

  return `${symbol}${formattedNumber}`
}

export function calculateTax(price: number, settings?: ProfileSettings): number {
  if (!settings?.autoCalculateTax) return 0
  return price * (settings.taxRate / 100)
}

export function calculatePriceWithTax(price: number, settings?: ProfileSettings): number {
  if (!settings?.autoCalculateTax) return price
  return price + calculateTax(price, settings)
}

export function isLowStock(stock: number, settings?: ProfileSettings): boolean {
  const threshold = settings?.lowStockThreshold || 5
  return stock <= threshold && stock > 0
}

export function isOutOfStock(stock: number): boolean {
  return stock <= 0
}
