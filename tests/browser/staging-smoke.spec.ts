import { test, expect } from '@playwright/test'

const frontendUrl = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5174'
const apiUrl = process.env.E2E_API_URL || 'http://127.0.0.1:8100'

test('staging UI and API are reachable', async ({ page, request }) => {
  const pageErrors: string[] = []
  page.on('pageerror', error => pageErrors.push(error.message))

  const health = await request.get(`${apiUrl}/api/health`)
  expect(health.ok()).toBeTruthy()

  const response = await page.goto(frontendUrl, { waitUntil: 'networkidle' })
  expect(response?.ok()).toBeTruthy()
  await expect(page.getByText('Iniciar Sesión')).toBeVisible()
  await expect(page.getByLabel('Usuario')).toBeVisible()
  await expect(page.getByLabel('Contraseña')).toBeVisible()
  expect(pageErrors).toEqual([])
})
