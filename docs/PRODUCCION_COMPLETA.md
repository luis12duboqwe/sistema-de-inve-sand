# Guía de Producción

> **Documento actualizado:** la guía histórica de instalación manual fue reemplazada por el runbook productivo basado en Docker Compose, PostgreSQL, gates de release y backup off-site.

La fuente canónica actual es:

**[`PRODUCCION_FINAL.md`](./PRODUCCION_FINAL.md)**

## Ruta corta

Desde la raíz del repositorio:

```bash
APP_DOMAIN=inventario.tudominio.com ./deploy/prepare-prod-env.sh
```

Completa `deploy/.env.prod` con los valores externos, incluido el destino off-site y sus credenciales.

```bash
./deploy/validate-prod.sh ./deploy/.env.prod
```

Después:

```bash
cd deploy
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  --profile backup \
  --profile backup-offsite \
  up -d --build
```

No uses las instrucciones antiguas de migración manual, crontab/systemd o arranque productivo con `uvicorn --reload`. Se conservan en el historial de Git si hace falta consultar cómo evolucionó el proyecto.

## Reglas actuales

- PostgreSQL obligatorio.
- API obligatoria en frontend productivo.
- Sin bypass local cuando el backend está caído.
- Migraciones versionadas y fail-fast.
- Backup local verificado + copia off-site.
- CI + Release Gate + DR drill antes de considerar estable una versión.

Consulta [`PRODUCCION_FINAL.md`](./PRODUCCION_FINAL.md) para todos los detalles.
