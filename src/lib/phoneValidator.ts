const ALLOWED_PHONE_REGEX = /^[0-9+\s\-()]+$/
const MAX_PHONE_LENGTH = 20

export function sanitizePhoneNumber(phone: unknown): string {
  if (phone === null || phone === undefined) {
    return ''
  }

  return String(phone).trim()
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

  if (sanitized.length > MAX_PHONE_LENGTH) {
    return {
      valid: false,
      phone: sanitized,
      error: `El número de teléfono no puede exceder ${MAX_PHONE_LENGTH} caracteres`
    }
  }

  if (!ALLOWED_PHONE_REGEX.test(sanitized)) {
    return {
      valid: false,
      phone: sanitized,
      error: 'Formato de teléfono inválido. Debe contener solo dígitos, espacios y los caracteres: + - ( )'
    }
  }

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
