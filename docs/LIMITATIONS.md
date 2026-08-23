# Limitaciones del Sistema v2.0

Este documento enumera únicamente limitaciones **vigentes**. Las limitaciones históricas ya corregidas se eliminan para evitar contradicciones con el código y la documentación productiva canónica.

## 1. Soporte Multi-moneda
**Estado**: No contemplado en v2.0 (decisión estratégica).

Aunque `Product` conserva el campo `moneda` por compatibilidad, la operación comercial, cierres y KPIs están diseñados para **Lempiras (HNL)**.

**Limitaciones**:
- No hay conversión automática de divisas.
- No se deben mezclar monedas dentro de una misma venta.
- No existen tasas de cambio históricas aplicadas por transacción.

Si se reabre esta función en una versión futura, deberá incorporarse `currency_code`, tasa aplicada a la operación y contabilidad/reportes multi-moneda.

## 2. Costos históricos
**Estado**: ✅ Implementado.

Cada `OrderItem` conserva `costo_unitario` en el momento de la venta. Los reportes financieros y Business Insights usan ese costo histórico, con fallback al costo actual únicamente para registros legacy donde el costo histórico no exista.

Por lo tanto, cambiar posteriormente `Product.costo` **no debe alterar el margen histórico de ventas nuevas**.

## 3. Fecha contable de la venta
**Estado**: ✅ Implementado con compatibilidad legacy.

Las órdenes conservan dos conceptos distintos:
- `created_at`: momento en que se creó la orden.
- `completed_at`: momento en que se convirtió realmente en una venta finalizada.

Reportes, cierres y Business Insights usan `completed_at`, con fallback conservador a `validada_at/created_at` para registros históricos anteriores a esta migración.

## 4. Forecasting (predicciones)
**Estado**: Básico/BETA.

El forecasting actual es determinista y suficiente para alertas operativas, pero no sustituye un modelo estadístico avanzado.

**Limitaciones**:
- No modela estacionalidad compleja de manera avanzada.
- No incorpora automáticamente promociones, feriados ni factores externos.
- Su precisión depende de disponer de suficiente historial de ventas.

## 5. Inteligencia Artificial
**Estado**: Opcional/BETA supervisada.

Las operaciones principales de inventario, ventas, transferencias, devoluciones, cierres y reportes no dependen de IA.

`ENABLE_AI_FEATURES=false` es una configuración válida. Las integraciones externas deben habilitarse únicamente cuando sus secretos, autenticación y pruebas estén completos.

## 6. Canales Meta / automatización
**Estado**: Requiere configuración externa real.

El código soporta WhatsApp, Messenger e Instagram, pero la disponibilidad real depende de credenciales y configuración de Meta.

En producción:
- Los webhooks Meta fallan cerrados si falta `META_APP_SECRET`.
- Las solicitudes de fotos de servicio fallan cerradas si falta `N8N_AUTH_TOKEN`.
- El health de canales no debe marcar la integración como lista si la validación de firma no está habilitada.

## 7. WebSocket de solicitudes de fotos
**Estado**: Preparado para instancia única.

La autenticación usa JWT mediante subprotocolo WebSocket, no query string. El broadcaster actual es en memoria, por lo que una instalación horizontal con varias réplicas del backend necesitará Redis/Kafka u otro bus compartido para eventos en tiempo real.

## 8. Base de datos
**Desarrollo/compatibilidad**: SQLite sigue soportado para desarrollo, pruebas y actualización de instalaciones legacy.

**Producción**: PostgreSQL 16 es la base canónica.

La migración SQLite → PostgreSQL, auditoría previa/posterior, backups y rollback están documentados en la guía productiva. No debe operarse una instalación multiusuario productiva nueva sobre SQLite.

## 9. Infraestructura pendiente antes del primer release estable
El repositorio puede ser candidato técnico, pero no existe release estable hasta completar el checklist de producción real:
- reglas de tags `v*`;
- backup off-site real;
- DR drill en staging;
- migración/verificación de los datos reales;
- dominio/HTTPS;
- smoke tests operativos.

La fuente canónica para ese proceso es `docs/PRODUCCION_FINAL.md` y el Issue #38.
