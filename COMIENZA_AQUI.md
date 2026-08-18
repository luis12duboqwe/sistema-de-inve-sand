# Comienza aquí

Esta guía reemplaza el quickstart antiguo basado en configuración manual de PostgreSQL/Sentry.

## Desarrollo

```bash
npm ci --legacy-peer-deps
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
./start-all.sh
```

Frontend: `http://localhost:5173`

Backend/Swagger: `http://localhost:8000/docs`

El modo local puede usarse únicamente en desarrollo/pruebas.

## Antes de enviar cambios

```bash
npm run lint
npm run test:coverage
npm run build

cd backend
pytest --cov=app --cov-report=term-missing -ra
```

La suite completa del backend requiere PostgreSQL.

## Producción

1. Genera configuración:

```bash
APP_DOMAIN=inventario.tudominio.com ./deploy/prepare-prod-env.sh
```

2. Configura un destino off-site real en `deploy/.env.prod`, por ejemplo:

```env
BACKUP_RCLONE_DESTINATION=offsite:mi-bucket/inventory
```

Añade las credenciales `RCLONE_CONFIG_*` correspondientes en el mismo entorno/secret manager, nunca en Git.

3. Valida:

```bash
./deploy/validate-prod.sh ./deploy/.env.prod
```

4. Levanta:

```bash
cd deploy
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  --profile backup \
  --profile backup-offsite \
  up -d --build
```

5. Comprueba:

```bash
curl -fsS https://inventario.tudominio.com/api/ready
curl -fsS https://inventario.tudominio.com/api/health
```

## Importante

En producción el frontend **no puede cambiar a almacenamiento local**. Si el backend falla, la interfaz bloquea la operación y muestra la opción de reintentar.

Las migraciones de compatibilidad son versionadas y quedan registradas en `schema_migrations`. Un error de migración detiene el arranque.

## Sigue con

Lee [`docs/PRODUCCION_FINAL.md`](docs/PRODUCCION_FINAL.md) para el procedimiento completo, backups, DR drill, release gate, protección de `main` y rollback.
