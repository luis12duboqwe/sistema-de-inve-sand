#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Render Compose using only synthetic configuration and verify the real
# mounted volume receives the database backup files.
cat > "$TMP_DIR/.env.prod" <<'EOF'
ENVIRONMENT=production
POSTGRES_DB=audit_synthetic
POSTGRES_USER=audit_synthetic
POSTGRES_PASSWORD=synthetic
DATABASE_URL=postgresql://audit_synthetic:synthetic@db:5432/audit_synthetic
BACKUP_DIR=/app/backups
EOF
PROD_ENV_FILE="$TMP_DIR/.env.prod" docker compose \
    --env-file "$TMP_DIR/.env.prod" \
    -f "$ROOT_DIR/deploy/docker-compose.prod.yml" \
    config --format json > "$TMP_DIR/compose.json"
python3 - "$TMP_DIR/compose.json" <<'PY'
import json,sys
config=json.load(open(sys.argv[1]))
backup=config['services']['backup']
assert backup['environment']['BACKUP_DIR']=='/backups',backup['environment']
mounts=backup['volumes']
assert any(m.get('target')=='/backups' and m.get('type')=='volume' for m in mounts), mounts
assert config['services']['backend']['environment']['BACKUP_DIR']=='/app/backups'
print("Persistencia backup Compose OK")
PY

# nginx MUST hide metrics from public requests; the operational healthcheck
# must query the backend container directly.
grep -Eq 'location = /api/metrics[[:space:]]*\{' "$ROOT_DIR/deploy/nginx.conf"
grep -Fq 'exec -T backend' "$ROOT_DIR/deploy/ops-healthcheck.sh"
if grep -Eq 'curl.*frontend_port.*api/metrics' "$ROOT_DIR/deploy/ops-healthcheck.sh"; then
    echo "Healthcheck continúa intentando consultar métricas públicas" >&2
    exit 1
fi

# First-time VPS bootstrap creates a separate SETUP_TOKEN; no real packages,
# database or ownership mutations are involved.
source "$ROOT_DIR/deploy/vps/install-vps.sh"
APP_DIR="$TMP_DIR/app"
APP_USER="audit"
APP_GROUP="audit"
DB_PASSWORD="synthetic"
WWW_DOMAIN="www.example.invalid"
DOMAIN="example.invalid"
mkdir -p "$APP_DIR/backend/venv/bin"
cat > "$APP_DIR/backend/venv/bin/python" <<'EOF'
#!/bin/sh
printf 'ZmFrZS1mZXJuZXQta2V5\n'
EOF
chmod +x "$APP_DIR/backend/venv/bin/python"
chown() { :; }
write_env >/dev/null
env_file="$APP_DIR/backend/.env"
test -f "$env_file"
token="$(grep '^SETUP_TOKEN=' "$env_file" | cut -d= -f2-)"
[[ "$token" =~ ^[[:xdigit:]]{64}$ ]] || { echo "SETUP_TOKEN inválido" >&2; exit 1; }
secret="$(grep '^SECRET_KEY=' "$env_file" | cut -d= -f2-)"
[ "$token" != "$secret" ] || { echo "SETUP_TOKEN no debe reutilizar SECRET_KEY" >&2; exit 1; }
grep -Fq 'ENVIRONMENT=production' "$env_file"
echo "Bootstrap SETUP_TOKEN y seguridad inicial OK"
