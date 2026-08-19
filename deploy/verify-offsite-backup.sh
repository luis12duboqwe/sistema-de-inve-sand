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

# --files-from-raw es un formato por líneas. Rechazamos nombres multilínea para
# que un nombre nunca pueda convertirse en varias entradas de la lista literal.
line_count="$(printf '%s\n' "$backup_name" | wc -l | tr -d '[:space:]')"
if [ "$line_count" -ne 1 ]; then
  echo "Nombre de backup inválido" >&2
  exit 2
fi

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

# `--files-from-raw -` lee nombres literales desde stdin. A diferencia de
# `--include`, caracteres como *, ?, [ o ] no se interpretan como patrones.
printf '%s\n%s\n' "$backup_name" "${backup_name}.sha256" | \
  "$rclone_bin" copy "$local_dir" "$destination" \
    --files-from-raw - \
    --checksum \
    --transfers 2 \
    --checkers 2 \
    --quiet

# Verifica el contenido descargándolo. `--download` evita que un backend sin
# hash común con el filesystem local degrade la comprobación a sólo tamaño.
# `--one-way` permite otros backups históricos en el destino remoto.
printf '%s\n%s\n' "$backup_name" "${backup_name}.sha256" | \
  "$rclone_bin" check "$local_dir" "$destination" \
    --files-from-raw - \
    --one-way \
    --download \
    --checkers 1 \
    --quiet
