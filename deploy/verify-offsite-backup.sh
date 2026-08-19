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

# El healthcheck no espera al siguiente ciclo horario del servicio de réplica:
# fuerza la copia inmediata únicamente del backup seleccionado y su sidecar.
"$rclone_bin" copy "$local_dir" "$destination" \
  --include "$backup_name" \
  --include "${backup_name}.sha256" \
  --checksum \
  --transfers 2 \
  --checkers 2 \
  --quiet

# Verifica el contenido descargándolo. `--download` evita que un backend sin
# hash común con el filesystem local degrade la comprobación a sólo tamaño.
# `--one-way` permite otros backups históricos en el destino remoto.
"$rclone_bin" check "$local_dir" "$destination" \
  --include "$backup_name" \
  --include "${backup_name}.sha256" \
  --one-way \
  --download \
  --checkers 1 \
  --quiet
