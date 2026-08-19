#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/backups" "$TMP_DIR/bin"
backup_name="inventory_20260818_120000.sql.gz"
printf 'database-backup' > "$TMP_DIR/backups/$backup_name"
printf 'fake checksum  %s\n' "$backup_name" > "$TMP_DIR/backups/${backup_name}.sha256"

cat > "$TMP_DIR/bin/rclone" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" > "$RCLONE_ARGS_FILE"
exit "${FAKE_RCLONE_EXIT:-0}"
EOF
chmod +x "$TMP_DIR/bin/rclone"

run_check() {
  BACKUP_CHECK_LOCAL_DIR="$TMP_DIR/backups" \
  BACKUP_RCLONE_DESTINATION="offsite:bucket/inventory" \
  RCLONE_BIN="$TMP_DIR/bin/rclone" \
  RCLONE_ARGS_FILE="$TMP_DIR/rclone-args" \
  sh "$DEPLOY_DIR/verify-offsite-backup.sh" "$backup_name"
}

run_check

grep -Fxq 'check' "$TMP_DIR/rclone-args"
grep -Fxq "$TMP_DIR/backups" "$TMP_DIR/rclone-args"
grep -Fxq 'offsite:bucket/inventory' "$TMP_DIR/rclone-args"
grep -Fxq "$backup_name" "$TMP_DIR/rclone-args"
grep -Fxq "${backup_name}.sha256" "$TMP_DIR/rclone-args"
grep -Fxq -- '--one-way' "$TMP_DIR/rclone-args"
grep -Fxq -- '--quiet' "$TMP_DIR/rclone-args"

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
   FAKE_RCLONE_EXIT=7 \
   sh "$DEPLOY_DIR/verify-offsite-backup.sh" "$backup_name" >/dev/null 2>&1; then
  echo "El verificador ocultó un fallo de rclone" >&2
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

echo "Off-site backup verifier tests OK"
