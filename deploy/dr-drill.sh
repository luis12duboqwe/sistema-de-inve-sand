#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
BACKUP_FILE="${2:-}"
REPORT_DIR="${DR_REPORT_DIR:-$DEPLOY_DIR/backups}"
DR_MAX_RPO_HOURS="${DR_MAX_RPO_HOURS:-30}"
DR_READY_ATTEMPTS="${DR_READY_ATTEMPTS:-40}"
DR_READY_POLL_SECONDS="${DR_READY_POLL_SECONDS:-1}"

fail() {
  echo "DR ERROR: $*" >&2
  exit 1
}

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

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '%s' "$value"
}

if [ -z "$BACKUP_FILE" ]; then
  fail "Uso: ./deploy/dr-drill.sh [env_file] <backup.sql.gz>"
fi

[ -f "$ENV_FILE" ] || fail "Falta $ENV_FILE"
[ -f "$BACKUP_FILE" ] || fail "Backup no encontrado: $BACKUP_FILE"
[ -f "${BACKUP_FILE}.sha256" ] || fail "Falta checksum obligatorio: ${BACKUP_FILE}.sha256"

case "$BACKUP_FILE" in
  *.sql.gz) ;;
  *) fail "El backup debe terminar en .sql.gz" ;;
esac

if ! [[ "$DR_MAX_RPO_HOURS" =~ ^[0-9]+$ ]] || \
   ! [[ "$DR_READY_ATTEMPTS" =~ ^[1-9][0-9]*$ ]] || \
   ! [[ "$DR_READY_POLL_SECONDS" =~ ^[0-9]+$ ]]; then
  fail "DR_MAX_RPO_HOURS debe ser >= 0, DR_READY_ATTEMPTS > 0 y DR_READY_POLL_SECONDS >= 0"
fi

POSTGRES_DB="$(read_env_value POSTGRES_DB)"
POSTGRES_USER="$(read_env_value POSTGRES_USER)"
POSTGRES_PASSWORD="$(read_env_value POSTGRES_PASSWORD)"
MIN_BACKUP_BYTES="$(read_env_value MIN_BACKUP_BYTES)"
MIN_BACKUP_BYTES="${MIN_BACKUP_BYTES:-1}"

[ -n "$POSTGRES_DB" ] || fail "POSTGRES_DB es obligatorio en $ENV_FILE"
[ -n "$POSTGRES_USER" ] || fail "POSTGRES_USER es obligatorio en $ENV_FILE"
[ -n "$POSTGRES_PASSWORD" ] || fail "POSTGRES_PASSWORD es obligatorio en $ENV_FILE"
[[ "$MIN_BACKUP_BYTES" =~ ^[0-9]+$ ]] || fail "MIN_BACKUP_BYTES debe ser entero"

mkdir -p "$REPORT_DIR"

backup_bytes="$(stat -c %s "$BACKUP_FILE")"
if [ "$backup_bytes" -lt "$MIN_BACKUP_BYTES" ]; then
  fail "Backup demasiado pequeño: ${backup_bytes} bytes (< ${MIN_BACKUP_BYTES})"
fi

# El sidecar generado dentro del contenedor puede contener una ruta como
# /backups/foo.sql.gz. Para un restore en otro host comparamos el hash, no esa ruta.
expected_hash="$(awk 'NR == 1 {print $1; exit}' "${BACKUP_FILE}.sha256")"
if ! [[ "$expected_hash" =~ ^[0-9A-Fa-f]{64}$ ]]; then
  fail "Checksum SHA-256 inválido en ${BACKUP_FILE}.sha256"
fi
actual_hash="$(sha256sum "$BACKUP_FILE" | awk '{print $1}')"
if [ "${actual_hash,,}" != "${expected_hash,,}" ]; then
  fail "Checksum SHA-256 no coincide con el backup"
fi

echo "Checksum SHA-256 válido. Verificando integridad gzip..."
gzip -t "$BACKUP_FILE" || fail "El archivo gzip está corrupto"

backup_epoch="$(stat -c %Y "$BACKUP_FILE")"
now_epoch="$(date +%s)"
if [ "$backup_epoch" -gt "$((now_epoch + 300))" ]; then
  fail "El backup tiene una fecha futura incompatible con el reloj del host"
fi
if [ "$backup_epoch" -gt "$now_epoch" ]; then
  rpo_seconds=0
