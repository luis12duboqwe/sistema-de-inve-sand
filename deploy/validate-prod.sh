#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE. Ejecuta: ./deploy/prepare-prod-env.sh" >&2
  exit 1
fi

if grep -Eq 'CHANGE_ME|GENERATE_WITH|midominio\.com|api\.example\.com|example\.com' "$ENV_FILE"; then
  echo "Hay placeholders pendientes en $ENV_FILE. Edita el archivo antes de producción." >&2
  grep -En 'CHANGE_ME|GENERATE_WITH|midominio\.com|api\.example\.com|example\.com' "$ENV_FILE" >&2 || true
  exit 1
fi

if grep -Eq '^CORS_ORIGINS=\*$' "$ENV_FILE"; then
  echo "CORS_ORIGINS no puede ser '*' en producción" >&2
  exit 1
fi

if grep -Eq '^ALLOWED_HOSTS=\*$' "$ENV_FILE"; then
  echo "ALLOWED_HOSTS no puede ser '*' en producción" >&2
  exit 1
fi

required=(
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD
  DATABASE_URL
  ENVIRONMENT
  SECRET_KEY
  CHANNEL_ENCRYPTION_KEY
  ALLOWED_HOSTS
  CORS_ORIGINS
  GRAFANA_ADMIN_PASSWORD
)

for key in "${required[@]}"; do
  if ! grep -Eq "^${key}=.+" "$ENV_FILE"; then
    echo "Falta valor requerido: $key" >&2
    exit 1
  fi
done

secret_key="$(grep -E '^SECRET_KEY=' "$ENV_FILE" | cut -d'=' -f2-)"
if [ "${#secret_key}" -lt 32 ]; then
  echo "SECRET_KEY debe tener al menos 32 caracteres" >&2
  exit 1
fi

channel_key="$(grep -E '^CHANNEL_ENCRYPTION_KEY=' "$ENV_FILE" | cut -d'=' -f2-)"
if [ "${#channel_key}" -lt 32 ]; then
  echo "CHANNEL_ENCRYPTION_KEY parece inválida o demasiado corta" >&2
  exit 1
fi

grafana_pass="$(grep -E '^GRAFANA_ADMIN_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2-)"
if [ "${#grafana_pass}" -lt 12 ]; then
  echo "GRAFANA_ADMIN_PASSWORD debe tener al menos 12 caracteres" >&2
  exit 1
fi

if grep -Eq '^DATABASE_URL=sqlite' "$ENV_FILE"; then
  echo "DATABASE_URL no puede usar SQLite en producción" >&2
  exit 1
fi

if ! grep -Eq '^MAX_REQUEST_BODY_BYTES=[0-9]+$' "$ENV_FILE"; then
  echo "MAX_REQUEST_BODY_BYTES debe estar definido como entero" >&2
  exit 1
fi

if ! grep -Eq '^ENVIRONMENT=production$' "$ENV_FILE"; then
  echo "ENVIRONMENT debe ser production" >&2
  exit 1
fi

if grep -Eq '^DEBUG=true$' "$ENV_FILE"; then
  echo "DEBUG debe estar en false para producción" >&2
  exit 1
fi

PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet

echo "Validación de producción OK."
echo "Levanta con:"
echo "  cd $DEPLOY_DIR"
echo "  docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup up -d --build"