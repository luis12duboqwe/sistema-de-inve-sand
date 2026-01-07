export interface ValidationIssue {
  field: string
  message: string
}

export interface ValidationResult {
  ok: boolean
  issues: ValidationIssue[]
}
