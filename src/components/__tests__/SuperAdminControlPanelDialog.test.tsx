import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SuperAdminControlPanelDialog } from '../SuperAdminControlPanelDialog'

const mockApiClient = vi.hoisted(() => ({
  getSuperAdminStockImeiDiagnostics: vi.fn().mockResolvedValue({ issues: [] }),
  getSuperAdminAuditLogs: vi.fn().mockResolvedValue({ items: [] }),
  getSuperAdminEntityHistory: vi.fn().mockResolvedValue({ audit_logs: [], stock_history: [], imei_history: [] }),
  getSuperAdminAlerts: vi.fn().mockResolvedValue({ items: [] }),
  getSuperAdminUsers: vi.fn().mockResolvedValue({ items: [] }),
}))

const mockInventoryService = vi.hoisted(() => ({
  listStockTransfers: vi.fn().mockResolvedValue([]),
}))

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@/lib/apiClient', () => ({
  apiClient: mockApiClient,
}))

vi.mock('@/lib/inventoryServiceFactory', () => ({
  inventoryServiceInstance: mockInventoryService,
}))

vi.mock('../ProductIMEIRegistryDialog', () => ({
  ProductIMEIRegistryDialog: () => null,
}))

describe('SuperAdminControlPanelDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApiClient.getSuperAdminStockImeiDiagnostics.mockResolvedValue({ issues: [] })
    mockApiClient.getSuperAdminAuditLogs.mockResolvedValue({ items: [] })
    mockApiClient.getSuperAdminEntityHistory.mockResolvedValue({ audit_logs: [], stock_history: [], imei_history: [] })
    mockApiClient.getSuperAdminAlerts.mockResolvedValue({ items: [] })
    mockApiClient.getSuperAdminUsers.mockResolvedValue({ items: [] })
    mockInventoryService.listStockTransfers.mockResolvedValue([])
  })

  it('shows an executive summary when the panel opens', async () => {
    render(
      <SuperAdminControlPanelDialog
        open
        onOpenChange={vi.fn()}
        products={[]}
        locations={[]}
        orders={[]}
      />
    )

    expect(await screen.findByText('Resumen operativo')).toBeInTheDocument()
    expect(screen.getByText('Sin problemas detectados')).toBeInTheDocument()
  })
})
