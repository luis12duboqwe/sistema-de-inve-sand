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
  python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
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

APP_DOMAIN="${APP_DOMAIN:-}"
if [ -z "$APP_DOMAIN" ] && [ -t 0 ]; then
  read -r -p "Dominio público sin https:// (ej: inventario.midominio.com): " APP_DOMAIN
fi
APP_DOMAIN="${APP_DOMAIN:-inventario.midominio.com}"

POSTGRES_DB="${POSTGRES_DB:-inventory}"
POSTGRES_USER="${POSTGRES_USER:-inventory_admin}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(generate_hex 24)}"
SECRET_KEY="${SECRET_KEY:-$(generate_hex 32)}"
CHANNEL_ENCRYPTION_KEY="${CHANNEL_ENCRYPTION_KEY:-$(generate_fernet_key)}"

set_env FRONTEND_PORT "${FRONTEND_PORT:-80}"
set_env POSTGRES_DB "$POSTGRES_DB"
set_env POSTGRES_USER "$POSTGRES_USER"
set_env POSTGRES_PASSWORD "$POSTGRES_PASSWORD"
set_env DATABASE_URL "postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
set_env ENVIRONMENT production
set_env DEBUG false
set_env SECRET_KEY "$SECRET_KEY"
set_env CHANNEL_ENCRYPTION_KEY "$CHANNEL_ENCRYPTION_KEY"
set_env ALLOWED_HOSTS "$APP_DOMAIN,localhost,127.0.0.1"
set_env CORS_ORIGINS "https://${APP_DOMAIN}"
set_env VITE_API_BASE_URL /api
set_env LOG_STRUCTURED true
set_env LOG_TO_FILES true
set_env LOG_DIRECTORY /app/logs
set_env LOG_INCLUDE_CONSOLE true
set_env ENABLE_AUTO_BACKUP true
set_env BACKUP_DIR /app/backups
set_env BACKUP_RETENTION_DAYS "${BACKUP_RETENTION_DAYS:-30}"
set_env BACKUP_INTERVAL_SECONDS "${BACKUP_INTERVAL_SECONDS:-86400}"

chmod 600 "$ENV_FILE"

cat <<EOF
Archivo de producción preparado: $ENV_FILE

Revisa estos valores antes de levantar:
  - APP_DOMAIN / ALLOWED_HOSTS: $APP_DOMAIN
  - SENTRY_DSN: opcional, recomendado
  - OPENAI_API_KEY: requerido sólo si usarás IA
  - SMTP_*: requerido sólo si usarás email/recuperación
  - N8N_* y Meta tokens: requeridos sólo para WhatsApp/Messenger/Instagram

Siguiente paso:
  cd $DEPLOY_DIR
  ./validate-prod.sh
  docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup up -d --build
EOF