#!/bin/bash
#
# Restore seguro para backups creados por backup_database.sh.
# Uso:
#   DB_USER=inventory_user DB_NAME=inventory_db DB_PASSWORD=... ./restore_database.sh /ruta/backup.sql.gz
#
# Por seguridad exige confirmacion explicita con RESTORE_CONFIRM=YES.

set -euo pipefail

DB_USER="${DB_USER:-inventory_user}"
DB_NAME="${DB_NAME:-inventory_db}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-inventory_pass}"
RESTORE_CONFIRM="${RESTORE_CONFIRM:-}"
BACKUP_FILE="${1:-}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

fail() {
    log "ERROR: $1"
    exit 1
}

if [[ -z "$BACKUP_FILE" ]]; then
    fail "Debe indicar el archivo .sql o .sql.gz a restaurar"
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    fail "No existe el archivo: $BACKUP_FILE"
fi

if [[ "$RESTORE_CONFIRM" != "YES" ]]; then
    fail "Restore bloqueado. Ejecute con RESTORE_CONFIRM=YES para confirmar que desea sobrescribir datos."
fi

if ! command -v psql >/dev/null 2>&1; then
    fail "psql no esta instalado"
fi

if [[ "$BACKUP_FILE" == *.gz ]]; then
    if ! command -v gunzip >/dev/null 2>&1; then
        fail "gunzip no esta instalado"
    fi
fi

if [[ -f "${BACKUP_FILE}.sha256" ]]; then
    log "Verificando checksum..."
    sha256sum -c "${BACKUP_FILE}.sha256"
fi

log "Probando conexion a PostgreSQL..."
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-password \
    -c "SELECT 1" >/dev/null

log "Restaurando backup en $DB_NAME..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-password \
        --set ON_ERROR_STOP=on
else
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-password \
        --set ON_ERROR_STOP=on \
        -f "$BACKUP_FILE"
fi

log "Restore completado. Verificando tablas principales..."
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-password \
    -c "SELECT COUNT(*) AS orders_count FROM orders;" \
    -c "SELECT COUNT(*) AS products_count FROM products;"

log "Restore finalizado correctamente."
