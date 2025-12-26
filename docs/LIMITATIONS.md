# Limitaciones del Sistema v2.0

## 1. Soporte Multi-moneda
**Estado**: Parcial / No implementado completamente.
**Descripción**: Aunque el modelo de datos `Product` tiene un campo `moneda`, el sistema asume actualmente una moneda base única (Lps) para todas las operaciones de venta y reportes.
**Impacto**:
- Los totales de las órdenes se suman aritméticamente sin conversión de divisas.
- Los reportes financieros asumen que todos los montos están en la misma moneda.
**Recomendación**: Para esta versión, utilizar una única moneda para todos los productos. El soporte real multi-moneda requeriría tablas de tasas de cambio históricas y lógica de conversión en tiempo real.

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
