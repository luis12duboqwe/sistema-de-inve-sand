#!/usr/bin/env bash

set -euo pipefail

VPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/vps/install-vps.sh
source "$VPS_DIR/install-vps.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

APP_DIR="$TMP_DIR/app"
mkdir -p "$APP_DIR/backend"
CALL_LOG="$TMP_DIR/calls.log"
SQL_LOG="$TMP_DIR/sql.log"

systemctl() {
    printf 'systemctl %s\n' "$*" >> "$CALL_LOG"
    return 0
}

sudo() {
    printf 'sudo %s\n' "$*" >> "$CALL_LOG"
    cat >> "$SQL_LOG"
    return 0
}

random_password() {
    printf '%s' 'deterministic-db-password-2026'
}

reset_logs() {
    : > "$CALL_LOG"
    : > "$SQL_LOG"
}

# Primera instalación: sin .env hay que crear/actualizar el rol y generar la
# contraseña que luego write_env persistirá en DATABASE_URL.
FORCE_ENV=false
unset DB_PASSWORD || true
reset_logs
configure_postgres >/dev/null

grep -q '^systemctl enable --now postgresql$' "$CALL_LOG"
grep -q '^sudo -u postgres psql -v ON_ERROR_STOP=1$' "$CALL_LOG"
grep -q "ALTER ROLE ${DB_USER} WITH PASSWORD 'deterministic-db-password-2026'" "$SQL_LOG"
[ "$DB_PASSWORD" = 'deterministic-db-password-2026' ]

# Reejecución normal: un backend/.env existente representa credenciales ya
# coordinadas con PostgreSQL. No debe ejecutarse psql ni generarse otra clave.
cat > "$APP_DIR/backend/.env" <<'EOF'
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg2://inventory_user:existing-password@localhost:5432/inventory_db
EOF
FORCE_ENV=false
unset DB_PASSWORD || true
reset_logs
configure_postgres >/dev/null

grep -q '^systemctl enable --now postgresql$' "$CALL_LOG"
if grep -q '^sudo ' "$CALL_LOG"; then
    echo 'La reejecución normal intentó modificar PostgreSQL pese a existir backend/.env' >&2
    exit 1
fi
if [ -s "$SQL_LOG" ]; then
    echo 'La reejecución normal produjo SQL inesperado' >&2
    exit 1
fi
if declare -p DB_PASSWORD >/dev/null 2>&1; then
    echo 'La reejecución normal generó una nueva DB_PASSWORD' >&2
    exit 1
fi

# Rotación explícita: --force-env sí debe volver a coordinar rol y .env.
FORCE_ENV=true
unset DB_PASSWORD || true
reset_logs
configure_postgres >/dev/null

grep -q '^sudo -u postgres psql -v ON_ERROR_STOP=1$' "$CALL_LOG"
grep -q "ALTER ROLE ${DB_USER} WITH PASSWORD 'deterministic-db-password-2026'" "$SQL_LOG"
[ "$DB_PASSWORD" = 'deterministic-db-password-2026' ]

echo 'VPS installer DB credential preservation tests OK'
