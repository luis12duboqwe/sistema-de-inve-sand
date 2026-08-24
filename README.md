# Sistema de Inventario Multi-Ubicación

Sistema de inventario y ventas para operación multi-tienda, con frontend React/Vite, API FastAPI y PostgreSQL como base productiva.

## Estado del proyecto

**Estado actual: candidato a producción.**

La base funcional y el endurecimiento técnico principal ya están integrados en `main`: política API-only, integridad de ventas e inventario, permisos por ubicación, migraciones versionadas, recuperación off-site preparada y gates automáticos de seguridad/CI. La fase pendiente antes del release es principalmente operativa y requiere infraestructura, secretos y verificaciones reales de producción.

No debe considerarse un release productivo hasta que:

1. CI del PR final esté en verde.
2. `./deploy/validate-prod.sh` pase con secretos y dominio reales.
3. Se configure un destino de backup fuera del host.
4. Se ejecute y verifique una restauración/DR drill.
5. `main` tenga protección de rama con PR y checks obligatorios.

## Arquitectura

- **Frontend:** React 19 + TypeScript + Vite.
- **Backend:** FastAPI + SQLAlchemy.
- **Base de datos productiva:** PostgreSQL 16.
- **Despliegue:** Docker Compose.
- **Seguridad:** JWT, RBAC, permisos por ubicación, rate limiting, guardas productivas y auditoría.
- **Observabilidad:** logs estructurados, Sentry opcional, Prometheus/Alertmanager/Grafana.
- **Backups:** `pg_dump` comprimido + SHA-256 + réplica off-site con rclone.
- **CI:** lint, frontend tests/coverage, backend PostgreSQL, E2E, auditoría de dependencias y Trivy.

## Regla de datos en producción

El frontend productivo **siempre usa la API**. El modo local existe únicamente para desarrollo y pruebas.

Si el backend no está disponible, la aplicación productiva muestra un bloqueo de conexión y permite reintentar. No existe bypass para continuar escribiendo en almacenamiento local.

## Inicio local

Requisitos:

- Node.js 22 recomendado.
- Python 3.11.
- PostgreSQL para ejecutar la suite completa del backend.

```bash
npm ci --legacy-peer-deps
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

Para usar los scripts existentes de desarrollo:

```bash
./start-all.sh
```

Frontend: `http://localhost:5173`

Backend: `http://localhost:8000/docs`

## Pruebas

Frontend:

```bash
npm run lint
npm run test:coverage
npm run build
```

Backend:

```bash
cd backend
pytest --cov=app --cov-report=term-missing -ra
```

E2E principales:

```bash
pytest -q tests/test_health_endpoints.py
pytest -q tests/e2e/test_runtime_e2e.py tests/e2e/test_business_flows_e2e.py
pytest -q tests/e2e/test_postgres_runtime_e2e.py
```

## Producción

Genera el archivo de entorno:

```bash
APP_DOMAIN=inventario.tudominio.com ./deploy/prepare-prod-env.sh
```

Después completa los valores externos que no se pueden generar automáticamente, especialmente `BACKUP_RCLONE_DESTINATION` y las credenciales `RCLONE_CONFIG_*` del proveedor elegido.

Valida antes de levantar:

```bash
./deploy/validate-prod.sh ./deploy/.env.prod
```

Despliegue recomendado:

```bash
cd deploy
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  --profile backup \
  --profile backup-offsite \
  up -d --build
```

El perfil de monitoreo puede agregarse con `--profile monitoring`.

## Migraciones

Al arrancar, SQLAlchemy crea tablas faltantes y el runner de compatibilidad aplica migraciones versionadas pendientes. Las migraciones aplicadas quedan registradas en `schema_migrations` y el backend valida columnas críticas antes de aceptar tráfico.

Un error de migración detiene el arranque: el sistema no debe operar con un esquema parcial.

## Recuperación

- Los backups locales se almacenan en el volumen `backend_backups`.
- Cada backup publicado debe tener checksum SHA-256.
- `backup-offsite` replica archivos verificados fuera del host.
- `.github/workflows/dr-drill.yml` ejecuta el ejercicio de restauración en staging cuando los secretos de staging están configurados.

## Documentación canónica

- [`COMIENZA_AQUI.md`](./COMIENZA_AQUI.md): ruta rápida para desarrollo y producción.
- [`docs/PRODUCCION_FINAL.md`](./docs/PRODUCCION_FINAL.md): guía productiva canónica.
- [`CHECKLIST_PRODUCCION.md`](./CHECKLIST_PRODUCCION.md): checklist previo al release.
- [`DEPLOY_CHECKLIST.md`](./DEPLOY_CHECKLIST.md): comandos de despliegue y rollback.
- [`docs/ARQUITECTURA.md`](./docs/ARQUITECTURA.md): arquitectura funcional.

Los documentos históricos de auditorías anteriores se conservan únicamente como referencia del proceso; ante una contradicción prevalecen este README y `docs/PRODUCCION_FINAL.md`.
