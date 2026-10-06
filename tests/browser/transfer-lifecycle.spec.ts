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
  const sourceName = `E2E Origen ${suffix}`
  const destinationName = `E2E Destino ${suffix}`
  const productName = `E2E Accesorio Transfer ${suffix}`
  const sku = `E2E-TR-${suffix}`
  await page.goto(frontendUrl, { waitUntil: 'networkidle' })
  await page.getByLabel('Usuario').fill(username)
  await page.getByLabel('Contraseña').fill(password)
  await page.getByRole('button', { name: 'Ingresar' }).click()
  await expect(page.getByText('E2E Admin', { exact: true })).toBeVisible({ timeout: 15000 })

  const token = await page.evaluate(() => localStorage.getItem('auth_token'))
  expect(token).toBeTruthy()
  for (const name of [sourceName, destinationName]) {
    const response = await page.request.post(`${apiUrl}/api/locations`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { nombre: name, tipo: 'tienda', activo: true },
    })
    expect(response.status()).toBe(201)
  }
  await page.reload({ waitUntil: 'networkidle' })

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

  await page.getByRole('tab', { name: 'Inventario' }).click()
  await page.getByRole('button', { name: 'Agregar más' }).click()
  const restockDialog = page.getByRole('dialog', { name: 'Agregar más inventario' })
  await restockDialog.getByPlaceholder('Buscar producto, SKU o modelo').fill(sku)
  await restockDialog.getByText(productName, { exact: true }).click()
  const restockCombos = restockDialog.getByRole('combobox')
  await restockCombos.first().click()
  await page.getByRole('option', { name: new RegExp(sourceName) }).click()
  const restockNumbers = restockDialog.getByRole('spinbutton')
  await restockNumbers.nth(0).fill('2')
  await restockNumbers.nth(1).fill('90')
  await restockDialog.getByRole('button', { name: 'Agregar más' }).click()
  await expect(restockDialog).not.toBeVisible({ timeout: 15000 })

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
  const listDialog = page.getByRole('dialog', { name: 'Transferencias de Stock' })
  await expect(listDialog).toBeVisible({ timeout: 15000 })
  await listDialog.getByRole('button', { name: 'Confirmar recepción' }).first().click()
  const receiveDialog = page.getByRole('dialog', { name: 'Confirmar Recepción' })
  await receiveDialog.getByLabel('Tu nombre *').fill('E2E Admin')
  await receiveDialog.getByLabel('Cantidad recibida *').fill('2')
  await receiveDialog.getByRole('button', { name: 'Confirmar recepción' }).click()
  await expect(receiveDialog).not.toBeVisible({ timeout: 15000 })
})
