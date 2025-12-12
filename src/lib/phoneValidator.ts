export function sanitizePhoneNumber(phone: unknown): string {
  if (phone === null || phone === undefined) {
    return ''
  }
  
  const phoneStr = String(phone).trim()
  return phoneStr
}

export function validatePhoneNumber(phone: unknown): { valid: boolean; phone: string; error?: string } {
  const sanitized = sanitizePhoneNumber(phone)
  
  if (!sanitized) {
    return {
      valid: false,
      phone: sanitized,
      error: 'El número de teléfono es requerido'
    }
  }

  // Remove all non-digit characters
  const digits = sanitized.replace(/\D/g, '')
  
  if (digits.length < 8) {
    return {
      valid: false,
      phone: sanitized,
      error: 'El número de teléfono debe tener al menos 8 dígitos'
    }
  }
  
  return {
    valid: true,
    phone: sanitized
  }
}
