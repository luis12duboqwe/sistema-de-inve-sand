# Despliegue En Produccion

Esta carpeta contiene lo necesario para levantar el sistema con Docker Compose en un servidor Linux.

Para VPS con Nginx + systemd, usa la guia y archivos en [vps/README.md](vps/README.md).

## 1. Preparar variables

```bash
APP_DOMAIN=inventario.tudominio.com ./deploy/prepare-prod-env.sh
```

El script crea `deploy/.env.prod`, genera `SECRET_KEY`, `POSTGRES_PASSWORD` y `CHANNEL_ENCRYPTION_KEY`, y deja el frontend usando `/api` por el proxy nginx interno.

Revisa `deploy/.env.prod` y completa sólo lo que aplique:

- `SENTRY_DSN` para monitoreo de errores.
- `OPENAI_API_KEY` si usarás funciones de IA.
- `SMTP_*` si usarás correos o recuperación.
- `N8N_*` y tokens Meta si usarás WhatsApp/Messenger/Instagram.

## 2. Validar

```bash
cd deploy
./validate-prod.sh
```

## 2.1 Gate Final (recomendado)

Ejecuta validación integral local antes de producción:

```bash
cd deploy
./prod-gate.sh ./.env.prod
```

Este gate cubre:

- validación de env y compose
- lint/build/tests frontend
- tests backend + E2E
- auditoría de dependencias
- escaneo de seguridad de contenedores

Checklist de salida:

- [GO_NO_GO_CHECKLIST.md](GO_NO_GO_CHECKLIST.md)

## 3. Levantar

```bash
cd deploy
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup up -d --build
```

Para levantar observabilidad enterprise (Prometheus + Alertmanager + Grafana):

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup --profile monitoring up -d --build
```

Servicios:

- `frontend`: nginx público, sirve React y proxya `/api` y `/uploads` al backend.
- `backend`: FastAPI privado dentro de la red Docker.
- `db`: PostgreSQL privado dentro de la red Docker.
- `backup`: backup diario de PostgreSQL al volumen `backend_backups`.
- `prometheus` (perfil `monitoring`): métricas y evaluación de alertas.
- `alertmanager` (perfil `monitoring`): envío activo de alertas a webhook.
- `grafana` (perfil `monitoring`): dashboards operativos.

## 4. Verificar

```bash
curl -f http://localhost/health || true
curl -f http://localhost/api/health
curl -f http://localhost/api/ready
curl -f http://localhost/api/metrics
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

Si usarás HTTPS con un proxy externo, apunta tu proxy al puerto configurado en `FRONTEND_PORT`.

## 5. Backup Manual

```bash
cd deploy
./backup-now.sh
```

También puedes pasar una ruta de env explícita:

```bash
./backup-now.sh /ruta/segura/.env.prod
```

El archivo queda en `deploy/backups/` junto con su checksum.

## 6. Restaurar Backup (Recuperación)

```bash
cd deploy
./restore-backup.sh ./.env.prod ./backups/manual_YYYYMMDD_HHMMSS.sql.gz --yes
```

Notas:

- Si existe `*.sha256`, se valida antes de restaurar.
- La restauración escribe sobre la BD objetivo; úsala en una ventana controlada.

## 7. Monitoreo Operativo

Health checks y métricas disponibles:

- `/api/health`: estado general + readiness embebido
- `/api/ready`: readiness de despliegue (200/503)
- `/api/metrics`: métricas runtime (requests, latencia, errores)
- `/api/metrics/prometheus`: formato Prometheus/OpenMetrics

Chequeo integral rápido:

```bash
cd deploy
./ops-healthcheck.sh ./.env.prod
```

## 8. Actualizar Versión

```bash
git pull
cd deploy
./validate-prod.sh
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup up -d --build
```

## 9. Simulacro DR (RTO/RPO)

Ejecuta un drill de recuperación en PostgreSQL temporal y genera reporte JSON:

```bash
cd deploy
./dr-drill.sh ./.env.prod ./backups/manual_YYYYMMDD_HHMMSS.sql.gz
```

Salida esperada:

- `rto_seconds`: tiempo de recuperación medido.
- `rpo_seconds`: antigüedad del backup restaurado.
- `restored_counts`: conteos de tablas críticas tras restauración.

También existe un workflow programado semanal en GitHub Actions: `.github/workflows/dr-drill.yml`.

## 10. Lanzamiento en Un Solo Comando

Flujo recomendado (validación, gate, despliegue y healthcheck):

```bash
./deploy/release-now.sh ./deploy/.env.prod
```

Opcional: desactivar stack de monitoreo en el lanzamiento:

```bash
USE_MONITORING=false ./deploy/release-now.sh ./deploy/.env.prod
```