#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"
MAX_BACKUP_AGE_HOURS="${MAX_BACKUP_AGE_HOURS:-30}"
BACKUP_READY_TIMEOUT_SECONDS="${BACKUP_READY_TIMEOUT_SECONDS:-600}"
BACKUP_READY_POLL_SECONDS="${BACKUP_READY_POLL_SECONDS:-5}"
OFFSITE_READY_TIMEOUT_SECONDS="${OFFSITE_READY_TIMEOUT_SECONDS:-600}"
OFFSITE_READY_POLL_SECONDS="${OFFSITE_READY_POLL_SECONDS:-5}"

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

if ! [[ "$BACKUP_READY_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || \
   ! [[ "$BACKUP_READY_POLL_SECONDS" =~ ^[1-9][0-9]*$ ]] || \
   ! [[ "$OFFSITE_READY_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || \
   ! [[ "$OFFSITE_READY_POLL_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "BACKUP_READY_TIMEOUT_SECONDS debe ser >= 0; OFFSITE_READY_TIMEOUT_SECONDS y los intervalos de polling deben ser > 0" >&2
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

echo "[3/4] Esperando un backup automático completo y verificable en el volumen Docker..."
latest_backup=""
waited_seconds=0

while true; do
  latest_backup="$(
    PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T backup sh -c \
      'ls -1t /backups/*.sql.gz 2>/dev/null | head -n1 || true'
  )"
  latest_backup="${latest_backup%$'\r'}"

  if [ -n "$latest_backup" ] && \
     PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T backup sh -c \
       'test -f "$1.sha256" && sha256sum -c "$1.sha256" >/dev/null' sh "$latest_backup"; then
    break
  fi

  if [ "$waited_seconds" -ge "$BACKUP_READY_TIMEOUT_SECONDS" ]; then
    echo "No apareció un backup completo con checksum válido dentro del tiempo permitido (${BACKUP_READY_TIMEOUT_SECONDS}s)" >&2
    exit 1
  fi

  sleep "$BACKUP_READY_POLL_SECONDS"
  waited_seconds="$((waited_seconds + BACKUP_READY_POLL_SECONDS))"
done

PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T backup sh -c \
  'sha256sum -c "$1.sha256"' sh "$latest_backup"

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
  if ! command -v timeout >/dev/null 2>&1; then
    echo "Falta el comando 'timeout'; no se puede acotar de forma segura la verificación off-site" >&2
    exit 1
  fi

  backup_name="${latest_backup##*/}"
  offsite_deadline="$(( $(date +%s) + OFFSITE_READY_TIMEOUT_SECONDS ))"

  while true; do
    now_epoch="$(date +%s)"
    remaining_seconds="$((offsite_deadline - now_epoch))"
    if [ "$remaining_seconds" -le 0 ]; then
      echo "El backup local existe, pero no pudo sincronizarse/verificarse off-site dentro de ${OFFSITE_READY_TIMEOUT_SECONDS}s" >&2
      exit 1
    fi

    # El deadline envuelve la llamada real. Si rclone/docker se queda colgado,
    # `timeout` termina el intento al agotar el tiempo restante del presupuesto.
    if PROD_ENV_FILE="$ENV_FILE" timeout --foreground "${remaining_seconds}s" \
       "${COMPOSE[@]}" exec -T backup-offsite \
       sh /usr/local/bin/verify-offsite-backup.sh "$backup_name" >/dev/null 2>&1; then
      echo "Backup off-site verificado: $backup_name y su checksum coinciden con la copia local."
      break
    fi

    now_epoch="$(date +%s)"
    remaining_seconds="$((offsite_deadline - now_epoch))"
    if [ "$remaining_seconds" -le 0 ]; then
      echo "El backup local existe, pero no pudo sincronizarse/verificarse off-site dentro de ${OFFSITE_READY_TIMEOUT_SECONDS}s" >&2
      exit 1
    fi

    sleep_seconds="$OFFSITE_READY_POLL_SECONDS"
    if [ "$sleep_seconds" -gt "$remaining_seconds" ]; then
      sleep_seconds="$remaining_seconds"
    fi
    if [ "$sleep_seconds" -gt 0 ]; then
      sleep "$sleep_seconds"
    fi
  done
else
  echo "REQUIRE_OFFSITE_BACKUP no está activo."
fi

echo "Salud operativa OK."
