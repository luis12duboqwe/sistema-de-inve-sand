import type { ValidationIssue, ValidationResult } from './types'

export interface ImportProductsState {
  hasFile: boolean
  selectedLocationId: string
  previewReady: boolean
  previewHasRows: boolean
}

export const validateImportSubmission = (state: ImportProductsState): ValidationResult => {
  const issues: ValidationIssue[] = []

  if (!state.selectedLocationId) {
    issues.push({ field: 'location', message: 'Selecciona la ubicación destino antes de importar' })
  }

  if (!state.hasFile) {
    issues.push({ field: 'file', message: 'Selecciona un archivo CSV antes de continuar' })
  }

  if (!state.previewReady) {
    issues.push({ field: 'preview', message: 'Genera una vista previa válida antes de importar' })
  }

  if (state.previewReady && !state.previewHasRows) {
    issues.push({ field: 'preview', message: 'No hay productos válidos para importar' })
  }

  if (issues.length > 0) {
    return { ok: false, issues }
  }

  return { ok: true, issues: [] }
}
