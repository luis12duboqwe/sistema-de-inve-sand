import type { OrderWithItems, ProductWithStock, Profile } from './types'
import { format } from 'date-fns'

export function generateOrderPDF(order: OrderWithItems, profile: Profile): void {
  const printWindow = window.open('', '_blank')
  if (!printWindow) return

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Orden #${order.id} - ${profile.name}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      padding: 40px;
      color: #1a1a1a;
      background: white;
    }
    
    .header {
      display: flex;
      justify-content: space-between;
      align-items: start;
      margin-bottom: 40px;
      padding-bottom: 20px;
      border-bottom: 2px solid #e5e7eb;
    }
    
    .company-info h1 {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 4px;
      color: #4f46e5;
    }
    
    .company-info p {
      color: #6b7280;
      font-size: 14px;
    }
    
    .order-info {
      text-align: right;
    }
    
    .order-number {
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    
    .order-date {
      color: #6b7280;
      font-size: 14px;
    }
    
    .section {
      margin-bottom: 30px;
    }
    
    .section-title {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 12px;
      color: #1f2937;
    }
    
    .customer-info {
      background: #f9fafb;
      padding: 20px;
      border-radius: 8px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    
    .info-row {
      display: flex;
      flex-direction: column;
    }
    
    .info-label {
      font-size: 12px;
      text-transform: uppercase;
      color: #6b7280;
      font-weight: 600;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    
    .info-value {
      font-size: 16px;
      color: #1f2937;
      font-weight: 500;
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }
    
    thead {
      background: #f3f4f6;
    }
    
    th {
      text-align: left;
      padding: 12px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      color: #6b7280;
      letter-spacing: 0.5px;
    }
    
    td {
      padding: 16px 12px;
      border-bottom: 1px solid #e5e7eb;
      font-size: 14px;
    }
    
    tbody tr:last-child td {
      border-bottom: none;
    }
    
    .product-name {
      font-weight: 600;
      color: #1f2937;
      margin-bottom: 4px;
    }
    
    .product-details {
      font-size: 12px;
      color: #6b7280;
    }
    
    .total-section {
      margin-top: 30px;
      display: flex;
      justify-content: flex-end;
    }
    
    .total-box {
      width: 300px;
      background: #f9fafb;
      padding: 20px;
      border-radius: 8px;
    }
    
    .total-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      font-size: 14px;
    }
    
    .total-row.final {
      border-top: 2px solid #e5e7eb;
      margin-top: 8px;
      padding-top: 16px;
      font-size: 18px;
      font-weight: 700;
      color: #4f46e5;
    }
    
    .status-badge {
      display: inline-block;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .status-pendiente {
      background: #fef3c7;
      color: #92400e;
    }
    
    .status-por_entregar {
      background: #dbeafe;
      color: #1e40af;
    }
    
    .status-completada {
      background: #d1fae5;
      color: #065f46;
    }
    
    .status-cancelada {
      background: #fee2e2;
      color: #991b1b;
    }
    
    .footer {
      margin-top: 60px;
      padding-top: 20px;
      border-top: 2px solid #e5e7eb;
      text-align: center;
      color: #6b7280;
      font-size: 12px;
    }
    
    .notes {
      background: #fffbeb;
      border-left: 4px solid #f59e0b;
      padding: 16px;
      margin-top: 20px;
      border-radius: 4px;
    }
    
    .notes-title {
      font-weight: 600;
      margin-bottom: 8px;
      color: #92400e;
    }
    
    .notes-text {
      color: #78350f;
      font-size: 14px;
      line-height: 1.5;
    }
    
    @media print {
      body {
        padding: 20px;
      }
      
      .no-print {
        display: none;
      }
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="company-info">
      <h1>${profile.name}</h1>
      ${profile.settings?.businessAddress ? `<p>${profile.settings.businessAddress}</p>` : ''}
      ${profile.settings?.businessPhone ? `<p>Tel: ${profile.settings.businessPhone}</p>` : ''}
      ${profile.settings?.businessEmail ? `<p>Email: ${profile.settings.businessEmail}</p>` : ''}
    </div>
    <div class="order-info">
      <div class="order-number">Orden #${order.id}</div>
      <div class="order-date">${format(new Date(order.created_at), 'dd/MM/yyyy HH:mm')}</div>
      <div style="margin-top: 8px;">
        <span class="status-badge status-${order.estado}">${getStatusLabel(order.estado)}</span>
      </div>
    </div>
  </div>
  
  <div class="section">
    <h2 class="section-title">Información del Cliente</h2>
    <div class="customer-info">
      <div class="info-row">
        <span class="info-label">Nombre</span>
        <span class="info-value">${order.customer_name}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Teléfono</span>
        <span class="info-value">${order.customer_phone}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Canal</span>
        <span class="info-value">${getChannelLabel(order.canal)}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Método de Pago</span>
        <span class="info-value">${getPaymentLabel(order.metodo_pago)}</span>
      </div>
    </div>
  </div>
  
  <div class="section">
    <h2 class="section-title">Productos</h2>
    <table>
      <thead>
        <tr>
          <th>Producto</th>
          <th style="text-align: center;">Cantidad</th>
          <th style="text-align: right;">Precio Unit.</th>
          <th style="text-align: right;">Subtotal</th>
        </tr>
      </thead>
      <tbody>
        ${order.items.map(item => `
          <tr>
            <td>
              <div class="product-name">${item.product?.nombre || 'Producto'}</div>
              <div class="product-details">
                ${item.product?.marca || ''} ${item.product?.modelo || ''} 
                ${item.product?.capacidad || ''}
                ${item.es_regalo_promocion ? '• <strong>REGALO/PROMOCIÓN</strong>' : ''}
              </div>
            </td>
            <td style="text-align: center;">${item.cantidad}</td>
            <td style="text-align: right;">${formatCurrency(item.precio_unitario, profile.settings?.currency || 'USD')}</td>
            <td style="text-align: right;">${formatCurrency(item.cantidad * item.precio_unitario, profile.settings?.currency || 'USD')}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  </div>

  ${order.trade_ins && order.trade_ins.length > 0 ? `
    <div class="section">
      <h2 class="section-title">Retomas (Trade-In)</h2>
      <table>
        <thead>
          <tr>
            <th>Dispositivo Recibido</th>
            <th style="text-align: center;">Condición</th>
            <th style="text-align: right;">Valor Estimado</th>
          </tr>
        </thead>
        <tbody>
          ${order.trade_ins.map(trade => `
            <tr>
              <td>
                <div class="product-name">${trade.marca} ${trade.modelo}</div>
                <div class="product-details">
                  ${trade.color || ''} ${trade.capacidad || ''}
                  ${trade.imei ? `• IMEI: ${trade.imei}` : ''}
                </div>
              </td>
              <td style="text-align: center; text-transform: capitalize;">${trade.condicion}</td>
              <td style="text-align: right; color: #dc2626;">- ${formatCurrency(trade.valor_estimado, profile.settings?.currency || 'USD')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  ` : ''}

  ${order.financing_details ? (() => {
    try {
      let details;
      if (typeof order.financing_details === 'string') {
        details = JSON.parse(order.financing_details);
      } else {
        details = order.financing_details;
      }

      return `
        <div class="section">
          <h2 class="section-title">Detalles de Financiamiento</h2>
          <div class="customer-info" style="background: #f9fafb; padding: 15px; border-radius: 8px;">
            <div class="info-row">
              <span class="info-label">Banco</span>
              <span class="info-value">${details.bank_name || 'N/A'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Plazo</span>
              <span class="info-value">${details.months > 0 ? `${details.months} meses` : 'Contado'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Prima (Down Payment)</span>
              <span class="info-value">${formatCurrency(details.down_payment || 0, profile.settings?.currency || 'USD')}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Monto a Financiar</span>
              <span class="info-value">${formatCurrency(details.financed_amount || 0, profile.settings?.currency || 'USD')}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Recargo Bancario (${((details.rate || 0) * 100).toFixed(1)}%)</span>
              <span class="info-value text-orange-600">+ ${formatCurrency(details.surcharge || 0, profile.settings?.currency || 'USD')}</span>
            </div>
            <div class="info-row" style="border-top: 1px solid #e5e7eb; margin-top: 8px; padding-top: 8px;">
              <span class="info-label" style="font-weight: 700;">Cuota Mensual</span>
              <span class="info-value" style="font-weight: 700; font-size: 1.1em;">${formatCurrency(details.monthly_payment || 0, profile.settings?.currency || 'USD')}</span>
            </div>
          </div>
        </div>
      `;
    } catch (e) { 
      console.error('Error parsing financing details for PDF:', e);
      return `<div class="section"><p style="color: red;">Error al cargar detalles de financiamiento</p></div>`; 
    }
  })() : ''}
  
  ${order.notas ? `
    <div class="notes">
      <div class="notes-title">Notas</div>
      <div class="notes-text">${order.notas}</div>
    </div>
  ` : ''}
  
  <div class="total-section">
    <div class="total-box">
      ${(() => {
        // Calcular subtotales para mostrar desglose claro
        const subtotalItems = order.items.reduce((sum, item) => sum + (item.cantidad * item.precio_unitario), 0);
        const totalTradeIns = order.trade_ins ? order.trade_ins.reduce((sum, t) => sum + t.valor_estimado, 0) : 0;
        let surcharge = 0;
        
        if (order.financing_details) {
          try {
            let d;
            if (typeof order.financing_details === 'string') {
              d = JSON.parse(order.financing_details);
            } else {
              d = order.financing_details;
            }
            surcharge = d.surcharge || 0;
          } catch (e) {
            console.error('Error parseando financing_details en pdfExport', e);
          }
        }

        return `
          <div class="total-row">
            <span>Subtotal Productos</span>
            <span>${formatCurrency(subtotalItems, profile.settings?.currency || 'USD')}</span>
          </div>
          
          ${totalTradeIns > 0 ? `
            <div class="total-row" style="color: #dc2626;">
              <span>(-) Retomas / Trade-In</span>
              <span>- ${formatCurrency(totalTradeIns, profile.settings?.currency || 'USD')}</span>
            </div>
          ` : ''}
          
          ${surcharge > 0 ? `
            <div class="total-row" style="color: #d97706;">
              <span>(+) Recargo Financiero</span>
              <span>+ ${formatCurrency(surcharge, profile.settings?.currency || 'USD')}</span>
            </div>
          ` : ''}

          ${profile.settings?.autoCalculateTax && profile.settings?.taxRate ? `
            <div class="total-row">
              <span>Impuesto (${profile.settings.taxRate}%)</span>
              <span>${formatCurrency(order.total - (order.total / (1 + profile.settings.taxRate / 100)), profile.settings?.currency || 'USD')}</span>
            </div>
          ` : ''}
          
          <div class="total-row final">
            <span>Total a Pagar</span>
            <span>${formatCurrency(order.total, profile.settings?.currency || 'USD')}</span>
          </div>
        `;
      })()}
    </div>
  </div>
  
  <div class="footer">
    <p>Generado el ${format(new Date(), 'dd/MM/yyyy HH:mm')}</p>
    <p style="margin-top: 4px;">Sistema de Inventario - ${profile.name}</p>
  </div>
  
  <script>
    window.onload = function() {
      window.print()
    }
  </script>
</body>
</html>
  `

  printWindow.document.write(html)
  printWindow.document.close()
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pendiente: 'Pendiente',
    por_entregar: 'Por Entregar',
    completada: 'Completada',
    cancelada: 'Cancelada'
  }
  return labels[status] || status
}

function getChannelLabel(channel: string): string {
  const labels: Record<string, string> = {
    whatsapp: 'WhatsApp',
    facebook: 'Facebook',
    instagram: 'Instagram',
    tienda: 'Tienda Física'
  }
  return labels[channel] || channel
}

function getPaymentLabel(payment: string): string {
  const labels: Record<string, string> = {
    efectivo: 'Efectivo',
    transferencia: 'Transferencia',
    tarjeta: 'Tarjeta',
    financiamiento: 'Financiamiento'
  }
  return labels[payment] || payment
}

function formatCurrency(amount: number, currency: string): string {
  const symbols: Record<string, string> = {
    USD: '$',
    EUR: '€',
    MXN: '$',
    COP: '$',
    ARS: '$'
  }
  
  return `${symbols[currency] || currency} ${amount.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`
}

export function generateProductReportPDF(products: ProductWithStock[], profile: Profile): void {
  const printWindow = window.open('', '_blank')
  if (!printWindow) return

  const totalValue = products.reduce((sum, p) => sum + (p.precio * p.stock_disponible), 0)
  const lowStockProducts = products.filter(p => 
    p.stock_disponible <= (profile.settings?.lowStockThreshold || 5)
  )

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Reporte de Productos - ${profile.name}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      padding: 40px;
      color: #1a1a1a;
      background: white;
    }
    
    .header {
      margin-bottom: 40px;
      padding-bottom: 20px;
      border-bottom: 2px solid #e5e7eb;
    }
    
    h1 {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 8px;
      color: #4f46e5;
    }
    
    .subtitle {
      color: #6b7280;
      font-size: 14px;
    }
    
    .stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin-bottom: 40px;
    }
    
    .stat-card {
      background: #f9fafb;
      padding: 20px;
      border-radius: 8px;
      border-left: 4px solid #4f46e5;
    }
    
    .stat-label {
      font-size: 12px;
      text-transform: uppercase;
      color: #6b7280;
      font-weight: 600;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
    }
    
    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: #1f2937;
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
      font-size: 12px;
    }
    
    thead {
      background: #f3f4f6;
    }
    
    th {
      text-align: left;
      padding: 10px 8px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      color: #6b7280;
      letter-spacing: 0.5px;
    }
    
    td {
      padding: 12px 8px;
      border-bottom: 1px solid #e5e7eb;
    }
    
    .low-stock {
      background: #fef3c7;
    }
    
    .out-of-stock {
      background: #fee2e2;
    }
    
    @media print {
      body { padding: 20px; }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>Reporte de Inventario</h1>
    <p class="subtitle">${profile.name} - ${format(new Date(), 'dd/MM/yyyy HH:mm')}</p>
  </div>
  
  <div class="stats">
    <div class="stat-card">
      <div class="stat-label">Total Productos</div>
      <div class="stat-value">${products.length}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Valor Inventario</div>
      <div class="stat-value">${formatCurrency(totalValue, profile.settings?.currency || 'USD')}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Stock Bajo</div>
      <div class="stat-value">${lowStockProducts.length}</div>
    </div>
  </div>
  
  <table>
    <thead>
      <tr>
        <th>SKU</th>
        <th>Producto</th>
        <th>Marca</th>
        <th>Modelo</th>
        <th style="text-align: center;">Stock</th>
        <th style="text-align: right;">Precio</th>
        <th style="text-align: right;">Valor Total</th>
      </tr>
    </thead>
    <tbody>
      ${products.map(p => `
        <tr class="${p.stock_disponible === 0 ? 'out-of-stock' : p.stock_disponible <= (profile.settings?.lowStockThreshold || 5) ? 'low-stock' : ''}">
          <td>${p.sku}</td>
          <td>${p.nombre}</td>
          <td>${p.marca}</td>
          <td>${p.modelo}</td>
          <td style="text-align: center;">${p.stock_disponible}</td>
          <td style="text-align: right;">${formatCurrency(p.precio, profile.settings?.currency || 'USD')}</td>
          <td style="text-align: right;">${formatCurrency(p.precio * p.stock_disponible, profile.settings?.currency || 'USD')}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>
  
  <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #e5e7eb; text-align: center; color: #6b7280; font-size: 12px;">
    <p>Generado por Sistema de Inventario - ${profile.name}</p>
  </div>
  
  <script>
    window.onload = function() {
      window.print()
    }
  </script>
</body>
</html>
  `

  printWindow.document.write(html)
  printWindow.document.close()
}
