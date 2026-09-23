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

resolve_release_sha() {
  local configured_sha="${APP_BUILD_SHA:-}"
  local git_sha=""
  local untracked=""

  if command -v git >/dev/null 2>&1 && \
     git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git_sha="$(git -C "$ROOT_DIR" rev-parse HEAD)"

    if ! git -C "$ROOT_DIR" diff --quiet --ignore-submodules -- || \
       ! git -C "$ROOT_DIR" diff --cached --quiet --ignore-submodules --; then
      echo "El árbol Git tiene cambios rastreados sin commit; no se puede certificar un release exacto." >&2
      return 1
    fi

    untracked="$(git -C "$ROOT_DIR" ls-files --others --exclude-standard)"
    if [ -n "$untracked" ]; then
      echo "Hay archivos no rastreados que podrían entrar al build; deben versionarse o ignorarse antes del release:" >&2
      printf '%s\n' "$untracked" | sed -n '1,20p' >&2
      return 1
    fi
  fi

  local candidate="${configured_sha:-$git_sha}"
  candidate="${candidate,,}"

  if ! [[ "$candidate" =~ ^[0-9a-f]{40}$ ]]; then
    echo "No se pudo determinar un APP_BUILD_SHA Git completo de 40 caracteres." >&2
    echo "Ejecuta el release desde un checkout Git limpio o define APP_BUILD_SHA explícitamente." >&2
    return 1
  fi

  if [ -n "$git_sha" ] && [ -n "$configured_sha" ] && \
     [ "$candidate" != "${git_sha,,}" ]; then
    echo "APP_BUILD_SHA=$candidate no coincide con HEAD=${git_sha,,}; release abortado." >&2
    return 1
  fi

  printf '%s' "$candidate"
}

if [ ! -f "$ENV_FILE" ]; then
  echo "Falta $ENV_FILE" >&2
  echo "Genera el archivo con: APP_DOMAIN=tu-dominio ./deploy/prepare-prod-env.sh $ENV_FILE" >&2
  exit 1
fi

APP_BUILD_SHA="$(resolve_release_sha)"
export APP_BUILD_SHA

echo "Release SHA: $APP_BUILD_SHA"

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

backend_container_id="$(
  PROD_ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" \
    -f docker-compose.prod.yml ps -q backend
)"
if [ -z "$backend_container_id" ]; then
  echo "No se pudo identificar el contenedor backend desplegado." >&2
  exit 1
fi
backend_image_id="$(docker inspect --format '{{.Image}}' "$backend_container_id")"

echo
echo "Release finalizado correctamente."
echo "Evidencia del artefacto desplegado:"
echo "  - SHA: $APP_BUILD_SHA"
echo "  - backend container: $backend_container_id"
echo "  - backend image ID: $backend_image_id"
echo "Siguiente verificación sugerida:"
echo "  - curl -f http://127.0.0.1/api/health"
echo "  - curl -f http://127.0.0.1/api/ready"
echo "  - curl -f http://127.0.0.1/api/metrics"
