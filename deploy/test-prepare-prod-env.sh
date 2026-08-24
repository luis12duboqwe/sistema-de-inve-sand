#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ENV_FILE="$TMP_DIR/.env.prod"
CHANNEL_KEY="test-channel-encryption-key-012345678901234567890123"

env_value() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d'=' -f2-
}

APP_DOMAIN="inventory.softmobile.test" \
CHANNEL_ENCRYPTION_KEY="$CHANNEL_KEY" \
BACKUP_RCLONE_DESTINATION="offsite:bucket/inventory" \
bash "$DEPLOY_DIR/prepare-prod-env.sh" "$ENV_FILE" >/dev/null

[ -f "$ENV_FILE" ]
[ "$(stat -c '%a' "$ENV_FILE")" = "600" ]
[ "$(env_value CORS_ORIGINS)" = "https://inventory.softmobile.test" ]
[ "$(env_value ALLOWED_HOSTS)" = "inventory.softmobile.test,localhost,127.0.0.1" ]
[ "$(env_value BACKUP_RCLONE_DESTINATION)" = "offsite:bucket/inventory" ]
[ "$(env_value CHANNEL_ENCRYPTION_KEY)" = "$CHANNEL_KEY" ]

for key in POSTGRES_PASSWORD SECRET_KEY SETUP_TOKEN DESTRUCTIVE_OPERATION_TOKEN GRAFANA_ADMIN_PASSWORD; do
  value="$(env_value "$key")"
  [ "${#value}" -ge 12 ]
  case "$value" in
    *CHANGE_ME*|*GENERATE_WITH*)
      echo "$key conservó un placeholder" >&2
      exit 1
      ;;
  esac
done

# Simula una instalación existente con contraseña manual y URL codificada. Una
# segunda preparación no debe reconstruir ni dañar el DATABASE_URL operativo.
MANUAL_DB_PASSWORD='manual@password/with:special'
CUSTOM_DATABASE_URL='postgresql+psycopg2://inventory_admin:manual%40password%2Fwith%3Aspecial@db:5432/inventory'
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${MANUAL_DB_PASSWORD}|" "$ENV_FILE"
sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${CUSTOM_DATABASE_URL}|" "$ENV_FILE"

POSTGRES_PASSWORD_BEFORE="$(env_value POSTGRES_PASSWORD)"
DATABASE_URL_BEFORE="$(env_value DATABASE_URL)"
SECRET_KEY_BEFORE="$(env_value SECRET_KEY)"
CHANNEL_KEY_BEFORE="$(env_value CHANNEL_ENCRYPTION_KEY)"
SETUP_TOKEN_BEFORE="$(env_value SETUP_TOKEN)"
DESTRUCTIVE_TOKEN_BEFORE="$(env_value DESTRUCTIVE_OPERATION_TOKEN)"
GRAFANA_PASSWORD_BEFORE="$(env_value GRAFANA_ADMIN_PASSWORD)"
ALLOWED_HOSTS_BEFORE="$(env_value ALLOWED_HOSTS)"
CORS_BEFORE="$(env_value CORS_ORIGINS)"

# Una segunda ejecución sin overrides debe ser idempotente: no rota secretos,
# dominio ni una URL de base de datos personalizada.
bash "$DEPLOY_DIR/prepare-prod-env.sh" "$ENV_FILE" >/dev/null

[ "$(env_value POSTGRES_PASSWORD)" = "$POSTGRES_PASSWORD_BEFORE" ]
[ "$(env_value DATABASE_URL)" = "$DATABASE_URL_BEFORE" ]
[ "$(env_value DATABASE_URL)" = "$CUSTOM_DATABASE_URL" ]
[ "$(env_value SECRET_KEY)" = "$SECRET_KEY_BEFORE" ]
[ "$(env_value CHANNEL_ENCRYPTION_KEY)" = "$CHANNEL_KEY_BEFORE" ]
[ "$(env_value SETUP_TOKEN)" = "$SETUP_TOKEN_BEFORE" ]
[ "$(env_value DESTRUCTIVE_OPERATION_TOKEN)" = "$DESTRUCTIVE_TOKEN_BEFORE" ]
[ "$(env_value GRAFANA_ADMIN_PASSWORD)" = "$GRAFANA_PASSWORD_BEFORE" ]
[ "$(env_value ALLOWED_HOSTS)" = "$ALLOWED_HOSTS_BEFORE" ]
[ "$(env_value CORS_ORIGINS)" = "$CORS_BEFORE" ]
[ "$(stat -c '%a' "$ENV_FILE")" = "600" ]

# Una rotación explícita sí debe aplicarse sin alterar los demás secretos.
ROTATED_GRAFANA="grafana-rotated-password-2026"
GRAFANA_ADMIN_PASSWORD="$ROTATED_GRAFANA" \
bash "$DEPLOY_DIR/prepare-prod-env.sh" "$ENV_FILE" >/dev/null

[ "$(env_value GRAFANA_ADMIN_PASSWORD)" = "$ROTATED_GRAFANA" ]
[ "$(env_value POSTGRES_PASSWORD)" = "$POSTGRES_PASSWORD_BEFORE" ]
[ "$(env_value DATABASE_URL)" = "$CUSTOM_DATABASE_URL" ]
[ "$(env_value SECRET_KEY)" = "$SECRET_KEY_BEFORE" ]
[ "$(env_value CHANNEL_ENCRYPTION_KEY)" = "$CHANNEL_KEY_BEFORE" ]
[ "$(env_value SETUP_TOKEN)" = "$SETUP_TOKEN_BEFORE" ]

echo "Production env bootstrap tests OK"
