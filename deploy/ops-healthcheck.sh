#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"
MAX_BACKUP_AGE_HOURS="${MAX_BACKUP_AGE_HOURS:-30}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE" >&2
  exit 1
fi

echo "[1/3] Verificando estado de contenedores..."
PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo "[2/3] Verificando /api/health y /api/metrics..."
frontend_port="$(grep -E '^FRONTEND_PORT=' "$ENV_FILE" | cut -d'=' -f2)"
frontend_port="${frontend_port:-80}"
curl -fsS "http://127.0.0.1:${frontend_port}/api/health" >/tmp/inventory_health.json
curl -fsS "http://127.0.0.1:${frontend_port}/api/metrics" >/tmp/inventory_metrics.json
echo "health: $(cat /tmp/inventory_health.json)"
echo "metrics: $(cat /tmp/inventory_metrics.json)"

echo "[3/3] Verificando antigüedad de backup más reciente..."
latest_backup="$(find "$DEPLOY_DIR/backups" -maxdepth 1 -type f -name '*.sql.gz' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)"

if [ -z "$latest_backup" ]; then
  echo "Sin backups locales en $DEPLOY_DIR/backups" >&2
  exit 1
fi

latest_mtime="$(stat -c %Y "$latest_backup")"
now_epoch="$(date +%s)"
age_hours="$(( (now_epoch - latest_mtime) / 3600 ))"

echo "Último backup: $latest_backup"
echo "Antigüedad: ${age_hours}h"

if [ "$age_hours" -gt "$MAX_BACKUP_AGE_HOURS" ]; then
  echo "Backup demasiado antiguo (> ${MAX_BACKUP_AGE_HOURS}h)" >&2
  exit 1
fi

echo "Salud operativa OK."
