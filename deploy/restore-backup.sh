#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
BACKUP_FILE="${2:-}"
CONFIRM_FLAG="${3:-}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"

if [ -z "$BACKUP_FILE" ]; then
  echo "Uso: ./deploy/restore-backup.sh [env_file] <backup.sql.gz> [--yes]" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE" >&2
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup no encontrado: $BACKUP_FILE" >&2
  exit 1
fi

if [ -f "${BACKUP_FILE}.sha256" ]; then
  echo "Validando checksum..."
  sha256sum -c "${BACKUP_FILE}.sha256"
else
  echo "Advertencia: no existe archivo checksum ${BACKUP_FILE}.sha256" >&2
fi

if [ "$CONFIRM_FLAG" != "--yes" ]; then
  echo "Esta operación sobrescribirá la base de datos de producción." >&2
  echo "Re-ejecuta con --yes para confirmar." >&2
  exit 1
fi

echo "Restaurando backup en PostgreSQL..."
gunzip -c "$BACKUP_FILE" | PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

echo "Verificando conexión post-restauración..."
PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT NOW();"'

echo "Restauración completada correctamente."
