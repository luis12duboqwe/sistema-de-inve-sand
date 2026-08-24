#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ENV_FILE="$TMP_DIR/.env.prod"

env_value() {
  local key="$1"
  local file="${2:-$ENV_FILE}"
  grep -E "^${key}=" "$file" | tail -n 1 | cut -d'=' -f2-
}

APP_DOMAIN="inventory.softmobile.test" \
BACKUP_RCLONE_DESTINATION="offsite:bucket/inventory" \
bash "$DEPLOY_DIR/prepare-prod-env.sh" "$ENV_FILE" >/dev/null

[ -f "$ENV_FILE" ]
[ "$(stat -c '%a' "$ENV_FILE")" = "600" ]
[ "$(env_value CORS_ORIGINS)" = "https://inventory.softmobile.test" ]
[ "$(env_value ALLOWED_HOSTS)" = "inventory.softmobile.test,localhost,127.0.0.1" ]
[ "$(env_value BACKUP_RCLONE_DESTINATION)" = "offsite:bucket/inventory" ]

CHANNEL_KEY="$(env_value CHANNEL_ENCRYPTION_KEY)"
python3 - "$CHANNEL_KEY" <<'PY'
import base64
import sys
value = sys.argv[1].encode()
assert len(value) == 44
assert len(base64.urlsafe_b64decode(value)) == 32
PY

for key in POSTGRES_PASSWORD SECRET_KEY SETUP_TOKEN DESTRUCTIVE_OPERATION_TOKEN GRAFANA_ADMIN_PASSWORD; do
  value="$(env_value "$key")"
  [ "${#value}" -ge 12 ]
  case "$value" in
    CHANGE_ME_STRONG_PASSWORD|GENERATE_WITH_OPENSSL_RAND_HEX_32|GENERATE_WITH_FERNET_GENERATE_KEY|CHANGE_ME_GRAFANA_PASSWORD)
      echo "$key conservó el sentinel exacto del template en un entorno nuevo" >&2
      exit 1
      ;;
  esac
done

# Simula valores reales que contienen palabras parecidas a los placeholders. Deben
# conservarse: sólo los sentinelas exactos del template son reemplazables.
MANUAL_DB_PASSWORD='prod_CHANGE_ME_later_2026'
CUSTOM_DATABASE_URL='postgresql+psycopg2://inventory_admin:prod_CHANGE_ME_later_2026@db:5432/inventory'
REAL_HOST='myexample.com'
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${MANUAL_DB_PASSWORD}|" "$ENV_FILE"
sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${CUSTOM_DATABASE_URL}|" "$ENV_FILE"
sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=${REAL_HOST},localhost,127.0.0.1|" "$ENV_FILE"
sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=https://${REAL_HOST}|" "$ENV_FILE"

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
# dominio ni una URL de base de datos personalizada, incluso cuando sus valores
# contienen texto como CHANGE_ME o example.com de forma legítima.
bash "$DEPLOY_DIR/prepare-prod-env.sh" "$ENV_FILE" >/dev/null

[ "$(env_value POSTGRES_PASSWORD)" = "$POSTGRES_PASSWORD_BEFORE" ]
[ "$(env_value POSTGRES_PASSWORD)" = "$MANUAL_DB_PASSWORD" ]
[ "$(env_value DATABASE_URL)" = "$DATABASE_URL_BEFORE" ]
[ "$(env_value DATABASE_URL)" = "$CUSTOM_DATABASE_URL" ]
[ "$(env_value SECRET_KEY)" = "$SECRET_KEY_BEFORE" ]
[ "$(env_value CHANNEL_ENCRYPTION_KEY)" = "$CHANNEL_KEY_BEFORE" ]
[ "$(env_value SETUP_TOKEN)" = "$SETUP_TOKEN_BEFORE" ]
[ "$(env_value DESTRUCTIVE_OPERATION_TOKEN)" = "$DESTRUCTIVE_TOKEN_BEFORE" ]
[ "$(env_value GRAFANA_ADMIN_PASSWORD)" = "$GRAFANA_PASSWORD_BEFORE" ]
[ "$(env_value ALLOWED_HOSTS)" = "$ALLOWED_HOSTS_BEFORE" ]
[ "$(env_value CORS_ORIGINS)" = "$CORS_BEFORE" ]
[ "$(env_value CORS_ORIGINS)" = "https://${REAL_HOST}" ]
[ "$(stat -c '%a' "$ENV_FILE")" = "600" ]

