# 📦 Sistema de Inventario Multi-Ubicación v2.0

Sistema de gestión de inventario avanzado con soporte para múltiples ubicaciones físicas (tiendas, bodegas) y múltiples canales de venta.

## 🚀 Estado del Proyecto

✅ **PROYECTO COMPLETADO Y AUDITADO** (Diciembre 2025)

El sistema ha pasado por una auditoría completa, corrección de bugs críticos y validación exhaustiva.

*   **Bugs Arreglados**: 15 críticos/importantes
*   **Tests**: 24/24 pasados (100%)
*   **Status**: Listo para Producción

## 📚 Documentación

Toda la documentación técnica se encuentra en la carpeta [`docs/`](./docs/):

*   **[Guía de Inicio Rápido](./INICIO_RAPIDO.md)**: Cómo levantar el sistema en 5 minutos.
*   **[Arquitectura](./docs/ARQUITECTURA.md)**: Detalles del diseño v2.0.
*   **[Manual Completo](./docs/MANUAL_COMPLETO.md)**: Guía detallada de uso y testing.
*   **[Deployment](./docs/DEPLOYMENT.md)**: Guía paso a paso para puesta en producción.
*   **[Auditoría](./docs/AUDITORIA.md)**: Registro de bugs encontrados y arreglados.

## 🛠️ Inicio Rápido

### Requisitos
*   Node.js 18+
*   Python 3.11+

### Ejecución

```bash
# Opción 1: Script automático (Recomendado)
./start-all.sh

# Opción 2: Manual
# Terminal 1 (Backend)
./start-backend.sh

# Terminal 2 (Frontend)
./start-frontend.sh
```

*   **Frontend**: http://localhost:5173
*   **Backend API**: http://localhost:8000/docs

## 🧪 Testing

Para ejecutar las pruebas de validación:

```bash
# Ejecutar tests de backend y frontend
./test-system.sh
```

Ver resultados detallados en [`docs/TESTING_RESULTS.md`](./docs/TESTING_RESULTS.md).

## 🔐 Seguridad

El sistema implementa:
*   Transacciones atómicas para integridad de datos.
*   Validación estricta de stock e IMEI.
*   Manejo de errores robusto.

Ver detalles en [`docs/SEGURIDAD.md`](./docs/SEGURIDAD.md).

---
**v2.0.0** - Ready for Production
