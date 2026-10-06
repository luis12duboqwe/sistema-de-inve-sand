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

test('creates and receives a stock transfer through the UI', async ({ page }) => {
  const suffix = Date.now().toString()
  const sourceName = `E2E Origen ${suffix}`\n  const destinationName = `E2E Destino ${suffix}`\n  const productName = `E2E Accesorio Transfer ${suffix}`\n  const sku = `E2E-TR-${suffix}`
  await page.goto(frontendUrl, { waitUntil: 'networkidle' })
  await page.getByLabel('Usuario').fill(username)
  await page.getByLabel('Contraseña').fill(password)
  await page.getByRole('button', { name: 'Ingresar' }).click()
  await expect(page.getByText('E2E Admin', { exact: true })).toBeVisible({ timeout: 15000 })

  await page.getByRole('tab', { name: 'Ubicaciones' }).click()
  for (const name of ['E2E Origen', 'E2E Destino']) {
    if (!(await page.getByText(name, { exact: true }).count())) {
      await page.getByRole('button', { name: 'Nueva Ubicación' }).click()
      await page.getByLabel('Nombre *').fill(name)
      await page.getByRole('button', { name: 'Crear Ubicación' }).click()
      await expect(page.getByText(name, { exact: true })).toBeVisible()
    }
  }

  await page.getByRole('tab', { name: 'Inicio' }).click()
  await page.getByRole('button', { name: 'Producto' }).click()
  await page.getByText('Categoría *').locator('..').getByRole('combobox').click()
  await page.getByRole('option', { name: 'Accesorio' }).click()
  await page.getByLabel('Marca *').fill('E2EBrand')
  await page.getByLabel('Modelo *').fill('CableTransfer')
  await page.getByLabel('Nombre del Producto * (generado automáticamente)').fill(productName)
  await page.getByLabel('SKU * (generado automáticamente)').fill(sku)
  await page.getByRole('spinbutton', { name: 'Stock Inicial *' }).fill('3')
  await page.getByLabel('Precio Venta *').fill('250')
  await page.getByLabel('Costo (Reportes)').fill('100')
  await page.getByLabel('Ubicación para Stock Inicial *').click()
  await page.getByRole('option', { name: sourceName }).click()
  await page.getByRole('button', { name: 'Guardar producto' }).click()
  await expect(page.getByText(productName).first()).toBeVisible({ timeout: 15000 })

  await page.getByRole('tab', { name: 'Transferencias' }).click()
  await page.getByRole('button', { name: 'Nueva transferencia' }).click()
  const transferDialog = page.getByRole('dialog')
  const combos = transferDialog.getByRole('combobox')
  await combos.nth(0).click()
  await page.getByRole('option', { name: sourceName }).click()
  await combos.nth(1).click()
  await page.getByRole('option', { name: destinationName }).click()
  await transferDialog.getByPlaceholder('Buscar por modelo, marca o SKU').fill(sku)
  await transferDialog.getByText(productName, { exact: true }).click()
  await transferDialog.getByRole('spinbutton').fill('2')
  await transferDialog.getByRole('button', { name: /Registrar 1 modelo/ }).click()
  await expect(transferDialog).not.toBeVisible({ timeout: 15000 })

  await page.getByRole('button', { name: 'Ver Transferencias' }).click()
  await page.getByRole('button', { name: 'Confirmar recepción' }).first().click()
  const receiveDialog = page.getByRole('dialog', { name: 'Confirmar Recepción' })
  await receiveDialog.getByLabel('Tu nombre *').fill('E2E Admin')
  await receiveDialog.getByLabel('Cantidad recibida *').fill('2')
  await receiveDialog.getByRole('button', { name: 'Confirmar recepción' }).click()
  await expect(receiveDialog).not.toBeVisible({ timeout: 15000 })
})
