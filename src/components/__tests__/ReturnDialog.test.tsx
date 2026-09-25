import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ReturnDialog } from '../ReturnDialog'
import type { OrderWithItems } from '@/lib/types'
import { toast } from 'sonner'

const mockInventoryService = vi.hoisted(() => ({
  createReturn: vi.fn(),
}))

vi.mock('@/lib/inventoryServiceFactory', () => ({
  inventoryServiceInstance: mockInventoryService,
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('ReturnDialog warranty-only post-sale flow', () => {
  const order = {
    id: 900,
    customer_name: 'Cliente Prueba',
    customer_phone: '+50499998888',
    canal: 'tienda',
    metodo_pago: 'efectivo',
    total: 12500,
    estado: 'completada',
    created_at: '2026-09-23T10:00:00Z',
    items: [
      {
        id: 901,
        order_id: 900,
        product_id: 100,
        cantidad: 1,
        precio_unitario: 12500,
        subtotal: 12500,
        product: {
          id: 100,
          sku: 'IPH15P-TEST',
          nombre: 'iPhone 15 Pro',
          categoria: 'celular',
        },
      },
    ],
  } as unknown as OrderWithItems

  beforeEach(() => {
    vi.clearAllMocks()
    mockInventoryService.createReturn.mockResolvedValue({ id: 1 })
  })

  it('shows the no-refund policy and blocks submitting until a sold item is selected', async () => {
    const browserUser = userEvent.setup()

    render(
      <ReturnDialog
        open
        onOpenChange={vi.fn()}
        order={order}
        onSuccess={vi.fn()}
      />
    )

    expect(screen.getByText(/No se realizan devoluciones de dinero ni/i)).toBeInTheDocument()
    expect(screen.queryByText('Reembolso')).not.toBeInTheDocument()
    expect(screen.queryByText('Crédito en Tienda')).not.toBeInTheDocument()

    await browserUser.click(screen.getByRole('button', { name: 'Confirmar Cambio / Garantía' }))

    expect(toast.error).toHaveBeenCalledWith('Selecciona al menos un producto para procesar la garantía')
    expect(mockInventoryService.createReturn).not.toHaveBeenCalled()
  })

  it('submits the selected cellphone as a warranty exchange with both IMEIs', async () => {
    const browserUser = userEvent.setup()
    const onSuccess = vi.fn()
    const onOpenChange = vi.fn()

    render(
      <ReturnDialog
        open
        onOpenChange={onOpenChange}
        order={order}
        onSuccess={onSuccess}
      />
    )

    await browserUser.click(screen.getByLabelText('iPhone 15 Pro'))
    await browserUser.type(
      screen.getByPlaceholderText('Escanea o escribe el IMEI del equipo defectuoso'),
      '111111111111111'
    )
    await browserUser.type(
      screen.getByPlaceholderText('Escanea o escribe el IMEI del equipo de reemplazo'),
      '222222222222222'
    )
    await browserUser.click(screen.getByRole('button', { name: 'Confirmar Cambio / Garantía' }))

    await waitFor(() => {
      expect(mockInventoryService.createReturn).toHaveBeenCalledWith({
        order_id: 900,
        reason: '',
        created_by: 'Usuario Actual',
        items: [
          {
            product_id: 100,
            quantity: 1,
            condition: 'defectuoso',
            action: 'warranty_exchange',
            imei: '111111111111111',
            replacement_imei: '222222222222222',
          },
        ],
      })
    })
    expect(toast.success).toHaveBeenCalledWith('Cambio por garantía procesado exitosamente')
    expect(onSuccess).toHaveBeenCalledTimes(1)
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
