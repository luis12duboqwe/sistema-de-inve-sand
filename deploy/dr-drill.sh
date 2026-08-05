#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
BACKUP_FILE="${2:-}"
REPORT_DIR="$DEPLOY_DIR/backups"

if [ -z "$BACKUP_FILE" ]; then
  echo "Uso: ./deploy/dr-drill.sh [env_file] <backup.sql.gz>" >&2
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

mkdir -p "$REPORT_DIR"

backup_epoch="$(stat -c %Y "$BACKUP_FILE")"
now_epoch="$(date +%s)"
rpo_seconds="$((now_epoch - backup_epoch))"

if [ -f "${BACKUP_FILE}.sha256" ]; then
  echo "Validando checksum del backup..."
  sha256sum -c "${BACKUP_FILE}.sha256"
fi

container_name="inventory-drill-$(date +%s)-$RANDOM"
report_file="$REPORT_DIR/dr_report_$(date +%Y%m%d_%H%M%S).json"

POSTGRES_DB="$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | cut -d'=' -f2-)"
POSTGRES_USER="$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | cut -d'=' -f2-)"
POSTGRES_PASSWORD="$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2-)"

if [ -z "$POSTGRES_DB" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ]; then
  echo "POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD son obligatorios en $ENV_FILE" >&2
  exit 1
fi

cleanup() {
  docker rm -f "$container_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Levantando PostgreSQL temporal para simulacro DR..."
docker run -d --name "$container_name" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  postgres:16-alpine >/dev/null

echo "Esperando disponibilidad de PostgreSQL temporal..."
for _ in $(seq 1 40); do
  if docker exec "$container_name" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

restore_started="$(date +%s)"
gunzip -c "$BACKUP_FILE" | docker exec -i "$container_name" sh -c \
  "PGPASSWORD='$POSTGRES_PASSWORD' psql -v ON_ERROR_STOP=1 -U '$POSTGRES_USER' -d '$POSTGRES_DB'" >/dev/null
restore_finished="$(date +%s)"

rto_seconds="$((restore_finished - restore_started))"

orders_count="$(docker exec "$container_name" sh -c "PGPASSWORD='$POSTGRES_PASSWORD' psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -t -A -c 'SELECT COUNT(*) FROM orders;'" 2>/dev/null || echo 0)"
transfers_count="$(docker exec "$container_name" sh -c "PGPASSWORD='$POSTGRES_PASSWORD' psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -t -A -c 'SELECT COUNT(*) FROM stock_transfers;'" 2>/dev/null || echo 0)"
returns_count="$(docker exec "$container_name" sh -c "PGPASSWORD='$POSTGRES_PASSWORD' psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -t -A -c 'SELECT COUNT(*) FROM returns;'" 2>/dev/null || echo 0)"
imeis_count="$(docker exec "$container_name" sh -c "PGPASSWORD='$POSTGRES_PASSWORD' psql -U '$POSTGRES_USER' -d '$POSTGRES_DB' -t -A -c 'SELECT COUNT(*) FROM product_imeis;'" 2>/dev/null || echo 0)"

cat > "$report_file" <<JSON
{
  "timestamp": "$(date -Iseconds)",
  "backup_file": "${BACKUP_FILE}",
  "rto_seconds": ${rto_seconds},
  "rpo_seconds": ${rpo_seconds},
  "restored_counts": {
    "orders": ${orders_count:-0},
    "stock_transfers": ${transfers_count:-0},
    "returns": ${returns_count:-0},
    "product_imeis": ${imeis_count:-0}
  }
}
JSON

echo "Simulacro DR completado."
echo "RTO: ${rto_seconds}s"
echo "RPO: ${rpo_seconds}s"
echo "Reporte: $report_file"
