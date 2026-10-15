import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { toast } from 'sonner'
import { NewOrderDialog } from '../NewOrderDialog'

const mockInventoryService = vi.hoisted(() => ({
  getBanks: vi.fn().mockResolvedValue([])
}))

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

vi.mock('@/lib/inventoryServiceFactory', () => ({
  inventoryServiceInstance: mockInventoryService
}))

describe('NewOrderDialog validations', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('last_sales_profile_slug', 'ventas')
    localStorage.setItem('last_source_location_id', '1')
    vi.clearAllMocks()
    mockInventoryService.getBanks.mockResolvedValue([])
  })

  it('shows validation when customer name is missing', async () => {
    render(
      <NewOrderDialog
        open
        onOpenChange={vi.fn()}
        profiles={[]}
        salesProfiles={[{ id: 1, name: 'Ventas', slug: 'ventas', tipo: 'vendedor_humano', canales: ['whatsapp'], active: true, created_at: '', updated_at: '' }]}
        locations={[{ id: 1, nombre: 'Tienda', tipo: 'tienda', activo: true, created_at: '' }]}
        products={[]}
        onSubmit={vi.fn()}
      />
    )

    const submit = screen.getByRole('button', { name: /completar venta/i })
    const user = userEvent.setup()
    await user.click(submit)

    expect(toast.error).toHaveBeenCalledWith('Ingresa el nombre del cliente')
  })
})

describe('NewOrderDialog preserves uncertain sales safely', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('last_sales_profile_slug', 'ventas')
    localStorage.setItem('last_source_location_id', '1')
    vi.clearAllMocks()
    mockInventoryService.getBanks.mockResolvedValue([])
  })

  it('retains the draft and reuses the same idempotency key after a lost response', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('Lost HTTP response'))
    const onOpenChange = vi.fn()
    const product = {
      id: 17, sku: 'QA-FUNDA-17', nombre: 'Funda de prueba QA',
      categoria: 'accesorio', condicion: 'nuevo', marca: 'QA', modelo: 'F1',
      is_serialized: false, precio: 500, moneda: 'HNL', activo: true,
      stock_disponible: 3,
      stock_items: [{ location_id: 1, cantidad_disponible: 3, cantidad_reservada: 0 }],
    } as any

    render(
      <NewOrderDialog
        open
        onOpenChange={onOpenChange}
        profiles={[]}
        salesProfiles={[{
          id: 1, name: 'Ventas', slug: 'ventas', tipo: 'vendedor_humano',
          canales: ['whatsapp'], active: true, created_at: '', updated_at: ''
        }]}
        locations={[{ id: 1, nombre: 'Tienda QA', tipo: 'tienda', activo: true, created_at: '' }]}
        products={[product]}
        onSubmit={onSubmit}
      />,
    )

    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Nombre del Cliente'), 'Cliente QA')
    await user.type(screen.getByLabelText('Teléfono'), '99999999')

    await user.click(screen.getByRole('combobox', { name: /Buscar producto por modelo/i }))
    await user.click(await screen.findByText(/Funda de prueba QA/))

    const button = screen.getByRole('button', { name: /Completar venta/i })
    await user.click(button)
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(button).toBeEnabled())
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
    expect((screen.getByLabelText('Nombre del Cliente') as HTMLInputElement).value).toBe('Cliente QA')

    await user.click(button)
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(2))
    const first = onSubmit.mock.calls[0][0]
    const second = onSubmit.mock.calls[1][0]
    expect(first.items[0].product_id).toBe(17)
    expect(first.idempotency_key).toMatch(/^[a-f0-9-]{36}$/)
    expect(second.idempotency_key).toBe(first.idempotency_key)
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })
})
