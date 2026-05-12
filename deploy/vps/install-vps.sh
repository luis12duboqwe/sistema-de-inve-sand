#!/usr/bin/env bash

set -euo pipefail

APP_USER="inventario"
APP_GROUP="www-data"
APP_DIR="/var/www/inventario"
BACKUP_DIR="/var/backups/inventory"
DB_NAME="inventory_db"
DB_USER="inventory_user"
DB_HOST="localhost"
DB_PORT="5432"
DOMAIN="invjear.com"
WWW_DOMAIN=""
EMAIL=""
WITH_SAMPLE_DATA="false"
SKIP_SSL="false"
SKIP_NODE_SETUP="false"
FORCE_ENV="false"
SELF_TEST="false"

usage() {
    cat <<'EOF'
Uso:
  sudo bash deploy/vps/install-vps.sh [opciones]

Opciones:
  --domain DOMINIO          Dominio principal. Default: invjear.com
  --www-domain DOMINIO      Dominio www. Default: www.<domain>
  --email EMAIL             Email para Certbot. Si no se indica, Certbot lo pedira/interactuara.
  --app-dir RUTA            Ruta del proyecto clonado. Default: /var/www/inventario
  --db-name NOMBRE          Base PostgreSQL. Default: inventory_db
  --db-user USUARIO         Usuario PostgreSQL. Default: inventory_user
  --with-sample-data        Ejecuta init_db.py --with-data
  --skip-ssl                No ejecuta Certbot ni configura HTTPS final
  --skip-node-setup         No instala Node.js desde NodeSource
  --force-env               Reescribe backend/.env si ya existe
    --self-test               Valida el instalador sin instalar paquetes ni tocar /etc
  -h, --help                Muestra esta ayuda

Ejemplo despues de clonar:
  cd /var/www/inventario
  sudo bash deploy/vps/install-vps.sh --domain invjear.com --email admin@invjear.com
EOF
}

log() {
    printf '\n==> %s\n' "$1"
}

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail "Ejecuta este script con sudo o como root."
    fi
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --domain)
                DOMAIN="${2:?Falta valor para --domain}"
                shift 2
                ;;
            --www-domain)
                WWW_DOMAIN="${2:?Falta valor para --www-domain}"
                shift 2
                ;;
            --email)
                EMAIL="${2:?Falta valor para --email}"
                shift 2
                ;;
            --app-dir)
                APP_DIR="${2:?Falta valor para --app-dir}"
                shift 2
                ;;
            --db-name)
                DB_NAME="${2:?Falta valor para --db-name}"
                shift 2
                ;;
            --db-user)
                DB_USER="${2:?Falta valor para --db-user}"
                shift 2
                ;;
            --with-sample-data)
                WITH_SAMPLE_DATA="true"
                shift
                ;;
            --skip-ssl)
                SKIP_SSL="true"
                shift
                ;;
            --skip-node-setup)
                SKIP_NODE_SETUP="true"
                shift
                ;;
            --force-env)
                FORCE_ENV="true"
                shift
                ;;
            --self-test)
                SELF_TEST="true"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                fail "Opcion desconocida: $1"
                ;;
        esac
    done

    if [[ -z "$WWW_DOMAIN" ]]; then
        WWW_DOMAIN="www.${DOMAIN}"
    fi
}

random_password() {
    openssl rand -base64 32 | tr -d '/+=' | cut -c1-32
}

