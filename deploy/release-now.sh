#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE" >&2
  echo "Genera el archivo con: APP_DOMAIN=tu-dominio ./deploy/prepare-prod-env.sh $ENV_FILE" >&2
  exit 1
fi

USE_MONITORING="${USE_MONITORING:-true}"
PROFILES=(--profile backup)
if [ "$USE_MONITORING" = "true" ]; then
  PROFILES+=(--profile monitoring)
fi

echo "[1/5] Validación de entorno de producción"
"$DEPLOY_DIR/validate-prod.sh" "$ENV_FILE"

echo "[2/5] Gate completo de calidad y seguridad"
"$DEPLOY_DIR/prod-gate.sh" "$ENV_FILE"

echo "[3/5] Despliegue de servicios"
cd "$DEPLOY_DIR"
docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml "${PROFILES[@]}" up -d --build

echo "[4/5] Healthcheck operativo post-deploy"
"$DEPLOY_DIR/ops-healthcheck.sh" "$ENV_FILE"

echo "[5/5] Estado de contenedores"
docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml ps

echo
echo "Release finalizado correctamente."
echo "Siguiente verificación sugerida:"
echo "  - curl -f http://127.0.0.1/api/health"
echo "  - curl -f http://127.0.0.1/api/ready"
echo "  - curl -f http://127.0.0.1/api/metrics"
