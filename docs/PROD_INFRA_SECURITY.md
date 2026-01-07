# 🛡️ Guía de Infraestructura y Seguridad para Producción

> Objetivo: desplegar el backend FastAPI + frontend Vite en un entorno endurecido con PostgreSQL, TLS y controles básicos de seguridad.

> Para un paso a paso operativo del stack Docker consulta [docs/DEPLOYMENT_PROD.md](DEPLOYMENT_PROD.md).

## 1. Preparar variables de entorno

1. Copia `backend/.env.example` a `backend/.env` y personaliza:
   - `DATABASE_URL=postgresql+psycopg2://USER:PASS@db:5432/inventory`
   - `SECRET_KEY=$(openssl rand -hex 32)`
   - `CORS_ORIGINS=https://app.midominio.com,https://admin.midominio.com`
   - `ALLOWED_HOSTS=api.midominio.com`
   - Ajusta `RATE_LIMIT_PER_MINUTE`, `LOGIN_ATTEMPTS_LIMIT` y `LOGIN_BLOCK_TIME` si usarás rate limiting a nivel middleware/proxy.
2. Exporta también `VITE_API_BASE_URL` para el frontend antes de build (`export VITE_API_BASE_URL=https://api.midominio.com`).

## 2. Provisionar PostgreSQL y servicios con Docker Compose

1. Revisa / ajusta `deploy/docker-compose.prod.yml` (credenciales, puertos, dominios).
2. Construye las imágenes:
   ```bash
   cd deploy
   docker compose -f docker-compose.prod.yml build
   ```
3. Levanta el stack:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
4. Verifica salud:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   curl http://localhost:8000/api/health
   curl http://localhost:4173
   ```

### Componentes incluidos
- `postgres:16-alpine` con volumen persistente `postgres_data`.
- Backend FastAPI (Dockerfile en `backend/`) sirviendo en el puerto 8000.
- Frontend estático servido por Nginx (Dockerfile `Dockerfile.frontend` + `deploy/nginx.conf`).

## 3. TLS y reverse proxy

Se recomienda colocar un proxy (Caddy, Nginx, Traefik) delante de los contenedores para manejar certificados Let’s Encrypt.

Ejemplo Caddyfile (no incluido en repo):
```
api.midominio.com {
    reverse_proxy backend:8000
}
app.midominio.com {
    reverse_proxy frontend:80
}
```

## 4. Endurecimiento del backend

- `TrustedHostMiddleware` ya está configurado; entra en vigor en producción si `ALLOWED_HOSTS` ≠ `['*']`.
- `prod_settings.SECURITY_HEADERS` se aplican automáticamente cuando `ENVIRONMENT=production`.
- El archivo `backend/.env` no debe versionarse. Usa `docker secrets` o un gestor externo para claves sensibles.
- Habilita backups automáticos configurando `ENABLE_AUTO_BACKUP=true` y definiendo `BACKUP_DIR` si ejecutas cronjobs.

## 5. Rate limiting y login protection

El módulo `app/config_production.py` expone parámetros que pueden ser usados por un middleware personalizado o por el proxy:
- `RATE_LIMIT_PER_MINUTE`: usar con Nginx (`limit_req_zone`) o Traefik para frenar abuso.
- `LOGIN_ATTEMPTS_LIMIT` + `LOGIN_BLOCK_TIME`: útiles para implementar lockout en el endpoint de login (pendiente si se requiere backend-level enforcement).

## 6. Logging y monitoreo

- Configura `LOG_DIR`, `LOG_FORMAT=json` y habilita `ENABLE_FILE_LOGGING=true` para obtener logs estructurados.
- Integra Sentry o New Relic exportando `SENTRY_DSN` / `NEW_RELIC_LICENSE_KEY` según `config_production`.
- Usa `docker logs backend -f` y `tail -f backend/logs/app.log` durante las primeras horas post-deploy.

## 7. Gestión de usuarios y roles (Consola RBAC)

- La consola `ManageUsersDialog` solo aparece cuando la app corre en **modo API** (`settings_use_api=true`). Debes iniciar sesión con un usuario que tenga el permiso `users:manage` o un rol system (`Super Admin`).
- Desde la UI (icono de escudo en la barra superior o Configuración → "Gestionar Usuarios"), puedes:
   1. Crear usuarios (username, nombre, email, contraseña inicial y rol).
   2. Cambiar rol mediante `RoleSelect` (envía `PUT /api/users/{id}/role`).
   3. Activar/desactivar cuentas y forzar reseteo de contraseña.
   4. Eliminar usuarios no system (se bloquea `is_superuser`).
- Todos los cambios golpean directamente los endpoints del backend (`listUsers`, `updateUser`, `updateUserRole`, `deleteUser`, `createUser`). Asegúrate de que el proxy solo exponga la consola en redes confiables.
- Para auditoría, monitorea los logs del backend (`users:manage` produce entradas en `backend_logs`). Configura alertas si ocurre un 403 repetido (indicador de intentos no autorizados).

## 8. Checklist rápido antes de exponer producción

- [ ] `ENVIRONMENT=production` y `DEBUG=false`.
- [ ] `DATABASE_URL` apunta a PostgreSQL (no SQLite).
- [ ] `SECRET_KEY` seguro (>32 chars) y diferente entre ambientes.
- [ ] `CORS_ORIGINS` / `ALLOWED_HOSTS` restringidos a dominios válidos.
- [ ] TLS activo en los dominios públicos.
- [ ] Backups diarios configurados (dump + copias fuera del servidor).
- [ ] Monitoreo (Sentry/Prometheus/APM) apuntando al backend.
- [ ] `python backend/check_production_readiness.py` retorna `ready=true`.

Con estos pasos el proyecto queda listo para operar en un entorno productivo con una base sólida de seguridad y mantenimiento.
