#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_TMP="$(mktemp -d)"
trap 'rm -rf "$ROOT_TMP"' EXIT

make_fixture() {
  local name="$1"
  local dir="$ROOT_TMP/$name"
  mkdir -p "$dir/bin" "$dir/reports"

  cat > "$dir/.env.prod" <<'EOF'
POSTGRES_DB=inventory_test
POSTGRES_USER=dr_user
POSTGRES_PASSWORD=pa'ss word
MIN_BACKUP_BYTES=1
EOF

  printf '%s\n' \
    'CREATE TABLE products (id integer);' \
    'CREATE TABLE stock (id integer);' \
    'CREATE TABLE orders (id integer);' \
    'CREATE TABLE stock_transfers (id integer);' \
    'CREATE TABLE returns (id integer);' \
    'CREATE TABLE product_imeis (id integer);' \
    'CREATE TABLE users (id integer);' \
    'CREATE TABLE schema_migrations (id text);' | gzip -c > "$dir/backup.sql.gz"

  # El nombre grabado en el sidecar puede pertenecer al host/contenedor original.
  hash="$(sha256sum "$dir/backup.sql.gz" | awk '{print $1}')"
  printf '%s  /backups/original-production-name.sql.gz\n' "$hash" > "$dir/backup.sql.gz.sha256"

  cat > "$dir/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

capture_file="${FAKE_DR_CAPTURE_FILE:?}"
printf '%s\n' '---CALL---' >> "$capture_file"
for arg in "$@"; do
  printf 'ARG=%s\n' "$arg" >> "$capture_file"
  case "$arg" in
    PGPASSWORD=*) printf '%s\n' "$arg" >> "${FAKE_DR_PASSWORD_FILE:?}" ;;
  esac
done

command_name="${1:-}"
if [ "$command_name" = "run" ]; then
  printf '%s\n' fake-container-id
  exit 0
fi
if [ "$command_name" = "rm" ]; then
  exit 0
fi
if [ "$command_name" != "exec" ]; then
  echo "docker falso recibió comando inesperado: $command_name" >&2
  exit 97
fi

joined=" $* "
if [[ "$joined" == *" pg_isready "* ]]; then
  if [ "${FAKE_DR_NEVER_READY:-0}" = "1" ]; then
    exit 1
  fi
  exit 0
fi

if [[ "$joined" != *" psql "* ]]; then
  echo "docker exec falso no recibió psql/pg_isready" >&2
  exit 96
fi

