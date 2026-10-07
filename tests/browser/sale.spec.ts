import {test,expect} from '@playwright/test'
test('completes a cash sale through the UI',async({page})=>{test.setTimeout(60000);
 await page.goto((process.env.E2E_FRONTEND_URL||'http://127.0.0.1:5174'),{waitUntil:'networkidle'})
 await page.getByLabel('Usuario').fill((process.env.E2E_USERNAME||'e2eadmin')); await page.getByLabel('Contraseña').fill((process.env.E2E_PASSWORD||'StageOnly!2026')); await page.getByRole('button',{name:'Ingresar'}).click()
 await expect(page.getByText('E2E Admin',{exact:true})).toBeVisible()
 const api=process.env.E2E_API_URL||'http://127.0.0.1:8100'
 const token=await page.evaluate(()=>localStorage.getItem('auth_token')); const headers={Authorization:`Bearer ${token}`}
 const loc=await page.request.post(`${api}/api/locations`,{headers,data:{nombre:'E2E Tienda',tipo:'tienda',activo:true}}); expect(loc.status()).toBe(201); const location=await loc.json()
 const prof=await page.request.post(`${api}/api/sales-profiles`,{headers,data:{name:'E2E Vendedor',slug:'e2e-vendedor',tipo:'vendedor_humano',active:true}}); expect(prof.status()).toBe(201)
 const prod=await page.request.post(`${api}/api/products`,{headers,data:{sku:'E2E-SKU-003',nombre:'E2E Producto',categoria:'celular',marca:'E2E',modelo:'Phone',condicion:'nuevo',precio:1000,costo:700,is_serialized:true,stock_inicial:1,initial_location_id:location.id,imeis:['359999999999991']}}); expect(prod.status()).toBe(201)
 await page.reload({waitUntil:'networkidle'})
 await page.getByRole('button',{name:'Nueva venta'}).first().click()
 const dlg=page.getByRole('dialog',{name:'Nueva venta'}); await expect(dlg).toBeVisible()
 const combos=dlg.getByRole('combobox')
 await combos.nth(0).click(); await page.getByRole('option',{name:/E2E Vendedor/}).first().click()
 await combos.nth(1).click(); await page.getByRole('option',{name:/E2E Tienda/}).first().click()
 await dlg.getByPlaceholder('Escanea SKU o IMEI').fill('359999999999991'); await dlg.getByRole('button',{name:'Agregar escaneado'}).click()
 await expect(dlg.getByText(/E2E Producto/).first()).toBeVisible()
 await dlg.getByLabel('Nombre del Cliente').fill('Cliente E2E')
 await dlg.getByLabel('Teléfono').fill('99999999')
 await dlg.getByRole('spinbutton',{name:'Efectivo'}).fill('1000')
 await dlg.getByRole('button',{name:'Completar venta'}).click()
 await expect(dlg).toBeHidden({timeout:15000})
})