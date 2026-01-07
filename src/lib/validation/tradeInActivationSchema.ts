import { z } from 'zod'
import type { ValidationIssue, ValidationResult } from './types'

export interface TradeInActivationDraft {
  imei: string
  color?: string
  capacidad?: string
  precio: string
  targetLocationId: string
}

const schema = z.object({
  imei: z
    .string()
    .trim()
    .min(10, { message: 'El IMEI debe tener al menos 10 dígitos' })
    .max(20, { message: 'El IMEI no puede exceder 20 caracteres' })
    .regex(/^[0-9A-Za-z-]+$/u, { message: 'El IMEI solo puede contener números y guiones' }),
  color: z
    .string()
    .max(80, { message: 'El color no puede exceder 80 caracteres' })
    .optional()
    .or(z.literal('').transform(() => undefined)),
  capacidad: z
    .string()
    .max(80, { message: 'La capacidad no puede exceder 80 caracteres' })
    .optional()
    .or(z.literal('').transform(() => undefined)),
  precio: z
    .string()
    .min(1, { message: 'Ingresa el precio de venta' })
    .refine(value => !Number.isNaN(Number(value)), { message: 'El precio debe ser numérico' }),
  targetLocationId: z
    .string()
    .trim()
    .min(1, { message: 'Selecciona la ubicación de destino' })
})

export const validateTradeInActivation = (draft: TradeInActivationDraft): ValidationResult => {
  const parsed = schema.safeParse(draft)
  if (!parsed.success) {
    const issues: ValidationIssue[] = parsed.error.issues.map(issue => ({
      field: issue.path.join('.') || 'activationForm',
      message: issue.message
    }))
    return { ok: false, issues }
  }

  const price = Number(parsed.data.precio)
  const issues: ValidationIssue[] = []
  if (price < 0) {
    issues.push({ field: 'precio', message: 'El precio de venta no puede ser negativo' })
  }

  if (issues.length > 0) {
    return { ok: false, issues }
  }

  return { ok: true, issues: [] }
}
