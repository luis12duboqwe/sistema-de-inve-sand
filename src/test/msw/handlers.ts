import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('*/api/orders', () => {
    return HttpResponse.json({ items: [{ id: 1, customer_name: 'Test', total: 100, estado: 'pendiente', canal: 'whatsapp', metodo_pago: 'efectivo', created_at: new Date().toISOString(), customer_phone: '+50499999999', items: [] }] })
  }),
  http.post('*/api/orders', async ({ request }) => {
    const body = await request.json() as any
    if (!body?.customer_name) {
      return HttpResponse.json({ detail: 'missing customer' }, { status: 400 })
    }
    return HttpResponse.json({ id: 2, ...body, estado: 'pendiente', created_at: new Date().toISOString() })
  }),
  http.post('*/api/stock-transfers', async ({ request }) => {
    const body = await request.json() as any
    if (!body?.cantidad) {
      return HttpResponse.json({ detail: 'cantidad requerida' }, { status: 400 })
    }
    return HttpResponse.json({ id: 10, estado: 'pendiente', created_at: new Date().toISOString(), ...body })
  }),
  http.get('*/api/stock-transfers', () => {
    return HttpResponse.json({ items: [] })
  }),
]