else
  rpo_seconds="$((now_epoch - backup_epoch))"
fi
max_rpo_seconds="$((DR_MAX_RPO_HOURS * 3600))"
if [ "$rpo_seconds" -gt "$max_rpo_seconds" ]; then
  fail "RPO excedido: backup de ${rpo_seconds}s (> ${max_rpo_seconds}s)"
fi

container_name="inventory-drill-$(date +%s)-$RANDOM"
report_file="$REPORT_DIR/dr_report_$(date -u +%Y%m%d_%H%M%S).json"
container_started=false

cleanup() {
  if [ "$container_started" = "true" ]; then
    docker rm -f "$container_name" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "Levantando PostgreSQL temporal para simulacro DR..."
docker run -d --name "$container_name" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  postgres:16-alpine >/dev/null
container_started=true

echo "Esperando disponibilidad de PostgreSQL temporal..."
postgres_ready=false
for ((attempt = 1; attempt <= DR_READY_ATTEMPTS; attempt++)); do
  if docker exec "$container_name" pg_isready \
      -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    postgres_ready=true
    break
  fi
  if [ "$attempt" -lt "$DR_READY_ATTEMPTS" ] && [ "$DR_READY_POLL_SECONDS" -gt 0 ]; then
    sleep "$DR_READY_POLL_SECONDS"
  fi
done

if [ "$postgres_ready" != "true" ]; then
  fail "PostgreSQL temporal no estuvo listo después de ${DR_READY_ATTEMPTS} intentos"
fi

restore_started="$(date +%s)"
echo "Restaurando backup con ON_ERROR_STOP..."
if ! gunzip -c "$BACKUP_FILE" | docker exec -i \
    -e PGPASSWORD="$POSTGRES_PASSWORD" \
    "$container_name" \
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null; then
  fail "La restauración PostgreSQL falló"
fi
restore_finished="$(date +%s)"
rto_seconds="$((restore_finished - restore_started))"

query_count() {
  local table="$1"
  local value
  if ! value="$(
    docker exec \
      -e PGPASSWORD="$POSTGRES_PASSWORD" \
      "$container_name" \
      psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
      -t -A -c "SELECT COUNT(*) FROM \"${table}\";"
  )"; then
    fail "No se pudo verificar la tabla restaurada: $table"
  fi
  value="${value%$'\r'}"
  if ! [[ "$value" =~ ^[0-9]+$ ]]; then
    fail "Conteo inválido para $table: $value"
  fi
  printf '%s' "$value"
}

critical_tables=(
  products
  stock
  orders
  stock_transfers
  returns
  product_imeis
  users
  schema_migrations
)
declare -A restored_counts=()
for table in "${critical_tables[@]}"; do
  restored_counts["$table"]="$(query_count "$table")"
done

# Una consulta adicional comprueba que las migraciones versionadas no sólo
# existan como tabla, sino que tengan al menos una entrada registrada.
if [ "${restored_counts[schema_migrations]}" -lt 1 ]; then
  fail "schema_migrations está vacío; el backup no representa una instalación migrada"
fi

backup_basename="$(basename "$BACKUP_FILE")"
backup_basename_json="$(json_escape "$backup_basename")"
timestamp="$(date -Iseconds)"
tmp_report="${report_file}.tmp"

cat > "$tmp_report" <<JSON
{
  "success": true,
  "timestamp": "${timestamp}",
  "backup_file": "${backup_basename_json}",
  "backup_sha256": "${actual_hash}",
  "backup_bytes": ${backup_bytes},
  "rto_seconds": ${rto_seconds},
  "rpo_seconds": ${rpo_seconds},
  "restored_counts": {
    "products": ${restored_counts[products]},
    "stock": ${restored_counts[stock]},
    "orders": ${restored_counts[orders]},
    "stock_transfers": ${restored_counts[stock_transfers]},
    "returns": ${restored_counts[returns]},
    "product_imeis": ${restored_counts[product_imeis]},
    "users": ${restored_counts[users]},
    "schema_migrations": ${restored_counts[schema_migrations]}
  }
}
JSON
chmod 600 "$tmp_report"
mv "$tmp_report" "$report_file"

echo "Simulacro DR completado y verificado."
echo "RTO: ${rto_seconds}s"
echo "RPO: ${rpo_seconds}s"
echo "Reporte: $report_file"
