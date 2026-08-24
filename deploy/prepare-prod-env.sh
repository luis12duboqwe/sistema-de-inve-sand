#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
EXAMPLE_FILE="$DEPLOY_DIR/.env.prod.example"

generate_hex() {
  local bytes="$1"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$bytes"
  else
    python3 - <<PY
import secrets
print(secrets.token_hex($bytes))
PY
  fi
}

generate_fernet_key() {
  # Fernet keys are URL-safe base64 encodings of exactly 32 random bytes. Use
  # only Python's standard library so a clean Docker host does not need the
  # backend's `cryptography` package installed just to prepare its environment.
  python3 - <<'PY'
import base64
import secrets
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
PY
}

get_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -n 1 | cut -d'=' -f2- || true
}

is_placeholder() {
  local value="$1"
  case "$value" in
    *CHANGE_ME*|*GENERATE_WITH*|*midominio.com*|*example.com*) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_value() {
  local key="$1"
  local fallback="$2"
  local env_value="${!key-}"
  local existing

  if [ -n "$env_value" ]; then
    printf '%s' "$env_value"
    return
  fi

  existing="$(get_env "$key")"
  if [ -n "$existing" ] && ! is_placeholder "$existing"; then
    printf '%s' "$existing"
    return
  fi

  printf '%s' "$fallback"
}

resolve_hex_secret() {
  local key="$1"
  local bytes="$2"
  local env_value="${!key-}"
  local existing

  if [ -n "$env_value" ]; then
    printf '%s' "$env_value"
    return
  fi

  existing="$(get_env "$key")"
  if [ -n "$existing" ] && ! is_placeholder "$existing"; then
    printf '%s' "$existing"
    return
  fi

  generate_hex "$bytes"
}

resolve_fernet_secret() {
  local env_value="${CHANNEL_ENCRYPTION_KEY-}"
  local existing

  if [ -n "$env_value" ]; then
    printf '%s' "$env_value"
    return
  fi

  existing="$(get_env CHANNEL_ENCRYPTION_KEY)"
  if [ -n "$existing" ] && ! is_placeholder "$existing"; then
    printf '%s' "$existing"
    return
  fi

  generate_fernet_key
}

set_env() {
  local key="$1"
  local value="$2"
  local escaped
  escaped="$(printf '%s' "$value" | sed 's/[&|\\]/\\&/g')"

  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i.bak "s|^${key}=.*|${key}=${escaped}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
  rm -f "$ENV_FILE.bak"
}

if [ ! -f "$ENV_FILE" ]; then
  cp "$EXAMPLE_FILE" "$ENV_FILE"
fi

# Capture explicit DB overrides before assigning resolved local values. When no
# override is supplied, an existing DATABASE_URL is authoritative and must not be
# reconstructed: it may contain URL-encoded credentials or a custom topology.
DB_COMPONENT_OVERRIDE=false
for db_key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD; do
  if [ -n "${!db_key-}" ]; then
    DB_COMPONENT_OVERRIDE=true
    break
  fi
done
DATABASE_URL_OVERRIDE="${DATABASE_URL-}"

APP_DOMAIN="${APP_DOMAIN:-}"
if [ -z "$APP_DOMAIN" ]; then
  EXISTING_CORS="$(get_env CORS_ORIGINS)"
  if [ -n "$EXISTING_CORS" ] && ! is_placeholder "$EXISTING_CORS"; then
    APP_DOMAIN="${EXISTING_CORS%%,*}"
    APP_DOMAIN="${APP_DOMAIN#https://}"
    APP_DOMAIN="${APP_DOMAIN#http://}"
    APP_DOMAIN="${APP_DOMAIN%/}"
  elif [ -t 0 ]; then
    read -r -p "Dominio público sin https:// (ej: inventario.midominio.com): " APP_DOMAIN
  fi
fi
APP_DOMAIN="${APP_DOMAIN:-inventario.midominio.com}"

POSTGRES_DB_VALUE="$(resolve_value POSTGRES_DB inventory)"
POSTGRES_USER_VALUE="$(resolve_value POSTGRES_USER inventory_admin)"
POSTGRES_PASSWORD_VALUE="$(resolve_hex_secret POSTGRES_PASSWORD 24)"
SECRET_KEY_VALUE="$(resolve_hex_secret SECRET_KEY 32)"
CHANNEL_ENCRYPTION_KEY_VALUE="$(resolve_fernet_secret)"
SETUP_TOKEN_VALUE="$(resolve_hex_secret SETUP_TOKEN 32)"
DESTRUCTIVE_OPERATION_TOKEN_VALUE="$(resolve_hex_secret DESTRUCTIVE_OPERATION_TOKEN 32)"
GRAFANA_ADMIN_PASSWORD_VALUE="$(resolve_hex_secret GRAFANA_ADMIN_PASSWORD 24)"

