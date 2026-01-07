# ⚙️ Despliegue Endurecido en Producción

Guía paso a paso para levantar el stack FastAPI + React en un servidor Linux usando Docker Compose, PostgreSQL y los controles de seguridad mínimos descritos en [docs/PROD_INFRA_SECURITY.md](PROD_INFRA_SECURITY.md).

## 1. Requisitos previos
- Docker Engine 24+ y Docker Compose v2.
- Dominio público (por ejemplo `api.midominio.com` y `app.midominio.com`).
- Certificados TLS administrados por el proxy frontal (Caddy/Traefik/Nginx con Let’s Encrypt).
- Variables sensibles generadas previamente (SECRET_KEY, contraseñas de BD, claves de API).

Antes de tocar el servidor, ejecuta localmente:
```bash
cd backend
python check_production_readiness.py
```
El script debe devolver `ready: true`; corrige cualquier advertencia antes de continuar.

## 2. Configurar secretos y variables
1. Copia la plantilla:
   ```bash
   cp deploy/.env.prod.example deploy/.env.prod
   ```
2. Edita `deploy/.env.prod` con valores reales (SECRET_KEY > 32 caracteres, contraseñas fuertes, dominios reales, claves de monitorización).
3. Mantén este archivo fuera de Git (ya está ignorado por `.gitignore`).
4. Cuando trabajes en CI/CD usa gestores de secretos externos (Vault, AWS Secrets Manager o Docker secrets).

Variables críticas a revisar:
- `DATABASE_URL`: usa el host `db` para la red interna del compose.
- `ALLOWED_HOSTS` / `CORS_ORIGINS`: lista explícita de dominios.
- `VITE_API_BASE_URL`: debe apuntar al mismo dominio expuesto por el backend.
- `ENABLE_FILE_LOGGING`, `BACKUP_DIR`: permitidos por los volúmenes `backend_logs` y `backend_backups`.

## 3. Construir imágenes
```bash
cd deploy
# Usa la misma .env tanto para sustitución como para pasar variables a los contenedores
docker compose --env-file ./.env.prod -f docker-compose.prod.yml build
```
El frontend recibe `VITE_API_BASE_URL` como build-arg para que los assets generados apunten al dominio final.

## 4. Levantar el stack
```bash
docker compose --env-file ./.env.prod -f docker-compose.prod.yml up -d
```
Componentes incluidos:
- `db`: PostgreSQL 16 en la red interna (`internal`) con volumen `postgres_data`.
- `backend`: FastAPI/uvicorn con chequeo de salud, logs y backups persistentes.
- `frontend`: build Vite + Nginx sirviendo assets estáticos con cabeceras endurecidas.

Redes:
- `internal`: aísla PostgreSQL del exterior; solo backend puede acceder.
- `edge`: expone backend y frontend para el proxy TLS.

Volúmenes persistentes:
- `postgres_data`: datos de la base.
- `backend_logs`: logs JSON para auditoría.
- `backend_backups`: dumps automáticos (si `ENABLE_AUTO_BACKUP=true`).

## 5. Verificaciones post-arranque
```bash
# Estado de servicios
docker compose -f docker-compose.prod.yml ps

# Logs iniciales
docker compose -f docker-compose.prod.yml logs backend

# Endpoints principales
curl http://localhost:8000/api/health
curl http://localhost:4173
```
Asegúrate de que el healthcheck del backend pasa (el contenedor quedará en `healthy`).

## 6. Proxy TLS y rate limiting
El archivo `deploy/nginx.conf` aplica cabeceras seguras cuando se usa el contenedor de frontend. Aun así, coloca **un reverse proxy externo** delante del stack para:
- Terminar TLS automático con Let’s Encrypt.
- Aplicar `limit_req` o reglas equivalentes (`RATE_LIMIT_PER_MINUTE`).
- Redirigir HTTP→HTTPS (obligatorio para que HSTS tenga efecto).

Ejemplo mínimo con Caddy:
```
api.midominio.com {
    reverse_proxy backend:8000
}
app.midominio.com {
    reverse_proxy frontend:80
}
```

## 7. Backups, logging y monitoreo
- Programa un cron/sidecar que ejecute `pg_dump` hacia `backend_backups` o un bucket externo.
- Revisa `backend/app/config_production.py` para habilitar `SENTRY_DSN`, `NEW_RELIC_LICENSE_KEY` o webhooks de N8N.
- Expone `docker compose logs backend -f` a tu sistema de agregación (Loki, CloudWatch, etc.).
- Monitoriza el endpoint `/api/health` y `/api/ai/status` cada 1-5 minutos.

## 8. Checklist rápido
1. `ENVIRONMENT=production` y `DEBUG=false`.
2. `SECRET_KEY` único y largo.
3. `DATABASE_URL` apunta a PostgreSQL.
4. `check_production_readiness.py` sin advertencias críticas.
5. TLS activo desde el proxy frontal.
6. Backups automáticos habilitados y probados.
7. Logs persistentes (volumen) y rotación configurada.
8. Alertas conectadas (Sentry/N8N/Prometheus).

Con esto el Task 6 (Infraestructura + Seguridad) queda cubierto: stack dockerizado, variables gestionadas por archivo seguro y documentación para reproducir el despliegue.
