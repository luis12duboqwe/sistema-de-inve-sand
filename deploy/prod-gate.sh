#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"
TEST_DB_CONTAINER="inventory-test-postgres-$RANDOM"
TEST_DB_PORT="${TEST_DB_PORT:-55432}"

cleanup() {
  docker rm -f "$TEST_DB_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

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
  exit 1
fi

echo "[1/9] Validando configuración de producción"
"$DEPLOY_DIR/validate-prod.sh" "$ENV_FILE"

REQUIRE_OFFSITE_BACKUP="$(read_env_value REQUIRE_OFFSITE_BACKUP)"
REQUIRE_OFFSITE_BACKUP="${REQUIRE_OFFSITE_BACKUP,,}"
COMPOSE_PROFILES=(--profile backup --profile monitoring)
if [ "$REQUIRE_OFFSITE_BACKUP" = "true" ]; then
  COMPOSE_PROFILES+=(--profile backup-offsite)
fi

echo "[2/9] Verificando docker compose (backup + monitoring${REQUIRE_OFFSITE_BACKUP:+ + política off-site})"
PROD_ENV_FILE="$ENV_FILE" docker compose \
  --env-file "$ENV_FILE" \
  -f "$DEPLOY_DIR/docker-compose.prod.yml" \
  "${COMPOSE_PROFILES[@]}" \
  config --quiet

echo "[3/9] Lint frontend"
cd "$ROOT_DIR"
npm ci --legacy-peer-deps
npm run lint

echo "[4/9] Build frontend"
npm run build

echo "[5/9] Tests frontend"
npm run test:coverage

echo "[6/9] Levantando PostgreSQL temporal para pruebas reales"
docker run -d --name "$TEST_DB_CONTAINER" \
  -e POSTGRES_DB=inventory_test \
  -e POSTGRES_USER=inventory_test \
  -e POSTGRES_PASSWORD=inventory_test_password \
  -p "127.0.0.1:${TEST_DB_PORT}:5432" \
  postgres:16-alpine >/dev/null

for _ in $(seq 1 40); do
  if docker exec "$TEST_DB_CONTAINER" pg_isready -U inventory_test -d inventory_test >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! docker exec "$TEST_DB_CONTAINER" pg_isready -U inventory_test -d inventory_test >/dev/null 2>&1; then
  echo "PostgreSQL temporal no quedó disponible" >&2
  exit 1
fi

export CI=true
export ENVIRONMENT=testing
export DEBUG=true
export DATABASE_URL="postgresql+psycopg2://inventory_test:inventory_test_password@127.0.0.1:${TEST_DB_PORT}/inventory_test"
export ALLOWED_HOSTS='*'
export CORS_ORIGINS='http://testserver,http://127.0.0.1'
export SENTRY_DISABLED=true
export ENABLE_AI_FEATURES=false

echo "[7/9] Tests backend + E2E PostgreSQL"
cd "$ROOT_DIR/backend"
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing -ra
cd "$ROOT_DIR"
pytest -q tests/test_health_endpoints.py
pytest -q tests/e2e/test_runtime_e2e.py tests/e2e/test_business_flows_e2e.py
pytest -q tests/e2e/test_postgres_runtime_e2e.py

echo "[8/9] Auditoría de dependencias"
npm audit --audit-level=high
python -m pip install pip-audit
cd "$ROOT_DIR/backend"
pip-audit -r requirements.txt
cd "$ROOT_DIR"

echo "[9/9] Build y escaneo de contenedores"
docker build --pull --no-cache -t inventory-backend:gate "$ROOT_DIR/backend"
docker build --pull --no-cache -t inventory-frontend:gate -f "$ROOT_DIR/Dockerfile.frontend" "$ROOT_DIR"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.56.2 image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed inventory-backend:gate
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.56.2 image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed inventory-frontend:gate

echo "Gate de producción completado correctamente."
