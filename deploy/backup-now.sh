#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"
OUT_DIR="$DEPLOY_DIR/backups"

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE. Ejecuta: ./deploy/prepare-prod-env.sh" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
timestamp="$(date +%Y%m%d_%H%M%S)"
backup_file="$OUT_DIR/manual_${timestamp}.sql.gz"

PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  | gzip > "$backup_file"

sha256sum "$backup_file" > "$backup_file.sha256"
echo "Backup creado: $backup_file"