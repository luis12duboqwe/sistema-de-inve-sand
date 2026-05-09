#!/bin/bash
#
# Script de Backup Automático para PostgreSQL
# 
# Permiso: chmod +x backup_database.sh
# 
# Crontab (backup diamos a las 2 AM):
#   0 2 * * * /path/to/backup_database.sh
#
# Crontab (backup semanales todos los domingos a las 3 AM):
#   0 3 * * 0 /path/to/backup_database.sh --weekly

set -euo pipefail

# ====================================
# CONFIGURACIÓN
# ====================================

# Cambiar según tu entorno
DB_USER="${DB_USER:-inventory_user}"
DB_NAME="${DB_NAME:-inventory_db}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-inventory_pass}"

# Directorio de backups
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Logs
LOG_FILE="${BACKUP_DIR}/backup.log"
CREATED_BACKUP_FILE=""

# ====================================
# FUNCIONES
# ====================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

create_backup() {
    local backup_type="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/${DB_NAME}_${backup_type}_${timestamp}.sql.gz"
    
    log "📦 Iniciando backup $backup_type..."
    
    # Crear directorio si no existe
    mkdir -p "$BACKUP_DIR"

    if ! command -v pg_dump >/dev/null 2>&1; then
        log "❌ ERROR: pg_dump no está instalado"
        return 1
    fi
    
    # Realizar backup
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-password \
        | gzip > "$backup_file"
    
    # Verificar tamaño
    local size=$(du -h "$backup_file" | cut -f1)
    log "✓ Backup guardado: $backup_file ($size)"
    
    # Generar checksum
    sha256sum "$backup_file" > "${backup_file}.sha256"
    log "✓ Checksum generado: ${backup_file}.sha256"
    CREATED_BACKUP_FILE="$backup_file"
}

cleanup_old_backups() {
    log "🧹 Limpiando backups antiguos (más de $BACKUP_RETENTION_DAYS días)..."
    
    find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz.sha256" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true
    
    local count=$(ls -1 "$BACKUP_DIR"/${DB_NAME}_*.sql.gz 2>/dev/null | wc -l)
    log "✓ Backups antiguos eliminados. Backups actuales: $count"
}

verify_backup() {
    local backup_file="$1"
    log "🔍 Verificando integridad del backup..."
    
    if [ -f "${backup_file}.sha256" ]; then
        if sha256sum -c "${backup_file}.sha256" >> "$LOG_FILE" 2>&1; then
            log "✓ Backup verificado correctamente"
            return 0
        else
            log "❌ ERROR: Verificación de integridad falló"
            return 1
        fi
    else
        log "⚠️  No hay checksum para verificar"
        return 0
    fi
}

send_notification() {
    local status="$1"
    local message="$2"
    
    # Si tienes webhook o email, agregar aquí
    # Ejemplo: curl -X POST https://hooks.slack.com/... -d "..."
    
    log "📧 Notificación: $status - $message"
}

# ====================================
# MAIN
# ====================================

main() {
    # Crear directorio y log antes de escribir cualquier log
    mkdir -p "$BACKUP_DIR"
    touch "$LOG_FILE"

    log "================================"
    log "Iniciando backup de BD"
    log "================================"
    
    # Determinar tipo de backup
    local backup_type="daily"
    if [[ "${1:-}" == "--weekly" ]]; then
        backup_type="weekly"
    fi
    
    # Ejecutar backup
    if create_backup "$backup_type"; then
        # Limpiar backups antiguos
        cleanup_old_backups
        
        # Verificar último backup
        verify_backup "$CREATED_BACKUP_FILE"
        
        # Logs de resumen
        log "✅ BACKUP COMPLETADO EXITOSAMENTE"
        send_notification "SUCCESS" "Backup de $DB_NAME completado"
    else
        log "❌ BACKUP FALLÓ"
        send_notification "ERROR" "Backup de $DB_NAME falló"
        exit 1
    fi
    
    log "================================\n"
}

main "$@"
