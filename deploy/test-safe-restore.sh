#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
cat > "$TMP/.env.prod" <<'EOF'
POSTGRES_DB=inventory_live
POSTGRES_USER=test_admin
POSTGRES_PASSWORD=synthetic
EOF
printf 'CREATE TABLE users(id INTEGER);\n' | gzip -c > "$TMP/restore.sql.gz"
sha256sum "$TMP/restore.sql.gz" > "$TMP/restore.sql.gz.sha256"
cat > "$TMP/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${RESTORE_CAPTURE:?}"
if [[ " $* " == *" createdb "* ]]; then
  [[ " $* " == *"isolated_restore_1"* ]] || exit 31
  exit 0
fi
if [[ " $* " == *" --single-transaction "* ]]; then
  cat >/dev/null
  exit 0
fi
if [[ " $* " == *" psql "* ]]; then
  printf '5\n'
  exit 0
fi
exit 32
EOF
chmod +x "$TMP/bin/docker"
export RESTORE_CAPTURE="$TMP/calls"
export PATH="$TMP/bin:$PATH"
# No se permite el nombre real; no debe invocar Docker.
if bash "$ROOT/deploy/restore-backup.sh" "$TMP/.env.prod" "$TMP/restore.sql.gz" --yes inventory_live > /dev/null 2>&1; then
  echo 'Accepted live production target' >&2; exit 1
fi
[ ! -e "$RESTORE_CAPTURE" ]
mv "$TMP/restore.sql.gz.sha256" "$TMP/hash.saved"
if bash "$ROOT/deploy/restore-backup.sh" "$TMP/.env.prod" "$TMP/restore.sql.gz" --yes isolated_restore_1 >/dev/null 2>&1; then
  echo 'Accepted file without checksum' >&2; exit 1
fi
[ ! -e "$RESTORE_CAPTURE" ]
mv "$TMP/hash.saved" "$TMP/restore.sql.gz.sha256"
bash "$ROOT/deploy/restore-backup.sh" "$TMP/.env.prod" "$TMP/restore.sql.gz" --yes isolated_restore_1 >/dev/null
grep -Fq 'createdb -U' "$RESTORE_CAPTURE"
grep -Fq -- '--single-transaction' "$RESTORE_CAPTURE"
if grep -Eq '(dropdb|TRUNCATE|DROP DATABASE)' "$RESTORE_CAPTURE"; then
  echo 'Unexpected destructive SQL' >&2; exit 1
fi
echo 'Safe isolated restore tests OK'
