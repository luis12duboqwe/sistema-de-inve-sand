#!/bin/sh

set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
MIN_BACKUP_BYTES="${MIN_BACKUP_BYTES:-1024}"

mkdir -p "$BACKUP_DIR"

while true; do
  timestamp="$(date +%Y%m%d_%H%M%S)"
  base_name="${POSTGRES_DB}_${timestamp}"
  sql_tmp="$BACKUP_DIR/.${base_name}.sql.tmp"
  gzip_tmp="$BACKUP_DIR/.${base_name}.sql.gz.tmp"
  final_file="$BACKUP_DIR/${base_name}.sql.gz"

  echo "[$(date -Iseconds)] creando backup verificado $final_file"
  rm -f "$sql_tmp" "$gzip_tmp"

  if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
      --host=db \
      --username="$POSTGRES_USER" \
      --dbname="$POSTGRES_DB" \
      --no-owner \
      --no-privileges \
      --file="$sql_tmp"; then
    if [ ! -s "$sql_tmp" ]; then
      echo "Backup rechazado: pg_dump produjo un archivo vacío" >&2
      rm -f "$sql_tmp"
    else
      gzip -c "$sql_tmp" > "$gzip_tmp"
      rm -f "$sql_tmp"

      backup_size="$(wc -c < "$gzip_tmp" | tr -d ' ')"
      if gzip -t "$gzip_tmp" && [ "$backup_size" -ge "$MIN_BACKUP_BYTES" ]; then
        mv "$gzip_tmp" "$final_file"
        sha256sum "$final_file" > "${final_file}.sha256"
        echo "[$(date -Iseconds)] backup confirmado (${backup_size} bytes)"
      else
        echo "Backup rechazado: gzip inválido o tamaño insuficiente" >&2
        rm -f "$gzip_tmp"
      fi
    fi
  else
    echo "pg_dump falló; no se publicará un backup incompleto" >&2
    rm -f "$sql_tmp" "$gzip_tmp"
  fi

  find "$BACKUP_DIR" -name "*.sql.gz" -mtime "+$RETENTION_DAYS" -delete
  find "$BACKUP_DIR" -name "*.sql.gz.sha256" -mtime "+$RETENTION_DAYS" -delete
  sleep "$INTERVAL"
done
