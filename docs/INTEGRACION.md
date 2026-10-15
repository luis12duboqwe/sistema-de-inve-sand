# Integración Frontend + Backend — SoftMobile

> Referencia histórica actualizada durante la auditoría. **No usar los ejemplos antiguos de SQLite productivo, resiembra de datos de muestra ni switches de almacenamiento local para producción.**

## Arquitectura vigente
- Frontend React/Vite/TypeScript y API FastAPI con PostgreSQL 16 para producción.
- En una compilación productiva, el frontend usa **exclusivamente la API** y falla cerrado cuando está indisponible.
- La sucursal de origen determina la ubicación del stock; las operaciones con IMEI, ventas, garantías y transferencias tienen permisos y garantías transaccionales.
- El modo KV/SQLite sigue limitado a desarrollo y escenarios explícitamente descartables.
- Los datos comerciales, identificadores de cuenta e historiales no deben persistirse en KV compartido entre usuarios.

## Ejecución local (desarrollo)
Utilizar las dependencias y variables de entorno del proyecto. Las pruebas automatizadas se ejecutan a través de GitHub Actions y las instrucciones vigentes de `README.md`/`docs/PRODUCCION_FINAL.md`. No realizar `init_db.py --with-data` en ninguna base compartida o de producción.

## Producción
La única ruta de referencia es [Producción Final](PRODUCCION_FINAL.md): configurar secretos sin subirlos a Git, `validate-prod.sh`, CI, backups locales y externos, restauración aislada verificable, gate de release y despliegue con rollback. Si falta cualquier requisito, **NO desplegar**.

## Automatización n8n/Meta
Ver [Integración n8n](INTEGRACION_N8N.md). El JSON de ejemplo es un **borrador de integración de webhook**, no una automatización de Meta/WhatsApp lista para clientes; tiene que incorporar verificación de origen, envío real con proveedor, manejo de reintentos e idempotencia.
