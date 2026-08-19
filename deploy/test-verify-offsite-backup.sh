#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/backups" "$TMP_DIR/bin"
# Intencionalmente contiene metacaracteres de filtros rclone. Debe tratarse
# como un nombre literal, nunca como patrón.
backup_name='inventory[1]*?_20260818_120000.sql.gz'
printf 'database-backup' > "$TMP_DIR/backups/$backup_name"
printf 'fake checksum  %s\n' "$backup_name" > "$TMP_DIR/backups/${backup_name}.sha256"

cat > "$TMP_DIR/bin/rclone" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
{
  printf '%s\n' '---CALL---'
  printf '%s\n' "$@"
  printf '%s\n' '---STDIN---'
  cat
} >> "$RCLONE_ARGS_FILE"
if [ "${FAKE_RCLONE_FAIL_COMMAND:-}" = "${1:-}" ]; then
  exit "${FAKE_RCLONE_EXIT:-7}"
fi
exit 0
EOF
chmod +x "$TMP_DIR/bin/rclone"

run_check() {
  : > "$TMP_DIR/rclone-args"
  BACKUP_CHECK_LOCAL_DIR="$TMP_DIR/backups" \
  BACKUP_RCLONE_DESTINATION="offsite:bucket/inventory" \
  RCLONE_BIN="$TMP_DIR/bin/rclone" \
  RCLONE_ARGS_FILE="$TMP_DIR/rclone-args" \
  sh "$DEPLOY_DIR/verify-offsite-backup.sh" "$backup_name"
}

run_check

[ "$(grep -Fxc -- '---CALL---' "$TMP_DIR/rclone-args")" -eq 2 ]
grep -Fxq 'copy' "$TMP_DIR/rclone-args"
grep -Fxq 'check' "$TMP_DIR/rclone-args"
grep -Fxq "$TMP_DIR/backups" "$TMP_DIR/rclone-args"
grep -Fxq 'offsite:bucket/inventory' "$TMP_DIR/rclone-args"
grep -Fxq -- '--files-from-raw' "$TMP_DIR/rclone-args"
grep -Fxq -- '-' "$TMP_DIR/rclone-args"
grep -Fxq "$backup_name" "$TMP_DIR/rclone-args"
grep -Fxq "${backup_name}.sha256" "$TMP_DIR/rclone-args"
grep -Fxq -- '--checksum' "$TMP_DIR/rclone-args"
grep -Fxq -- '--one-way' "$TMP_DIR/rclone-args"
grep -Fxq -- '--download' "$TMP_DIR/rclone-args"
grep -Fxq -- '--quiet' "$TMP_DIR/rclone-args"
if grep -Fxq -- '--include' "$TMP_DIR/rclone-args"; then
  echo "El verificador volvió a usar filtros de patrón para nombres exactos" >&2
  exit 1
fi

rm "$TMP_DIR/backups/${backup_name}.sha256"
if run_check >/dev/null 2>&1; then
  echo "El verificador aceptó un backup sin .sha256" >&2
  exit 1
fi
printf 'fake checksum  %s\n' "$backup_name" > "$TMP_DIR/backups/${backup_name}.sha256"

if BACKUP_CHECK_LOCAL_DIR="$TMP_DIR/backups" \
   BACKUP_RCLONE_DESTINATION="offsite:bucket/inventory" \
   RCLONE_BIN="$TMP_DIR/bin/rclone" \
   RCLONE_ARGS_FILE="$TMP_DIR/rclone-args" \
   FAKE_RCLONE_FAIL_COMMAND=copy \
   sh "$DEPLOY_DIR/verify-offsite-backup.sh" "$backup_name" >/dev/null 2>&1; then
  echo "El verificador ocultó un fallo durante la copia inmediata" >&2
  exit 1
fi

if BACKUP_CHECK_LOCAL_DIR="$TMP_DIR/backups" \
   BACKUP_RCLONE_DESTINATION="offsite:bucket/inventory" \
   RCLONE_BIN="$TMP_DIR/bin/rclone" \
   RCLONE_ARGS_FILE="$TMP_DIR/rclone-args" \
   FAKE_RCLONE_FAIL_COMMAND=check \
   sh "$DEPLOY_DIR/verify-offsite-backup.sh" "$backup_name" >/dev/null 2>&1; then
  echo "El verificador ocultó un fallo de verificación remota" >&2
  exit 1
fi

if BACKUP_CHECK_LOCAL_DIR="$TMP_DIR/backups" \
   BACKUP_RCLONE_DESTINATION="offsite:bucket/inventory" \
   RCLONE_BIN="$TMP_DIR/bin/rclone" \
   RCLONE_ARGS_FILE="$TMP_DIR/rclone-args" \
   sh "$DEPLOY_DIR/verify-offsite-backup.sh" '../escape.sql.gz' >/dev/null 2>&1; then
  echo "El verificador aceptó un nombre de archivo inseguro" >&2
  exit 1
fi

multiline_name="inventory_bad
second.sql.gz"
if BACKUP_CHECK_LOCAL_DIR="$TMP_DIR/backups" \
   BACKUP_RCLONE_DESTINATION="offsite:bucket/inventory" \
   RCLONE_BIN="$TMP_DIR/bin/rclone" \
   RCLONE_ARGS_FILE="$TMP_DIR/rclone-args" \
   sh "$DEPLOY_DIR/verify-offsite-backup.sh" "$multiline_name" >/dev/null 2>&1; then
  echo "El verificador aceptó un nombre multilínea" >&2
  exit 1
fi

echo "Off-site backup verifier tests OK"
