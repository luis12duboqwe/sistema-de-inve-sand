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
  SETUP_TOKEN
  ALLOWED_HOSTS
  CORS_ORIGINS
  GRAFANA_ADMIN_PASSWORD
  REQUIRE_OFFSITE_BACKUP
  BACKUP_OFFSITE_INTERVAL_SECONDS
)

for key in "${required[@]}"; do
  if ! grep -Eq "^${key}=.+" "$ENV_FILE"; then
    echo "Falta valor requerido: $key" >&2
    exit 1
  fi
done

validate_min_length() {
  local key="$1"
  local min_length="$2"
  local value
  value="$(grep -E "^${key}=" "$ENV_FILE" | cut -d'=' -f2-)"
  if [ "${#value}" -lt "$min_length" ]; then
    echo "$key debe tener al menos $min_length caracteres" >&2
    exit 1
  fi
}

validate_min_length SECRET_KEY 32
validate_min_length CHANNEL_ENCRYPTION_KEY 32
validate_min_length SETUP_TOKEN 32
validate_min_length GRAFANA_ADMIN_PASSWORD 12

if grep -Eq '^ENABLE_DESTRUCTIVE_PURGE=true$' "$ENV_FILE"; then
  if ! grep -Eq '^DESTRUCTIVE_OPERATION_TOKEN=.{32,}$' "$ENV_FILE"; then
    echo "DESTRUCTIVE_OPERATION_TOKEN de al menos 32 caracteres es obligatorio cuando ENABLE_DESTRUCTIVE_PURGE=true" >&2
    exit 1
  fi
fi

if grep -Eq '^DATABASE_URL=sqlite' "$ENV_FILE"; then
  echo "DATABASE_URL no puede usar SQLite en producción" >&2
  exit 1
fi

if ! grep -Eq '^MAX_REQUEST_BODY_BYTES=[0-9]+$' "$ENV_FILE"; then
  echo "MAX_REQUEST_BODY_BYTES debe estar definido como entero" >&2
  exit 1
fi

if ! grep -Eq '^MIN_BACKUP_BYTES=[0-9]+$' "$ENV_FILE"; then
  echo "MIN_BACKUP_BYTES debe estar definido como entero" >&2
  exit 1
fi

if ! grep -Eq '^BACKUP_OFFSITE_INTERVAL_SECONDS=[0-9]+$' "$ENV_FILE"; then
  echo "BACKUP_OFFSITE_INTERVAL_SECONDS debe estar definido como entero" >&2
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

if ! grep -Eq '^REQUIRE_OFFSITE_BACKUP=(true|false)$' "$ENV_FILE"; then
  echo "REQUIRE_OFFSITE_BACKUP debe ser true o false" >&2
  exit 1
fi

if grep -Eq '^REQUIRE_OFFSITE_BACKUP=true$' "$ENV_FILE"; then
  if ! grep -Eq '^BACKUP_RCLONE_DESTINATION=[^[:space:]:]+:.+' "$ENV_FILE"; then
    echo "BACKUP_RCLONE_DESTINATION debe apuntar a un remote rclone fuera del host (ej: offsite:bucket/inventory)" >&2
    exit 1
  fi
fi

PROD_ENV_FILE="$ENV_FILE" docker compose \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_FILE" \
  --profile backup \
  --profile backup-offsite \
  --profile monitoring \
  config --quiet

echo "Validación de producción OK."
echo "Levanta con:"
echo "  cd $DEPLOY_DIR"
echo "  docker compose --env-file .env.prod -f docker-compose.prod.yml --profile backup --profile backup-offsite up -d --build"