sql=""
args=("$@")
for ((i=0; i<${#args[@]}; i++)); do
  if [ "${args[$i]}" = "-c" ] && [ $((i + 1)) -lt ${#args[@]} ]; then
    sql="${args[$((i + 1))]}"
    break
  fi
done

if [ -z "$sql" ]; then
  cat >/dev/null
  if [ "${FAKE_DR_RESTORE_FAIL:-0}" = "1" ]; then
    exit 42
  fi
  exit 0
fi

if [ -n "${FAKE_DR_QUERY_FAIL_TABLE:-}" ] && [[ "$sql" == *"\"${FAKE_DR_QUERY_FAIL_TABLE}\""* ]]; then
  exit 43
fi

# Todas las tablas críticas, incluida schema_migrations, tienen al menos una fila.
printf '%s\n' 1
EOF
  chmod +x "$dir/bin/docker"
  printf '%s\n' "$dir"
}

run_dr() {
  local dir="$1"
  shift
  : > "$dir/docker-calls"
  : > "$dir/password-args"
  env \
    PATH="$dir/bin:$PATH" \
    FAKE_DR_CAPTURE_FILE="$dir/docker-calls" \
    FAKE_DR_PASSWORD_FILE="$dir/password-args" \
    DR_REPORT_DIR="$dir/reports" \
    DR_MAX_RPO_HOURS=30 \
    DR_READY_ATTEMPTS=1 \
    DR_READY_POLL_SECONDS=0 \
    "$@" \
    bash "$DEPLOY_DIR/dr-drill.sh" "$dir/.env.prod" "$dir/backup.sql.gz"
}

# 1. Camino exitoso: reporte JSON válido, tablas críticas y password como un solo argumento.
success_dir="$(make_fixture success)"
success_output="$(run_dr "$success_dir" 2>&1)"
report_file="$(find "$success_dir/reports" -maxdepth 1 -name 'dr_report_*.json' -print -quit)"
[ -n "$report_file" ] || { echo "No se generó reporte DR" >&2; exit 1; }

python - "$report_file" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["success"] is True
assert payload["backup_file"] == "backup.sql.gz"
assert len(payload["backup_sha256"]) == 64
for table in (
    "products", "stock", "orders", "stock_transfers", "returns",
    "product_imeis", "users", "schema_migrations",
):
    assert payload["restored_counts"][table] == 1
PY

if ! grep -Fxq "PGPASSWORD=pa'ss word" "$success_dir/password-args"; then
  echo "La contraseña no llegó a psql como un único argumento de entorno" >&2
  exit 1
fi
if grep -Fq "pa'ss word" <<<"$success_output"; then
  echo "La contraseña apareció en la salida del DR" >&2
  exit 1
fi

# 2. El sidecar SHA-256 es obligatorio y debe validarse antes de iniciar Docker.
missing_checksum_dir="$(make_fixture missing-checksum)"
rm "$missing_checksum_dir/backup.sql.gz.sha256"
set +e
missing_output="$(run_dr "$missing_checksum_dir" 2>&1)"
missing_status=$?
set -e
[ "$missing_status" -ne 0 ] || { echo "DR aceptó backup sin checksum" >&2; exit 1; }
grep -Fq 'Falta checksum obligatorio' <<<"$missing_output"
[ ! -s "$missing_checksum_dir/docker-calls" ] || { echo "DR tocó Docker antes de validar checksum" >&2; exit 1; }

# 3. Un checksum incorrecto debe abortar antes de iniciar Docker.
bad_hash_dir="$(make_fixture bad-hash)"
printf '%064d  /backups/backup.sql.gz\n' 0 > "$bad_hash_dir/backup.sql.gz.sha256"
set +e
bad_hash_output="$(run_dr "$bad_hash_dir" 2>&1)"
bad_hash_status=$?
set -e
[ "$bad_hash_status" -ne 0 ] || { echo "DR aceptó checksum incorrecto" >&2; exit 1; }
grep -Fq 'Checksum SHA-256 no coincide' <<<"$bad_hash_output"
[ ! -s "$bad_hash_dir/docker-calls" ] || { echo "DR inició Docker con checksum inválido" >&2; exit 1; }

# 4. PostgreSQL que nunca queda listo debe fallar explícitamente.
not_ready_dir="$(make_fixture not-ready)"
set +e
not_ready_output="$(run_dr "$not_ready_dir" FAKE_DR_NEVER_READY=1 2>&1)"
not_ready_status=$?
set -e
[ "$not_ready_status" -ne 0 ] || { echo "DR aceptó PostgreSQL no disponible" >&2; exit 1; }
grep -Fq 'PostgreSQL temporal no estuvo listo' <<<"$not_ready_output"

# 5. Fallos durante psql restore deben propagarse.
restore_fail_dir="$(make_fixture restore-fail)"
set +e
restore_output="$(run_dr "$restore_fail_dir" FAKE_DR_RESTORE_FAIL=1 2>&1)"
restore_status=$?
set -e
[ "$restore_status" -ne 0 ] || { echo "DR ocultó un fallo de restauración" >&2; exit 1; }
grep -Fq 'La restauración PostgreSQL falló' <<<"$restore_output"

# 6. Fallos de consulta no pueden convertirse silenciosamente en conteo cero.
query_fail_dir="$(make_fixture query-fail)"
set +e
query_output="$(run_dr "$query_fail_dir" FAKE_DR_QUERY_FAIL_TABLE=returns 2>&1)"
query_status=$?
set -e
[ "$query_status" -ne 0 ] || { echo "DR ocultó un fallo consultando tabla crítica" >&2; exit 1; }
grep -Fq 'No se pudo verificar la tabla restaurada: returns' <<<"$query_output"

printf '%s\n' 'DR drill hardening tests OK'
