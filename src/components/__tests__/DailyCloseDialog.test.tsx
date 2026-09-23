import type { ReactNode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DailyCloseDialog } from '../DailyCloseDialog'
import { apiClient } from '@/lib/apiClient'
import { toast } from 'sonner'

vi.mock('framer-motion', async () => {
  const React = await import('react')
  const MotionElement = ({ children }: { children?: ReactNode }) => React.createElement('div', null, children)

  return {
    AnimatePresence: ({ children }: { children?: ReactNode }) => React.createElement(React.Fragment, null, children),
    motion: new Proxy({}, {
      get: () => MotionElement,
    }),
  }
})

vi.mock('@/lib/apiClient', () => ({
  apiClient: {
    getDailyClosePending: vi.fn(),
    getDailyCloseConfig: vi.fn(),
    listLocations: vi.fn(),
    validateDailyClose: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('DailyCloseDialog production-critical validation flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getDailyClosePending).mockResolvedValue([
      {
        id: 501,
        customer_name: 'Cliente Prueba',
        customer_phone: '+50499998888',
        canal: 'tienda',
        metodo_pago: 'efectivo',
        total: 12500,
        estado: 'completada',
        source_location_id: 1,
        source_location_name: 'Tienda Centro',
        created_at: '2026-09-23T10:00:00Z',
        items_count: 1,
        items_summary: 'iPhone 15 Pro',
      },
    ] as Awaited<ReturnType<typeof apiClient.getDailyClosePending>>)
    vi.mocked(apiClient.getDailyCloseConfig).mockResolvedValue({
      configured: true,
      mensaje: 'Cierre diario configurado',
    })
    vi.mocked(apiClient.listLocations).mockResolvedValue([
      { id: 1, nombre: 'Tienda Centro', tipo: 'tienda', activo: true, created_at: '2026-09-23T10:00:00Z' },
    ] as Awaited<ReturnType<typeof apiClient.listLocations>>)
    vi.mocked(apiClient.validateDailyClose).mockResolvedValue({
      validated_count: 1,
      total_ventas: 12500,
      mensaje: 'Cierre validado',
    } as Awaited<ReturnType<typeof apiClient.validateDailyClose>>)
  })

  it('loads completed sales, validates the selected sale and reports a successful close', async () => {
    const browserUser = userEvent.setup()
    const onValidated = vi.fn()

    render(
      <DailyCloseDialog
        open
        onOpenChange={vi.fn()}
        onValidated={onValidated}
      />
    )

    expect(await screen.findByText(/#501 — Cliente Prueba/)).toBeInTheDocument()
    expect(screen.getByText(/1 venta\(s\) seleccionada\(s\)/i)).toBeInTheDocument()

    await browserUser.type(screen.getByLabelText(/Código de validación/), '654321')
    await browserUser.click(screen.getByRole('button', { name: /Validar 1 Venta\(s\)/i }))

    await waitFor(() => {
      expect(apiClient.validateDailyClose).toHaveBeenCalledWith({
        validation_code: '654321',
        order_ids: [501],
        location_id: undefined,
        notas: undefined,
      })
    })
    expect(onValidated).toHaveBeenCalledTimes(1)
    expect(toast.success).toHaveBeenCalledWith('1 ventas validadas exitosamente')
    expect(await screen.findByText('¡Cierre de día completado!')).toBeInTheDocument()
  })
})
