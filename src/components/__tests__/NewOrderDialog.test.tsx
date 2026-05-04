import { render, screen } from '@testing-library/react'
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

    const submit = screen.getByRole('button', { name: /crear orden/i })
    const user = userEvent.setup()
    await user.click(submit)

    expect(toast.error).toHaveBeenCalledWith('Ingresa el nombre del cliente')
  })
})
