import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TransferListDialog } from '../TransferListDialog'

const mockInventoryService = vi.hoisted(() => ({
  listStockTransfers: vi.fn(),
  confirmStockTransfer: vi.fn(),
  rejectStockTransfer: vi.fn(),
  cancelStockTransfer: vi.fn(),
}))

const mockApiClient = vi.hoisted(() => ({
  getDailyCloseConfig: vi.fn(),
}))

vi.mock('@/lib/inventoryServiceFactory', () => ({
  inventoryServiceInstance: mockInventoryService,
}))

vi.mock('@/lib/apiClient', () => ({
  apiClient: mockApiClient,
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('TransferListDialog production-critical receiving flow', () => {
  const locations = [
    { id: 1, nombre: 'Tienda Centro', tipo: 'tienda' as const, activo: true, created_at: '2026-09-23T10:00:00Z' },
    { id: 2, nombre: 'Tienda Norte', tipo: 'tienda' as const, activo: true, created_at: '2026-09-23T10:00:00Z' },
    { id: 3, nombre: 'Bodega', tipo: 'bodega' as const, activo: true, created_at: '2026-09-23T10:00:00Z' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockApiClient.getDailyCloseConfig.mockResolvedValue({ configured: false })
    mockInventoryService.confirmStockTransfer.mockResolvedValue(undefined)
    mockInventoryService.rejectStockTransfer.mockResolvedValue(undefined)
    mockInventoryService.cancelStockTransfer.mockResolvedValue(undefined)
  })

  it('shows only transfers relevant to the selected location', async () => {
    mockInventoryService.listStockTransfers.mockResolvedValue([
      {
        id: 10,
        product_id: 100,
        from_location_id: 1,
        to_location_id: 2,
        cantidad: 1,
        estado: 'pendiente',
        created_at: '2026-09-23T10:00:00Z',
        product: { nombre: 'iPhone 15' },
      },
      {
        id: 11,
        product_id: 101,
        from_location_id: 2,
        to_location_id: 3,
        cantidad: 1,
        estado: 'pendiente',
        created_at: '2026-09-23T10:00:00Z',
        product: { nombre: 'Galaxy S24' },
      },
    ])

    render(
      <TransferListDialog
        open
        onOpenChange={vi.fn()}
        locations={locations}
        currentLocationId={1}
      />
    )

    expect(await screen.findByText('iPhone 15')).toBeInTheDocument()
    expect(screen.queryByText('Galaxy S24')).not.toBeInTheDocument()
  })

  it('requires receiving IMEI scan and sends the exact confirmation payload', async () => {
    const onTransferUpdated = vi.fn()
    const user = userEvent.setup()
    mockInventoryService.listStockTransfers.mockResolvedValue([
      {
        id: 20,
        product_id: 200,
        from_location_id: 1,
        to_location_id: 2,
        cantidad: 1,
        estado: 'pendiente',
        created_at: '2026-09-23T10:00:00Z',
        imeis: ['123456789012345'],
        product: { nombre: 'iPhone 15 Pro' },
      },
    ])

    render(
      <TransferListDialog
        open
        onOpenChange={vi.fn()}
        locations={locations}
        currentLocationId={2}
        onTransferUpdated={onTransferUpdated}
      />
    )

    expect(await screen.findByText('iPhone 15 Pro')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Confirmar recepción' }))

    await user.type(screen.getByLabelText('Tu nombre *'), 'Luis')
    const scanInput = screen.getByLabelText(/Escanear IMEIs recibidos/)
    await user.type(scanInput, '123456789012345')
    await user.click(screen.getByRole('button', { name: 'Registrar' }))

    const confirmButtons = screen.getAllByRole('button', { name: 'Confirmar recepción' })
    await user.click(confirmButtons[confirmButtons.length - 1])

    await waitFor(() => {
      expect(mockInventoryService.confirmStockTransfer).toHaveBeenCalledWith(
        20,
        'Luis',
        ['123456789012345'],
        undefined,
        1,
        undefined,
      )
    })
    expect(onTransferUpdated).toHaveBeenCalledTimes(1)
  })
})
