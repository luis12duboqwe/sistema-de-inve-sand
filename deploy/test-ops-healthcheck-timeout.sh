#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/bin"
cat > "$TMP_DIR/.env.prod" <<'EOF'
REQUIRE_OFFSITE_BACKUP=true
FRONTEND_PORT=8080
EOF

cat > "$TMP_DIR/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
args=" $* "

if [[ "$args" == *" ps --status running --services "* ]]; then
  printf '%s\n' db backend frontend backup backup-offsite
  exit 0
fi

if [[ "$args" == *" ps "* ]]; then
  exit 0
fi

if [[ "$args" == *" exec -T backup-offsite "* ]]; then
  # Simula una llamada remota que queda bloqueada por mucho más tiempo que el
  # presupuesto configurado del healthcheck.
  sleep 30
  exit 0
fi

if [[ "$args" == *" exec -T backup "*"ls -1t /backups/"* ]]; then
  printf '%s\n' '/backups/inventory_20260818_120000.sql.gz'
  exit 0
fi

if [[ "$args" == *" exec -T backup "*"stat -c %Y"* ]]; then
  date +%s
  exit 0
fi

if [[ "$args" == *" exec -T backup "* ]]; then
  # Las comprobaciones de sidecar/checksum locales son exitosas en este test.
  exit 0
fi

echo "docker falso recibió argumentos inesperados: $*" >&2
exit 99
EOF
chmod +x "$TMP_DIR/bin/docker"

cat > "$TMP_DIR/bin/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '{"ok":true}\n'
EOF
chmod +x "$TMP_DIR/bin/curl"

start_epoch="$(date +%s)"
set +e
output="$(
  PATH="$TMP_DIR/bin:$PATH" \
  OFFSITE_READY_TIMEOUT_SECONDS=1 \
  OFFSITE_READY_POLL_SECONDS=1 \
  BACKUP_READY_TIMEOUT_SECONDS=1 \
  BACKUP_READY_POLL_SECONDS=1 \
  bash "$DEPLOY_DIR/ops-healthcheck.sh" "$TMP_DIR/.env.prod" 2>&1
)"
status=$?
set -e
elapsed="$(( $(date +%s) - start_epoch ))"

if [ "$status" -eq 0 ]; then
  echo "El healthcheck aceptó una verificación off-site colgada" >&2
  exit 1
fi

if [ "$elapsed" -gt 5 ]; then
  echo "El deadline no acotó la llamada: ${elapsed}s" >&2
  exit 1
fi

if ! grep -Fq 'no pudo sincronizarse/verificarse off-site dentro de 1s' <<<"$output"; then
  echo "El healthcheck no reportó el agotamiento del deadline" >&2
  printf '%s\n' "$output" >&2
  exit 1
fi

echo "Off-site healthcheck timeout test OK (${elapsed}s)"
