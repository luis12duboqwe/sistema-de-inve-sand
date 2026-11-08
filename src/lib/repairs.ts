export type RepairStatus =
  | 'received' | 'diagnosing' | 'awaiting_approval' | 'approved'
  | 'awaiting_parts' | 'repairing' | 'quality_check' | 'ready'
  | 'delivered' | 'cancelled'

export type RepairIssue = 'screen' | 'battery' | 'charging' | 'software'
  | 'camera' | 'water_damage' | 'micro_soldering' | 'other'

export interface RepairCase {
  id: number
  external_reference: string
  location_id: number
  device_model: string
  issue_category: RepairIssue
  status: RepairStatus
  technician_id: number | null
  quote_amount: number | string | null
  quote_approved: boolean
  qa_passed: boolean
  revision: number
  created_at: string
}

export interface CreateRepairCase {
  intake_key: string
  location_id: number
  device_model: string
  issue_category: RepairIssue
}

export interface RepairTransitionInput {
  next_status: RepairStatus
  expected_revision: number
  event_key: string
  quote_amount?: string
  approval_reference?: string
  parts_available?: boolean
  qa_passed?: boolean
}

export interface RepairAssignmentInput {
  expected_revision: number
  technician_id: number
  event_key: string
}

export const repairStatusNames: Record<RepairStatus, string> = {
  received: 'Recibido',
  diagnosing: 'En diagnóstico',
  awaiting_approval: 'Esperando aprobación',
  approved: 'Presupuesto aprobado',
  awaiting_parts: 'Esperando repuestos',
  repairing: 'En reparación',
  quality_check: 'Control de calidad',
  ready: 'Listo para entrega',
  delivered: 'Entregado',
  cancelled: 'Cancelado'
}

export const repairIssueNames: Record<RepairIssue, string> = {
  screen: 'Pantalla',
  battery: 'Batería',
  charging: 'Carga',
  software: 'Software',
  camera: 'Cámara',
  water_damage: 'Daño por líquidos',
  micro_soldering: 'Microsoldadura',
  other: 'Otro'
}
