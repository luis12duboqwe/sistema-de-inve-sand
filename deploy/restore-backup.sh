#!/usr/bin/env bash
# Restore exclusivamente en una base de datos nueva y aislada. Cutover manual.
set -euo pipefail
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
BACKUP_FILE="${2:-}"
CONFIRM="${3:-}"
TARGET_DB="${4:-}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"
if [[ -z "$BACKUP_FILE" || "$CONFIRM" != "--yes" || -z "$TARGET_DB" ]]; then
  echo 'Uso: restore-backup.sh <env_file> <backup.sql.gz> --yes <nombre_bd_nueva>' >&2
  exit 2
fi
if [[ ! -f "$ENV_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo 'Faltan env o backup' >&2; exit 2
fi
if [[ ! "$TARGET_DB" =~ ^[a-z][a-z0-9_]{2,48}$ ]] ||
   [[ "$TARGET_DB" == postgres || "$TARGET_DB" == template0 || "$TARGET_DB" == template1 ]]; then
  echo 'Nombre destino inválido' >&2; exit 2
fi
ENV_FILE="$(realpath "$ENV_FILE")"
BACKUP_FILE="$(realpath "$BACKUP_FILE")"
source_db="$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"
if [[ ! "$source_db" =~ ^[a-z][a-z0-9_]*$ ]]; then
  echo 'POSTGRES_DB debe ser un nombre sin comillas, válido y explícito.' >&2
  exit 2
fi
if [[ -z "$source_db" || "$TARGET_DB" == "$source_db" ]]; then
  echo 'RECHAZADO: el destino coincide con la BD activa.' >&2
  exit 2
fi
if [[ ! -f "${BACKUP_FILE}.sha256" ]]; then
  echo 'Falta checksum obligatorio. Abortando.' >&2; exit 2
fi
expected_hash="$(awk 'NR==1 { print $1 }' "${BACKUP_FILE}.sha256")"
actual_hash="$(sha256sum "$BACKUP_FILE" | awk '{ print $1 }')"
if [[ ! "$expected_hash" =~ ^[0-9a-fA-F]{64}$ ]] || [[ "${expected_hash,,}" != "$actual_hash" ]]; then
  echo 'Checksum SHA256 inválido. Abortando.' >&2; exit 2
fi
gzip -t "$BACKUP_FILE" || { echo 'Backup gzip inválido' >&2; exit 2; }
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
# createdb falla si el destino ya existe. Jamás truncar o eliminar datos activos.
PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T db sh -c '
  set -eu
  target="$1"
  if [ "$target" = "$POSTGRES_DB" ]; then
    echo "Destino coincide con la base en servicio" >&2; exit 3
  fi
  PGPASSWORD="$POSTGRES_PASSWORD" createdb -U "$POSTGRES_USER" "$target"
' sh "$TARGET_DB"
echo "Restaurando en base aislada $TARGET_DB con transacción única..."
if ! gunzip -c "$BACKUP_FILE" | PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T db \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 --single-transaction -U "$POSTGRES_USER" -d "$1"' sh "$TARGET_DB"; then
  echo "Restauración aislada fallida. La BD de producción no se modificó." >&2
  exit 1
fi
# Comprobar presencia de cinco tablas de negocio antes de declarar recuperable.
table_count="$(PROD_ENV_FILE="$ENV_FILE" "${COMPOSE[@]}" exec -T db \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -A -t -U "$POSTGRES_USER" -d "$1" -c "$2"' \
  sh "$TARGET_DB" "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('users','orders','products','stock','schema_migrations')")"
table_count="${table_count//$'\r'/}"
if [[ ! "$table_count" =~ ^[0-9]+$ || "$table_count" -lt 5 ]]; then
  echo "Esquema incompleto ($table_count/5 tablas); no conmutar producción." >&2
  exit 1
fi
echo "Base AISLADA restaurada y comprobada: $TARGET_DB."
echo 'No se cambió la conexión de producción. Hacer pruebas y aprobar plan de cutover/rollback.'
