import type { ProfileSettings } from './types'

export function formatPrice(
  amount: number,
  settings?: ProfileSettings
): string {
  const currency = settings?.currency || 'HNL'
  const format = settings?.priceFormat || 'standard'
  
  let formattedNumber: string
  
  switch (format) {
    case 'comma':
      formattedNumber = amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, '.').replace('.', ',')
      break
    case 'space':
      formattedNumber = amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
      break
    case 'standard':
    default:
      formattedNumber = amount.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
      break
  }
  
  return `${currency} ${formattedNumber}`
}

export function calculateTax(
  amount: number,
  settings?: ProfileSettings
): number {
  if (!settings?.autoCalculateTax || !settings?.taxRate) {
    return 0
  }
  
  return (amount * settings.taxRate) / 100
}

export function calculateTotal(
  subtotal: number,
  settings?: ProfileSettings
): number {
  const tax = calculateTax(subtotal, settings)
  return subtotal + tax
}

export function getCurrencySymbol(currency: string): string {
  const symbols: Record<string, string> = {
    'HNL': 'L',
    'USD': '$',
    'MXN': '$',
    'EUR': '€'
  }
  
  return symbols[currency] || currency
}
export function formatPrice(
  amount: number,
  settings?: ProfileSettings
): string {
  const currency = settings?.currency || 'HNL'
  const format = settings?.priceFormat || 'standard'
  
  let formattedNumber: string
  
  switch (format) {
    case 'comma':
      formattedNumber = amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, '.').replace('.', ',')
      break
    case 'space':
      formattedNumber = amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
      break
    case 'standard':
    default:
      formattedNumber = amount.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
      break
  }
  
  return `${currency} ${formattedNumber}`
}

export function calculateTax(
  amount: number,
  settings?: ProfileSettings
): number {
  if (!settings?.autoCalculateTax || !settings?.taxRate) {
    return 0
  }
  
  return (amount * settings.taxRate) / 100
}

export function calculateTotal(
  subtotal: number,
  settings?: ProfileSettings
): number {
  const tax = calculateTax(subtotal, settings)
  return subtotal + tax
}

export function getCurrencySymbol(currency: string): string {
  const symbols: Record<string, string> = {
    'HNL': 'L',
    'USD': '$',
    'MXN': '$',
    'EUR': '€'
  }
  
  return symbols[currency] || currency
}
