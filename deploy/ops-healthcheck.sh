#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"
MAX_BACKUP_AGE_HOURS="${MAX_BACKUP_AGE_HOURS:-30}"

read_env_value() {
  local key="$1"
  local value
  value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d'=' -f2- || true)"
  value="${value%$'\r'}"
  value="${value#\"}"
  value="${value%\"}"
  value="${value#\'}"
  value="${value%\'}"
  printf '%s' "$value"
}

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE" >&2
  exit 1
fi

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
REQUIRE_OFFSITE_BACKUP="$(read_env_value REQUIRE_OFFSITE_BACKUP)"
REQUIRE_OFFSITE_BACKUP="${REQUIRE_OFFSITE_BACKUP,,}"

echo "[1/4] Verificando estado de servicios críticos..."
PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" ps
running_services="$(PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" ps --status running --services)"

for service in db backend frontend backup; do
  if ! grep -Fxq "$service" <<<"$running_services"; then
    echo "Servicio crítico no está running: $service" >&2
    exit 1
  fi
done

if [ "$REQUIRE_OFFSITE_BACKUP" = "true" ] && ! grep -Fxq "backup-offsite" <<<"$running_services"; then
  echo "REQUIRE_OFFSITE_BACKUP=true pero backup-offsite no está running" >&2
  exit 1
fi

echo "[2/4] Verificando /api/health, /api/ready y /api/metrics..."
frontend_port="$(read_env_value FRONTEND_PORT)"
frontend_port="${frontend_port:-80}"
curl -fsS "http://127.0.0.1:${frontend_port}/api/health" >/tmp/inventory_health.json
curl -fsS "http://127.0.0.1:${frontend_port}/api/ready" >/tmp/inventory_ready.json
curl -fsS "http://127.0.0.1:${frontend_port}/api/metrics" >/tmp/inventory_metrics.json
echo "health: $(cat /tmp/inventory_health.json)"
echo "ready: $(cat /tmp/inventory_ready.json)"
echo "metrics: $(cat /tmp/inventory_metrics.json)"

echo "[3/4] Verificando backup automático más reciente en el volumen Docker..."
latest_backup="$(
  PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T backup sh -c \
    'ls -1t /backups/*.sql.gz 2>/dev/null | head -n1 || true'
)"
latest_backup="${latest_backup%$'\r'}"

if [ -z "$latest_backup" ]; then
  echo "El volumen backend_backups no contiene backups automáticos" >&2
  exit 1
fi

if ! PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T backup sh -c \
  'test -f "$1.sha256" && sha256sum -c "$1.sha256"' sh "$latest_backup"; then
  echo "Checksum inválido o ausente para $latest_backup" >&2
  exit 1
fi

latest_mtime="$(
  PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T backup sh -c \
    'stat -c %Y "$1"' sh "$latest_backup"
)"
latest_mtime="${latest_mtime%$'\r'}"
now_epoch="$(date +%s)"
age_hours="$(( (now_epoch - latest_mtime) / 3600 ))"

echo "Último backup automático: $latest_backup"
echo "Antigüedad: ${age_hours}h"

if [ "$age_hours" -gt "$MAX_BACKUP_AGE_HOURS" ]; then
  echo "Backup demasiado antiguo (> ${MAX_BACKUP_AGE_HOURS}h)" >&2
  exit 1
fi

echo "[4/4] Verificando política off-site..."
if [ "$REQUIRE_OFFSITE_BACKUP" = "true" ]; then
  echo "backup-offsite está running. La existencia remota debe confirmarse en el destino configurado durante el cierre del Issue #38."
else
  echo "REQUIRE_OFFSITE_BACKUP no está activo."
fi

echo "Salud operativa OK."
