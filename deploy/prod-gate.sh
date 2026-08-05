#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
ENV_FILE="${1:-$DEPLOY_DIR/.env.prod}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE" >&2
  exit 1
fi

echo "[1/8] Validando configuración de producción"
"$DEPLOY_DIR/validate-prod.sh" "$ENV_FILE"

echo "[2/8] Verificando docker compose (backup + monitoring)"
PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" -f "$DEPLOY_DIR/docker-compose.prod.yml" --profile backup --profile monitoring config --quiet

echo "[3/8] Lint frontend"
cd "$ROOT_DIR"
npm install
npm run lint

echo "[4/8] Build frontend"
npm run build

echo "[5/8] Tests frontend"
npm run test -- --run

echo "[6/8] Tests backend + E2E"
cd "$ROOT_DIR/backend"
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
cd "$ROOT_DIR"
pytest -q tests/test_health_endpoints.py tests/e2e

echo "[7/8] Auditoría de dependencias"
npm audit --audit-level=high
python -m pip install pip-audit
cd "$ROOT_DIR/backend"
pip-audit -r requirements.txt
cd "$ROOT_DIR"

echo "[8/8] Escaneo de contenedores"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$ROOT_DIR:/workspace" aquasec/trivy:0.56.2 fs --exit-code 1 --severity HIGH,CRITICAL /workspace

echo "Gate de producción completado correctamente."
