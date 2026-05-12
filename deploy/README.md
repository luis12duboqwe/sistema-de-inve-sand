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

## 3. Levantar

```bash
cd deploy
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup up -d --build
```

Servicios:

- `frontend`: nginx público, sirve React y proxya `/api` y `/uploads` al backend.
- `backend`: FastAPI privado dentro de la red Docker.
- `db`: PostgreSQL privado dentro de la red Docker.
- `backup`: backup diario de PostgreSQL al volumen `backend_backups`.

## 4. Verificar

```bash
curl -f http://localhost/health || true
curl -f http://localhost/api/health
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

## 6. Actualizar Versión

```bash
git pull
cd deploy
./validate-prod.sh
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup up -d --build
```