run_self_test() {
    log "Self-test: validando repositorio"
    validate_repo

    log "Self-test: validando herramientas locales"
    command -v bash >/dev/null || fail "bash no disponible"
    command -v openssl >/dev/null || fail "openssl no disponible"
    command -v python3 >/dev/null || fail "python3 no disponible"
    command -v npm >/dev/null || fail "npm no disponible"
    command -v node >/dev/null || fail "node no disponible"

    log "Self-test: generando secretos"
    local generated_password
    local generated_secret
    local generated_fernet
    generated_password="$(random_password)"
    generated_secret="$(openssl rand -hex 32)"
    generated_fernet="$(python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
)"
    [[ ${#generated_password} -ge 24 ]] || fail "password generado demasiado corto"
    [[ ${#generated_secret} -eq 64 ]] || fail "SECRET_KEY generado invalido"
    python3 - "$generated_fernet" <<'PY'
import sys
from cryptography.fernet import Fernet
Fernet(sys.argv[1].encode())
PY

    log "Self-test: validando npm ci con legacy peer deps"
    (cd "$APP_DIR" && npm ci --legacy-peer-deps --dry-run)

    log "Self-test: validando imports backend"
    local python_bin="python3"
    if [[ -x "$APP_DIR/backend/venv/bin/python" ]]; then
        python_bin="$APP_DIR/backend/venv/bin/python"
    fi
    PYTHONPATH="$APP_DIR/backend" ENVIRONMENT=testing DEBUG=true ALLOWED_HOSTS='*' \
        DATABASE_URL='postgresql+psycopg2://selftest:selftest@localhost:5432/selftest' \
        "$python_bin" - <<'PY'
from app.config import Settings

settings = Settings(
    database_url="postgresql+psycopg2://selftest:selftest@localhost:5432/selftest",
    environment="testing",
    debug=True,
    allowed_hosts="*",
    cors_origins="http://localhost",
)
assert settings.environment == "testing"
PY

    log "Self-test: validando plantillas de texto"
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' RETURN
    cat > "$tmp_dir/inventario.service" <<EOF
[Service]
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=${APP_DIR}/backend/.env
ExecStart=${APP_DIR}/backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
EOF
    grep -q "$APP_DIR/backend" "$tmp_dir/inventario.service"

    echo "Self-test OK: el instalador esta listo para ejecutarse en VPS."
}

install_packages() {
    log "Instalando paquetes del sistema"
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        ca-certificates \
        certbot \
        curl \
        git \
        nginx \
        openssl \
        postgresql \
        postgresql-client \
        python3-certbot-nginx \
        python3-pip \
        python3-venv

    if [[ "$SKIP_NODE_SETUP" != "true" ]]; then
        if ! command -v node >/dev/null 2>&1 || ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)' >/dev/null 2>&1; then
            log "Instalando Node.js 22 LTS"
            curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
            DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs
        fi
    fi
}

validate_repo() {
    log "Validando repositorio en ${APP_DIR}"
    [[ -d "$APP_DIR" ]] || fail "No existe ${APP_DIR}. Clona el repo ahi primero."
    [[ -f "$APP_DIR/package.json" ]] || fail "No encuentro package.json en ${APP_DIR}."
    [[ -f "$APP_DIR/backend/requirements.txt" ]] || fail "No encuentro backend/requirements.txt."
}

create_user_and_dirs() {
    log "Creando usuario y directorios"
    useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER" 2>/dev/null || true
    mkdir -p "$APP_DIR" "$BACKUP_DIR" "$APP_DIR/backend/logs" "$APP_DIR/backend/uploads" /var/www/html
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR" "$BACKUP_DIR"
}

configure_postgres() {
    log "Configurando PostgreSQL"
    systemctl enable --now postgresql

    DB_PASSWORD="$(random_password)"
    sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
    ELSE
        ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;

SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL
}

write_env() {
    log "Creando backend/.env"
    local env_file="$APP_DIR/backend/.env"
    if [[ -f "$env_file" && "$FORCE_ENV" != "true" ]]; then
        echo "Ya existe ${env_file}; no lo reescribo. Usa --force-env para regenerarlo."
        echo "Verificando que el .env existente pueda conectarse a PostgreSQL..."
        if ! sudo -u "$APP_USER" bash -lc "cd '$APP_DIR/backend' && set -a && . ./.env && set +a && ./venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)
with engine.connect() as connection:
    connection.execute(text('SELECT 1'))
PY"; then
            fail "El .env existente no conecta a PostgreSQL. Reejecuta con --force-env para regenerar DATABASE_URL y password."
        fi
        return 0
    fi

    local secret_key
    local channel_key
    secret_key="$(openssl rand -hex 32)"
    channel_key="$($APP_DIR/backend/venv/bin/python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
)"

    umask 077
    cat > "$env_file" <<EOF
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

CORS_ORIGINS=https://${DOMAIN},https://${WWW_DOMAIN}
ALLOWED_HOSTS=${DOMAIN},${WWW_DOMAIN},localhost,127.0.0.1

SECRET_KEY=${secret_key}
CHANNEL_ENCRYPTION_KEY=${channel_key}
ACCESS_TOKEN_EXPIRE_MINUTES=60

ENABLE_AUTO_BACKUP=true
BACKUP_DIR=${BACKUP_DIR}
BACKUP_RETENTION_DAYS=30

LOG_LEVEL=INFO
LOG_STRUCTURED=true
LOG_TO_FILES=true
LOG_DIRECTORY=./logs
LOG_INCLUDE_CONSOLE=true

SENTRY_DISABLED=true
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.0
SENTRY_PROFILES_SAMPLE_RATE=0.0

ENABLE_AI_FEATURES=false
ENABLE_FORECAST_SCHEDULER=false
OPENAI_API_KEY=

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TLS=true

N8N_WEBHOOK_URL=
N8N_AUTH_TOKEN=
EOF
    chown "$APP_USER:$APP_GROUP" "$env_file"
}

install_backend() {
    log "Instalando backend Python"
    cd "$APP_DIR/backend"
    sudo -u "$APP_USER" python3 -m venv venv
    sudo -u "$APP_USER" ./venv/bin/pip install --upgrade pip
    sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt
}

init_database() {
    log "Inicializando tablas"
    cd "$APP_DIR/backend"
    if [[ "$WITH_SAMPLE_DATA" == "true" ]]; then
        sudo -u "$APP_USER" bash -lc "cd '$APP_DIR/backend' && set -a && . ./.env && set +a && ./venv/bin/python init_db.py --with-data"
    else
        sudo -u "$APP_USER" bash -lc "cd '$APP_DIR/backend' && set -a && . ./.env && set +a && ./venv/bin/python init_db.py"
    fi
}

build_frontend() {
    log "Construyendo frontend"
    cd "$APP_DIR"
    npm ci --legacy-peer-deps
    npm run build
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR/dist"
}

write_systemd() {
    log "Configurando systemd"
    cat > /etc/systemd/system/inventario.service <<EOF
[Unit]
Description=Sistema de Inventario FastAPI
After=network.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=${APP_DIR}/backend/.env
Environment=PYTHONPATH=${APP_DIR}/backend
ExecStart=${APP_DIR}/backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGINT

NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=${APP_DIR}/backend/logs ${APP_DIR}/backend/uploads ${BACKUP_DIR}

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now inventario
}

write_nginx_http() {
    log "Configurando Nginx HTTP"
    cat > "/etc/nginx/sites-available/${DOMAIN}" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} ${WWW_DOMAIN};

    server_tokens off;
    client_max_body_size 25m;

    root ${APP_DIR}/dist;
    index index.html;

    location = /health {
        access_log off;
        add_header Content-Type text/plain;
        return 200 "ok\n";
    }

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /assets/ {
        try_files \$uri =404;
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
    ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl enable --now nginx
    systemctl reload nginx
}

configure_ssl() {
    if [[ "$SKIP_SSL" == "true" ]]; then
        echo "SSL omitido por --skip-ssl."
        return 0
    fi

    log "Solicitando certificado Let's Encrypt"
    local certbot_args=(--nginx -d "$DOMAIN" -d "$WWW_DOMAIN" --redirect --agree-tos --non-interactive)
    if [[ -n "$EMAIL" ]]; then
        certbot_args+=(--email "$EMAIL")
    else
        certbot_args+=(--register-unsafely-without-email)
    fi
    certbot "${certbot_args[@]}"
    write_nginx_ssl
    nginx -t
    systemctl reload nginx
}

write_nginx_ssl() {
    log "Aplicando configuracion Nginx HTTPS final"
    cat > "/etc/nginx/sites-available/${DOMAIN}" <<EOF
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} ${WWW_DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://${DOMAIN}\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN} ${WWW_DOMAIN};

    server_tokens off;
    client_max_body_size 25m;

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Permissions-Policy "accelerometer=(), camera=(), gyroscope=(), microphone=()" always;
    add_header Content-Security-Policy "default-src 'self'; connect-src 'self' https: wss:; img-src 'self' data: blob: https:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;

    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
    gzip_min_length 256;

    root ${APP_DIR}/dist;
    index index.html;

    location = /health {
        access_log off;
        add_header Content-Type text/plain;
        return 200 "ok\n";
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_connect_timeout 30s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }

    location /assets/ {
        try_files \$uri =404;
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
}

configure_backup() {
    log "Configurando backup diario"
    cat > /etc/cron.d/inventario-backup <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 2 * * * ${APP_USER} cd ${APP_DIR}/backend && set -a && . ./.env && set +a && ./backup_database.sh >> /var/log/inventario-backup.log 2>&1
EOF
    chmod 0644 /etc/cron.d/inventario-backup
    sudo -u "$APP_USER" bash -lc "cd '$APP_DIR/backend' && set -a && . ./.env && set +a && ./backup_database.sh"
}

run_checks() {
    log "Ejecutando verificaciones finales"
    systemctl --no-pager --full status inventario || true
    curl -fsS "http://127.0.0.1:8000/api/health" >/dev/null
    curl -fsS "http://127.0.0.1/health" >/dev/null

    if [[ "$SKIP_SSL" != "true" ]]; then
        curl -fsS "https://${DOMAIN}/health" >/dev/null || true
        curl -fsS "https://${DOMAIN}/api/health" >/dev/null || true
    fi
}

main() {
    parse_args "$@"
    if [[ "$SELF_TEST" == "true" ]]; then
        run_self_test
        exit 0
    fi

    require_root
    validate_repo
    install_packages
    create_user_and_dirs
    install_backend
    configure_postgres
    write_env
    init_database
    build_frontend
    write_systemd
    write_nginx_http
    configure_ssl
    configure_backup
    run_checks

    cat <<EOF

Listo.

Frontend: https://${DOMAIN}
Backend health: https://${DOMAIN}/api/health

Comandos utiles:
  systemctl status inventario
  journalctl -u inventario -n 100 --no-pager
  tail -n 100 /var/log/inventario-backup.log
EOF
}

main "$@"