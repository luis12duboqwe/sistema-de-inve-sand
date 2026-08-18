#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"

read_env_value() {
  local key="$1"
  local value
  value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d'=' -f2- || true)"
  value="${value%$'\r'}"
  value="${value#\"}"
  value="${value%\"}"
  value="${value#\'}"
  value="${value%\'}"
  printf '%s' "$value"
}

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE" >&2
  echo "Genera el archivo con: APP_DOMAIN=tu-dominio ./deploy/prepare-prod-env.sh $ENV_FILE" >&2
  exit 1
fi

USE_MONITORING="${USE_MONITORING:-true}"
REQUIRE_OFFSITE_BACKUP="$(read_env_value REQUIRE_OFFSITE_BACKUP)"
REQUIRE_OFFSITE_BACKUP="${REQUIRE_OFFSITE_BACKUP,,}"
PROFILES=(--profile backup)

if [ "$REQUIRE_OFFSITE_BACKUP" = "true" ]; then
  PROFILES+=(--profile backup-offsite)
fi

if [ "$USE_MONITORING" = "true" ]; then
  PROFILES+=(--profile monitoring)
fi

echo "[1/5] Validación de entorno de producción"
"$DEPLOY_DIR/validate-prod.sh" "$ENV_FILE"

echo "[2/5] Gate completo de calidad y seguridad"
"$DEPLOY_DIR/prod-gate.sh" "$ENV_FILE"

echo "[3/5] Despliegue de servicios"
if [ "$REQUIRE_OFFSITE_BACKUP" = "true" ]; then
  echo "Backup off-site obligatorio: se activará el perfil backup-offsite."
fi
cd "$DEPLOY_DIR"
PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml "${PROFILES[@]}" up -d --build

echo "[4/5] Healthcheck operativo post-deploy"
"$DEPLOY_DIR/ops-healthcheck.sh" "$ENV_FILE"

echo "[5/5] Estado de contenedores"
PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml "${PROFILES[@]}" ps

echo
echo "Release finalizado correctamente."
echo "Siguiente verificación sugerida:"
echo "  - curl -f http://127.0.0.1/api/health"
echo "  - curl -f http://127.0.0.1/api/ready"
echo "  - curl -f http://127.0.0.1/api/metrics"