DATABASE_URL_VALUE="$DATABASE_URL_OVERRIDE"
if [ -z "$DATABASE_URL_VALUE" ]; then
  EXISTING_DATABASE_URL="$(get_env DATABASE_URL)"
  if [ "$DB_COMPONENT_OVERRIDE" = false ] \
     && [ -n "$EXISTING_DATABASE_URL" ] \
     && ! is_placeholder "$EXISTING_DATABASE_URL"; then
    DATABASE_URL_VALUE="$EXISTING_DATABASE_URL"
  else
    DATABASE_URL_VALUE="postgresql+psycopg2://${POSTGRES_USER_VALUE}:${POSTGRES_PASSWORD_VALUE}@db:5432/${POSTGRES_DB_VALUE}"
  fi
fi

set_env FRONTEND_PORT "$(resolve_value FRONTEND_PORT 80)"
set_env POSTGRES_DB "$POSTGRES_DB_VALUE"
set_env POSTGRES_USER "$POSTGRES_USER_VALUE"
set_env POSTGRES_PASSWORD "$POSTGRES_PASSWORD_VALUE"
set_env DATABASE_URL "$DATABASE_URL_VALUE"
set_env ENVIRONMENT production
set_env DEBUG false
set_env SECRET_KEY "$SECRET_KEY_VALUE"
set_env CHANNEL_ENCRYPTION_KEY "$CHANNEL_ENCRYPTION_KEY_VALUE"
set_env SETUP_TOKEN "$SETUP_TOKEN_VALUE"
set_env DESTRUCTIVE_OPERATION_TOKEN "$DESTRUCTIVE_OPERATION_TOKEN_VALUE"
set_env ENABLE_DESTRUCTIVE_PURGE "$(resolve_value ENABLE_DESTRUCTIVE_PURGE false)"
set_env ALLOWED_HOSTS "$(resolve_value ALLOWED_HOSTS "$APP_DOMAIN,localhost,127.0.0.1")"
set_env CORS_ORIGINS "$(resolve_value CORS_ORIGINS "https://${APP_DOMAIN}")"
set_env VITE_API_BASE_URL "$(resolve_value VITE_API_BASE_URL /api)"
set_env LOG_STRUCTURED "$(resolve_value LOG_STRUCTURED true)"
set_env LOG_TO_FILES "$(resolve_value LOG_TO_FILES true)"
set_env LOG_DIRECTORY "$(resolve_value LOG_DIRECTORY /app/logs)"
set_env LOG_INCLUDE_CONSOLE "$(resolve_value LOG_INCLUDE_CONSOLE true)"
set_env ENABLE_AUTO_BACKUP "$(resolve_value ENABLE_AUTO_BACKUP true)"
set_env BACKUP_DIR "$(resolve_value BACKUP_DIR /app/backups)"
set_env BACKUP_RETENTION_DAYS "$(resolve_value BACKUP_RETENTION_DAYS 30)"
set_env BACKUP_INTERVAL_SECONDS "$(resolve_value BACKUP_INTERVAL_SECONDS 86400)"
set_env MIN_BACKUP_BYTES "$(resolve_value MIN_BACKUP_BYTES 1024)"
set_env REQUIRE_OFFSITE_BACKUP "$(resolve_value REQUIRE_OFFSITE_BACKUP true)"
set_env BACKUP_OFFSITE_INTERVAL_SECONDS "$(resolve_value BACKUP_OFFSITE_INTERVAL_SECONDS 3600)"
set_env GRAFANA_ADMIN_PASSWORD "$GRAFANA_ADMIN_PASSWORD_VALUE"
if [ -n "${BACKUP_RCLONE_DESTINATION:-}" ]; then
  set_env BACKUP_RCLONE_DESTINATION "$BACKUP_RCLONE_DESTINATION"
fi

chmod 600 "$ENV_FILE"

cat <<EOF2
Archivo de producción preparado: $ENV_FILE

Revisa estos valores antes de levantar:
  - ALLOWED_HOSTS / CORS_ORIGINS: $(get_env ALLOWED_HOSTS) / $(get_env CORS_ORIGINS)
  - SETUP_TOKEN: úsalo sólo para crear el primer administrador
  - ENABLE_DESTRUCTIVE_PURGE: debe permanecer en false salvo una operación autorizada
  - BACKUP_RCLONE_DESTINATION: configura un destino fuera de este servidor
  - RCLONE_CONFIG_*: configura credenciales del remote sólo en .env.prod/secret manager
  - GRAFANA_ADMIN_PASSWORD: generado automáticamente si faltaba; custódialo fuera de Git
  - SENTRY_DSN: opcional, recomendado
  - OPENAI_API_KEY: requerido sólo si usarás IA
  - SMTP_*: requerido sólo si usarás email/recuperación
  - N8N_* y Meta tokens: requeridos sólo para WhatsApp/Messenger/Instagram

Los secretos existentes válidos se conservan al volver a ejecutar este script. Para rotar
un valor, pásalo explícitamente como variable de entorno y valida el impacto antes de aplicar.

Siguiente paso:
  cd $DEPLOY_DIR
  ./validate-prod.sh
  docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup --profile backup-offsite up -d --build
EOF2
