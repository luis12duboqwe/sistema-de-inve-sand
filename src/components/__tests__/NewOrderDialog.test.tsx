import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { NewOrderDialog } from '../NewOrderDialog'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))
vi.mock('@/lib/apiClient', () => ({ apiClient: { getBanks: vi.fn().mockResolvedValue([]) } }))

const toast = (await import('sonner')).toast

describe('NewOrderDialog validations', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('last_sales_profile_slug', 'ventas')
    localStorage.setItem('last_source_location_id', '1')
    vi.clearAllMocks()
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

    const submit = screen.getByRole('button', { name: /crear orden/i })
    const user = userEvent.setup()
    await user.click(submit)

    expect(toast.error).toHaveBeenCalledWith('Por favor ingresa el nombre del cliente')
  })
})
