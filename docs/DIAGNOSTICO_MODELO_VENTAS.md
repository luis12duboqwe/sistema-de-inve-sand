# Diagnóstico del Sistema vs Modelo de Ventas del Negocio

Fecha: 2026-03-09

## 1) Resumen Ejecutivo

El sistema actual está **muy avanzado** para operación retail de celulares y accesorios con múltiples puntos de venta:

- Inventario multi-ubicación
- Órdenes con salida por ubicación
- Canales de venta (WhatsApp/Facebook/Instagram)
- IMEI y trazabilidad
- Transferencias de stock
- Devoluciones, garantía y retomas (trade-in)
- Financiamiento bancario
- RBAC por permisos
- Reportes y capa de IA

Conclusión: el núcleo operativo está listo para producción. Para alinearlo al 100% con un modelo de ventas comercial completo, faltan principalmente capas de control financiero/operativo.

---

## 2) Cobertura Funcional Actual (confirmada)

### Inventario y operación
- Catálogo de productos global
- Stock por ubicación (tienda/bodega/oficina)
- Transferencia entre ubicaciones
- Historial de movimientos (kardex operativo)
- Alertas de stock bajo

### Venta y postventa
- Órdenes con items, canal, método de pago y estado
- Búsqueda avanzada de órdenes
- Historial de cliente
- Devoluciones
- Garantía por IMEI

### Especial para telefonía
- Control de IMEIs y ciclo de vida
- Venta/transferencia/consulta por IMEI

### Gestión comercial
- Perfiles de venta (bots, vendedores, canales)
- Trade-in (retomas) y políticas
- Financiamiento (bancos/opciones)

### Seguridad y control
- JWT + RBAC granular
- Roles de sistema y permisos por módulo

### Inteligencia
- Forecasting
- Insights y recomendaciones

---

## 3) Brechas Críticas para Modelo de Ventas “Comercial Completo”

## Alta prioridad
1. **Compras/recepciones a proveedor (entrada formal de inventario)**
   - Hoy hay proveedores, pero falta ciclo formal de compra: orden de compra → recepción parcial/total → costo real.
2. **Costeo y margen real por venta**
   - Falta motor de costo (promedio/PEPS) para utilidad bruta real por orden y por producto.
3. **Cuentas por cobrar (ventas a crédito)**
   - Se requiere estado de cuenta por cliente, cuotas, vencimientos, abonos y mora.
4. **Arqueo/cierre de caja por turno o día**
   - Para control operativo y conciliación de métodos de pago.

## Media prioridad
5. **Reserva de inventario con vencimiento operativo**
   - Ya hay base de stock reservado, pero falta política de expiración automática y reasignación.
6. **Aprobaciones operativas**
   - Flujo de aprobación para descuentos, devoluciones complejas, cancelaciones y ajustes manuales.
7. **Comisiones de vendedor/canal**
   - Cálculo por margen/volumen/meta.
8. **Alertas por SLA operacional**
   - Órdenes pendientes por tiempo, transferencias no confirmadas, retomas sin resolución.

## Baja prioridad / expansión
9. **Integraciones externas de canal**
   - APIs directas WhatsApp/Meta para trazabilidad completa de conversación→venta.
10. **Facturación fiscal electrónica**
   - Dependiendo del marco tributario local.

---

## 4) Recomendación por Fases

### Fase 1 (imprescindible – 2 a 4 semanas)
- Módulo de compras/recepción
- Costo unitario y margen real
- Cuentas por cobrar básicas
- Cierre diario de caja

### Fase 2 (optimización – 2 a 3 semanas)
- Política de reserva con expiración
- Aprobaciones por rol
- Comisiones por vendedor/canal

### Fase 3 (escalamiento – 3+ semanas)
- Integraciones de canal
- Facturación fiscal/contable
- KPIs ejecutivos avanzados

---

## 5) KPIs mínimos recomendados para tu operación

- Ventas netas diarias/semanales/mensuales
- Margen bruto real
- Rotación y días de inventario por categoría
- Tasa de quiebre de stock
- Cumplimiento de transferencias (tiempo)
- Conversión por canal
- Ticket promedio por canal y vendedor
- Recuperación de cartera (si hay crédito)

---

## 6) Estado de preparación actual

- Operación comercial diaria: **Sí**
- Escalamiento a varias tiendas/bodegas: **Sí**
- Gobierno por roles/permisos: **Sí**
- Control financiero comercial completo: **Parcial (falta Fase 1)**

---

## 7) Siguiente paso recomendado

Definir el “modelo de ventas real” de tu negocio en 8 decisiones:

1. ¿Vendes a crédito? (sí/no)
2. ¿Necesitas cierre de caja por vendedor o por sucursal?
3. ¿Costo por promedio o PEPS?
4. ¿Descuento libre o por aprobación?
5. ¿Tienes comisiones por vendedor/canal?
6. ¿Qué porcentaje de ventas lleva financiamiento?
7. ¿Qué SLA tienes para transferencias y entregas?
8. ¿Qué reportes exige contabilidad semanalmente?

Con esas respuestas se puede convertir este diagnóstico en backlog técnico listo para implementación.
