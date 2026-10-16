# SoftMobile — instrucciones vigentes para asistentes de código

## Repositorio y alcance
- **ERP oficial:** `luis12duboqwe/sistema-de-inve-sand`. No confundir con el fork independiente de Chatwoot ni con SoftMarketHn.
- Stack actual: React/Vite/TypeScript y FastAPI/SQLAlchemy, PostgreSQL 16 en producción, Docker Compose, Nginx y GitHub Actions.
- Los datos de negocio productivos vienen **exclusivamente de la API**. `src/lib/runtimePolicy.ts` fuerza el modo API en builds productivas; KV local sólo sirve para laboratorio/desarrollo y preferencias expresamente permitidas.
- Las órdenes, existencias y los IMEIs son globales por producto pero **se autorizan por ubicación**. Un usuario de una tienda no puede consultar detalles de inventario de otra.
- `backend/app/models/`, `backend/app/schemas/`, `backend/app/routers/`, `backend/app/services/` son paquetes; no confiar en guías antiguas que los describen como un único archivo.

## Seguridad innegociable
1. **Nunca** borrar o reconstruir bases reales, resembra datos ficticios, usar `--with-data` en VPS, ejecutar `DROP`/`TRUNCATE` manual ni desactivar las políticas de permisos para lograr un test verde.
2. Antes de cambiar inventario, orden, garantía, devolución, transferencias o dinero: revisar flujo transaccional, concurrencia, IMEI y efecto contable. Todo cambio de stock y estado debe ser atómico.
3. Mantener `sessionStorage` del JWT en frontend, nunca persistir credenciales ni datasets de negocio en `localStorage` productivo.
4. Cualquier request o webhook de integración debe autenticar origen, aplicar idempotencia y no repetir mutaciones cuando la respuesta es incierta.
5. Los tokens de Meta, OpenAI, bases de datos o n8n no deben aparecer en documentos, logs, commits ni datos de tests.
6. Los precios y descuentos se validan en el backend; la IA no autoriza descuentos fuera de `backend/app/utils/ai_sales_policy.py`.
7. Las migraciones existentes son específicas. Crear una migración transaccional con prueba y respaldo; **nunca** indicar a un desarrollador que borre `backend/inventory.db` por un cambio de modelo.

## Auditoría y proceso de cambios
- Revisar `docs/auditoria-continua/HALLAZGOS.json` y el PR de auditoría consolidado antes de dar por corregida una falla.
- Crear PR desde una rama segura. Mantener `main`, el VPS y los datos reales intactos hasta pruebas suficientes y revisión explícita del despliegue.
- Ejecutar: `npm ci --legacy-peer-deps`, `npm run lint`, `npm run test:coverage`, `npm run build`, suite de backend PostgreSQL y CI E2E. Los tests con SQLite no sustituyen la suite en PostgreSQL.
- Tratar cada workflow según su SHA: un check verde de una rama o commit anterior no aprueba cambios nuevos.
- Pruebas negativas obligatorias para permisos por tienda, stock serializado, reintentos, números monetarios, subida de archivos y rollback ante errores.
- La restauración de backups es un procedimiento controlado: verificar hash, importar en **base nueva aislada**, validar contenido y preparar rollback/cutover aparte.
- No declarar “100% terminado” sin evidencia del entorno final; separar claramente corrección en código, CI, despliegue y operación real.

## Referencias de código
- Frontend: `src/App.tsx`, `src/lib/apiClient.ts`, `src/lib/inventoryServiceFactory.ts`, `src/hooks/use-kv.ts`.
- Backend: `backend/app/main.py`, `backend/app/auth.py`, `backend/app/services/order_service.py`, `backend/app/utils/location_access.py`.
- Deploy: `deploy/docker-compose.prod.yml`, `deploy/release-now.sh`, `deploy/ops-healthcheck.sh`, `deploy/restore-backup.sh`.
- Auditoría: `docs/auditoria-continua/`.

**Nota:** una guía de desarrollo histórica no constituye autorización para ejecutar scripts de despliegue, limpiar documentación ni modificar entornos productivos.
