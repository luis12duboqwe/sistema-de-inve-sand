import { test, expect } from '@playwright/test'

const frontendUrl = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5174'
const apiUrl = process.env.E2E_API_URL || 'http://127.0.0.1:8100'
const username = process.env.E2E_USERNAME || 'e2eadmin'
const password = process.env.E2E_PASSWORD || 'StageOnly!2026'

test.describe.serial('authenticated staging journey', () => {
  test.beforeAll(async ({ request }) => {
    const setup = await request.post(`${apiUrl}/api/auth/setup`, {
      data: { username, email: 'e2eadmin@example.invalid', full_name: 'E2E Admin', password },
    })
    expect([200, 403]).toContain(setup.status())
  })

  test('logs in, navigates modules, and opens critical workflows', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', error => pageErrors.push(error.message))
    await page.goto(frontendUrl, { waitUntil: 'networkidle' })
    await page.getByLabel('Usuario').fill(username)
    await page.getByLabel('Contraseña').fill(password)
    await page.getByRole('button', { name: 'Ingresar' }).click()
    await expect(page.getByText('E2E Admin', { exact: true })).toBeVisible({ timeout: 15000 })

    for (const tab of ['Inicio', 'Inventario', 'Analítica', 'Multitienda', 'Ventas', 'Transferencias', 'Ubicaciones', 'Canales', 'Financiamiento']) {
      const trigger = page.getByRole('tab', { name: tab })
      if (await trigger.count()) {
        await trigger.click()
        await expect(trigger).toHaveAttribute('data-state', 'active')
      }
    }

    await page.getByRole('tab', { name: 'Inicio' }).click()
    await page.getByRole('button', { name: 'Producto' }).click()
    await expect(page.getByRole('heading', { name: 'Nuevo producto' })).toBeVisible()
    await expect(page.getByLabel('Precio Venta *')).toBeVisible()
    await page.keyboard.press('Escape')

    await page.getByRole('button', { name: 'Nueva venta' }).click()
    await expect(page.getByText(/Nueva venta/i).first()).toBeVisible()
    await page.keyboard.press('Escape')

    expect(pageErrors).toEqual([])
  })
})
