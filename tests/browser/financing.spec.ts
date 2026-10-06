import { test, expect } from '@playwright/test'

const frontendUrl = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5174'
const apiUrl = process.env.E2E_API_URL || 'http://127.0.0.1:8100'
const username = process.env.E2E_USERNAME || 'e2eadmin'
const password = process.env.E2E_PASSWORD || 'StageOnly!2026'

test.beforeAll(async ({ request }) => {
  const setup = await request.post(`${apiUrl}/api/auth/setup`, {
    data: { username, email: 'e2eadmin@example.invalid', full_name: 'E2E Admin', password },
  })
  expect([200, 403]).toContain(setup.status())
})

test('creates financing bank settings', async ({ page }) => {
  const bankName = `Banco E2E ${Date.now()}`
  await page.goto(frontendUrl, { waitUntil: 'networkidle' })
  await page.getByLabel('Usuario').fill(username)
  await page.getByLabel('Contraseña').fill(password)
  await page.getByRole('button', { name: 'Ingresar' }).click()
  await expect(page.getByText('E2E Admin', { exact: true })).toBeVisible({ timeout: 15000 })
  await page.getByRole('tab', { name: 'Financiamiento' }).click()
  await expect(page.getByText('Configuración de Financiamiento')).toBeVisible()
  await page.getByPlaceholder('Nombre del Banco').fill(bankName)
  await page.getByRole('button', { name: 'Agregar' }).click()
  await expect(page.getByText(bankName)).toBeVisible({ timeout: 10000 })
})
