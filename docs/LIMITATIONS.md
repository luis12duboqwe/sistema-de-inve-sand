# Limitaciones del Sistema v2.0

## 1. Soporte Multi-moneda
**Estado**: No contemplado (decisión estratégica).
**Descripción**: Aunque el modelo de datos `Product` conserva el campo `moneda` por compatibilidad, la plataforma opera exclusivamente en **Lempiras (HNL)** para ventas, reportes, transferencias y KPIs.
**Impacto**:
- No se realizarán conversiones automáticas ni se mezclarán divisas dentro de una misma operación.
- Cambiar el valor del campo `moneda` en un producto no tiene efecto práctico y se considera solo para trazabilidad.
**Lineamiento**: Todo el catálogo y las órdenes deben configurarse en HNL. El soporte multi-moneda quedó descartado para esta versión; si se reabre, requerirá tablas de tasas de cambio históricas, campos `currency_code` y `fx_rate_applied` en órdenes y reportes multi-moneda.

## 2. Costos Históricos
**Estado**: No implementado.
**Descripción**: El costo del producto se guarda en la tabla `Product`, pero no se copia a `OrderItem` al momento de la venta.
**Impacto**:
- El cálculo de margen de ganancia en reportes históricos usa el costo *actual* del producto, no el costo que tenía al momento de la venta.
- Esto puede generar distorsiones en reportes de meses anteriores si el costo del producto cambia.
**Workaround**: Mantener costos estables o asumir que el margen es una estimación.

## 3. Forecasting (Predicciones)
**Estado**: Básico.
**Descripción**: El módulo de predicción usa una regresión lineal simple sobre el historial de ventas.
**Limitaciones**:
- No detecta estacionalidad compleja (ej. Navidad).
- No filtra eventos atípicos (ventas mayoristas únicas).
- La precisión depende del volumen de datos históricos (mínimo 30-60 días recomendados).

## 4. Base de Datos
**Estado**: SQLite (Por defecto).
**Limitaciones**:
- No recomendada para alta concurrencia de escritura.
- Riesgo de bloqueos ("database is locked") si hay múltiples usuarios escribiendo simultáneamente.
**Recomendación**: Migrar a PostgreSQL para despliegues en producción con múltiples usuarios.
