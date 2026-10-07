import { test, expect } from '@playwright/test'

const frontendUrl = process.env.E2E_FRONTEND_URL || 'http://127.0.0.1:5174'
const apiUrl = process.env.E2E_API_URL || 'http://127.0.0.1:8100'
const username = process.env.E2E_USERNAME || 'e2eadmin'
const password = process.env.E2E_PASSWORD || 'StageOnly!2026'

test.beforeAll(async ({ request }) => {
  const setup = await request.post(`${apiUrl}/api/auth/setup`, { data: { username, email: 'e2eadmin@example.invalid', full_name: 'E2E Admin', password } })
  expect([200, 403]).toContain(setup.status())
})

test('registers a multistore serialized receipt', async ({ page }) => {
  test.setTimeout(60000)
  const suffix = Date.now().toString()
  const locationName = `E2E Receipt ${suffix}`
  const productName = `E2E Receipt Phone ${suffix}`
  const sku = `E2E-RC-${suffix}`
  const imei = '35' + suffix.padEnd(13, '7').slice(0, 13)

  await page.goto(frontendUrl, { waitUntil: 'networkidle' })
  await page.getByLabel('Usuario').fill(username)
  await page.getByLabel('Contraseña').fill(password)
  await page.getByRole('button', { name: 'Ingresar' }).click()
  await expect(page.getByText('E2E Admin', { exact: true })).toBeVisible({ timeout: 15000 })
  const token = await page.evaluate(() => localStorage.getItem('auth_token'))
  expect(token).toBeTruthy()
  const headers = { Authorization: `Bearer ${token}` }

  const loc = await page.request.post(`${apiUrl}/api/locations`, { headers, data: { nombre: locationName, tipo: 'tienda', activo: true } })
  expect(loc.status()).toBe(201)
  const location = await loc.json()
  const prod = await page.request.post(`${apiUrl}/api/products`, { headers, data: {
    sku, nombre: productName, categoria: 'celular', marca: 'E2E', modelo: 'ReceiptPhone',
    condicion: 'nuevo', precio: 1000, costo: 700, is_serialized: true, stock_inicial: 0,
  } })
  expect(prod.status()).toBe(201)

  await page.reload({ waitUntil: 'networkidle' })
  await page.getByTitle(/herramientas/i).click()
  await page.getByText('Control multitienda', { exact: true }).click()
  const dlg = page.getByRole('dialog', { name: 'Control Multitienda' })
  await dlg.getByRole('tab', { name: 'Recepción' }).click()
  await dlg.getByRole('combobox').first().click()
  await page.getByRole('option', { name: new RegExp(locationName) }).click()
  const invoice = `E2E-FAC-${suffix}`
  await dlg.getByPlaceholder('FAC-001').fill(invoice)
  await dlg.getByPlaceholder('Buscar producto, SKU o modelo').first().fill(sku)
  await dlg.getByText(productName, { exact: true }).click()
  await dlg.getByPlaceholder('IMEI1, IMEI2').fill(imei)
  const nums = dlg.getByRole('spinbutton')
  await nums.nth(0).fill('1')
  await nums.nth(1).fill('700')
  await dlg.getByRole('button', { name: 'Registrar recepción' }).click()
  await expect(dlg.getByText(invoice, { exact: false }).first()).toBeVisible({ timeout: 15000 })
})
