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
)

for key in "${required[@]}"; do
  if ! grep -Eq "^${key}=.+" "$ENV_FILE"; then
    echo "Falta valor requerido: $key" >&2
    exit 1
  fi
done

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