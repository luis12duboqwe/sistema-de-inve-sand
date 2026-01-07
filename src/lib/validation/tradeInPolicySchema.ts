import { z } from 'zod'
import type { ValidationIssue, ValidationResult } from './types'

export interface TradeInPolicyDraft {
  rule_type: string
  pattern: string
  action: string
  reason?: string
}

const schema = z.object({
  rule_type: z.enum(['model_rejection', 'brand_rejection', 'condition_rejection']),
  pattern: z
    .string()
    .trim()
    .min(2, { message: 'El patrón debe tener al menos 2 caracteres' })
    .max(120, { message: 'El patrón no puede exceder 120 caracteres' }),
  action: z.enum(['reject', 'review', 'allow']),
  reason: z
    .string()
    .max(200, { message: 'La razón no puede exceder 200 caracteres' })
    .optional()
    .or(z.literal('').transform(() => undefined))
})

export const validateTradeInPolicy = (draft: TradeInPolicyDraft): ValidationResult => {
  const parsed = schema.safeParse(draft)
  if (!parsed.success) {
    const issues: ValidationIssue[] = parsed.error.issues.map(issue => ({
      field: issue.path.join('.') || 'policyForm',
      message: issue.message
    }))
    return { ok: false, issues }
  }
  return { ok: true, issues: [] }
}
