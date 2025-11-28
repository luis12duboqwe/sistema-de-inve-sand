import type { ProductWithStock, OrderWithItems } from './types'

export function exportToCSV(data: Record<string, unknown>[], filename: string) {
  if (data.length === 0) {
    throw new Error('No hay datos para exportar')
  }

  const headers = Object.keys(data[0])
  const csvRows: string[] = []

  csvRows.push(headers.join(','))

  for (const row of data) {
    const values = headers.map(header => {
      const value = row[header]
      const escaped = ('' + value).replace(/"/g, '\\"')
      return `"${escaped}"`
    })
    csvRows.push(values.join(','))
  }

  const csvString = csvRows.join('\n')
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)

  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export function exportProductsToCSV(products: ProductWithStock[], profileName?: string) {
  const exportData = products.map(product => ({
    SKU: product.sku,
    Nombre: product.nombre,
    Categoría: product.categoria,
    Marca: product.marca,
    Modelo: product.modelo,
    Capacidad: product.capacidad,
    Condición: product.condicion,
    Precio: product.precio,
    Moneda: product.moneda,
    'Garantía (meses)': product.garantia_meses,
    Stock: product.stock_disponible,
    Activo: product.activo ? 'Sí' : 'No',
  }))

  const filename = `productos_${profileName || 'todos'}_${new Date().toISOString().split('T')[0]}.csv`
  exportToCSV(exportData, filename)
}

export function exportOrdersToCSV(orders: OrderWithItems[], profileName?: string) {
  const exportData = orders.map(order => ({
    ID: order.id,
    Cliente: order.customer_name,
    Teléfono: order.customer_phone,
    Canal: order.canal,
    'Método de Pago': order.metodo_pago,
    Total: order.total,
    Estado: order.estado,
    Fecha: new Date(order.created_at).toLocaleDateString('es-HN'),
    Productos: order.items.length,
  }))

  const filename = `ordenes_${profileName || 'todas'}_${new Date().toISOString().split('T')[0]}.csv`
  exportToCSV(exportData, filename)
}

export function exportOrderDetailsToCSV(order: OrderWithItems) {
  const exportData = order.items.map(item => ({
    'ID Orden': order.id,
    Cliente: order.customer_name,
    Producto: item.product.nombre,
    SKU: item.product.sku,
    Cantidad: item.cantidad,
    'Precio Unitario': item.precio_unitario,
    Subtotal: item.cantidad * item.precio_unitario,
    'Regalo/Promoción': item.es_regalo_promocion ? 'Sí' : 'No',
  }))

  const filename = `orden_${order.id}_detalle_${new Date().toISOString().split('T')[0]}.csv`
  exportToCSV(exportData, filename)
}
