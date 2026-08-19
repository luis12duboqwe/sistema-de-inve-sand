#!/bin/sh

set -eu

backup_name="${1:-}"
local_dir="${BACKUP_CHECK_LOCAL_DIR:-/backups}"
destination="${BACKUP_RCLONE_DESTINATION:-}"
rclone_bin="${RCLONE_BIN:-rclone}"

if [ -z "$backup_name" ]; then
  echo "Debe indicarse el nombre del backup a verificar" >&2
  exit 2
fi

case "$backup_name" in
  */*|*\\*|.|..)
    echo "Nombre de backup inválido" >&2
    exit 2
    ;;
esac

if [ -z "$destination" ]; then
  echo "BACKUP_RCLONE_DESTINATION es obligatorio" >&2
  exit 2
fi

backup_file="$local_dir/$backup_name"
checksum_file="${backup_file}.sha256"

if [ ! -f "$backup_file" ] || [ ! -f "$checksum_file" ]; then
  echo "Falta el backup local o su checksum" >&2
  exit 1
fi

# Compara sólo el backup solicitado y su .sha256. `rclone check` falla si el
# destino no contiene ambos archivos o si el contenido/tamaño/hash difiere.
# No imprimimos la configuración del remote ni credenciales.
"$rclone_bin" check "$local_dir" "$destination" \
  --include "$backup_name" \
  --include "${backup_name}.sha256" \
  --one-way \
  --checkers 1 \
  --quiet