# APP_DOMAIN explícito representa un cambio intencional de dominio y debe actualizar
# los valores derivados sin tocar los secretos o DATABASE_URL existentes.
APP_DOMAIN="inventory-new.softmobile.test" \
bash "$DEPLOY_DIR/prepare-prod-env.sh" "$ENV_FILE" >/dev/null

[ "$(env_value ALLOWED_HOSTS)" = "inventory-new.softmobile.test,localhost,127.0.0.1" ]
[ "$(env_value CORS_ORIGINS)" = "https://inventory-new.softmobile.test" ]
[ "$(env_value POSTGRES_PASSWORD)" = "$POSTGRES_PASSWORD_BEFORE" ]
[ "$(env_value DATABASE_URL)" = "$CUSTOM_DATABASE_URL" ]
[ "$(env_value SECRET_KEY)" = "$SECRET_KEY_BEFORE" ]
[ "$(env_value CHANNEL_ENCRYPTION_KEY)" = "$CHANNEL_KEY_BEFORE" ]
[ "$(env_value GRAFANA_ADMIN_PASSWORD)" = "$GRAFANA_PASSWORD_BEFORE" ]

# Una copia del template puede personalizar usuario, base o topología antes de
# generar la contraseña. Si la contraseña de DATABASE_URL sigue siendo exactamente
# el sentinel del template, hay que reemplazar sólo esa credencial y preservar el
# resto de la URL personalizada, incluyendo encoding del usuario e IPv6.
CUSTOM_TEMPLATE_ENV="$TMP_DIR/custom-template.env"
cp "$DEPLOY_DIR/.env.prod.example" "$CUSTOM_TEMPLATE_ENV"
sed -i 's|^POSTGRES_DB=.*|POSTGRES_DB=custom_inventory|' "$CUSTOM_TEMPLATE_ENV"
sed -i 's|^POSTGRES_USER=.*|POSTGRES_USER=custom_admin|' "$CUSTOM_TEMPLATE_ENV"
sed -i 's|^DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg2://custom%40admin:CHANGE_ME_STRONG_PASSWORD@[2001:db8::42]:5544/custom_inventory?sslmode=require|' "$CUSTOM_TEMPLATE_ENV"

APP_DOMAIN="custom.softmobile.test" \
BACKUP_RCLONE_DESTINATION="offsite:bucket/custom" \
bash "$DEPLOY_DIR/prepare-prod-env.sh" "$CUSTOM_TEMPLATE_ENV" >/dev/null 2>/dev/null

CUSTOM_GENERATED_PASSWORD="$(env_value POSTGRES_PASSWORD "$CUSTOM_TEMPLATE_ENV")"
CUSTOM_REBUILT_URL="$(env_value DATABASE_URL "$CUSTOM_TEMPLATE_ENV")"
[ "$CUSTOM_GENERATED_PASSWORD" != "CHANGE_ME_STRONG_PASSWORD" ]
[ "$CUSTOM_REBUILT_URL" = "postgresql+psycopg2://custom%40admin:${CUSTOM_GENERATED_PASSWORD}@[2001:db8::42]:5544/custom_inventory?sslmode=require" ]

# Un archivo preexistente con placeholder de Grafana puede corresponder a un volumen
# ya inicializado. El bootstrap no debe fingir una rotación cambiando sólo el env.
EXISTING_ENV="$TMP_DIR/existing.env"
cp "$DEPLOY_DIR/.env.prod.example" "$EXISTING_ENV"
APP_DOMAIN="existing.softmobile.test" \
BACKUP_RCLONE_DESTINATION="offsite:bucket/existing" \
bash "$DEPLOY_DIR/prepare-prod-env.sh" "$EXISTING_ENV" >/dev/null 2>/dev/null

[ "$(env_value GRAFANA_ADMIN_PASSWORD "$EXISTING_ENV")" = "CHANGE_ME_GRAFANA_PASSWORD" ]
[ "$(stat -c '%a' "$EXISTING_ENV")" = "600" ]

# Ni siquiera un override explícito debe presentarse como rotación de Grafana en
# un entorno existente. Debe fallar y dejar el archivo intacto.
if GRAFANA_ADMIN_PASSWORD='pretend-rotation-password-2026' \
   bash "$DEPLOY_DIR/prepare-prod-env.sh" "$EXISTING_ENV" >/dev/null 2>/dev/null; then
  echo "El bootstrap aceptó una falsa rotación de Grafana en un entorno existente" >&2
  exit 1
fi
[ "$(env_value GRAFANA_ADMIN_PASSWORD "$EXISTING_ENV")" = "CHANGE_ME_GRAFANA_PASSWORD" ]

echo "Production env bootstrap tests OK"
