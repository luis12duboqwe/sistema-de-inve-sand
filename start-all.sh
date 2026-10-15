#!/usr/bin/env bash
# Inicio LOCAL únicamente; no aprovisiona ni reescribe bases de datos.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
ENVIRONMENT="${ENVIRONMENT:-development}"
if [[ "$ENVIRONMENT" == "production" || "$ENVIRONMENT" == "prod" ]]; then
  echo "No ejecutar start-all.sh en producción: usar deploy/release-now.sh" >&2
  exit 2
fi
if [[ ! -d node_modules ]]; then
  echo "Faltan dependencias frontend: ejecute npm ci --legacy-peer-deps" >&2
  exit 2
fi
PYTHON=""
if [[ -x backend/.venv/bin/python ]]; then
  PYTHON="backend/.venv/bin/python"
elif [[ -x backend/venv/bin/python ]]; then
  PYTHON="backend/venv/bin/python"
else
  echo "Falta entorno virtual: python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt" >&2
  exit 2
fi
if [[ ! -f backend/.env ]]; then
  echo "Falta backend/.env; configurar DATABASE_URL para una base local de desarrollo." >&2
  exit 2
fi
if ! grep -Eq '^DATABASE_URL=' backend/.env; then
  echo "Falta DATABASE_URL; NO se creará una BD automáticamente." >&2
  exit 2
fi
command -v npm >/dev/null || { echo "npm no instalado" >&2; exit 2; }
backend_pid=""
frontend_pid=""
cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$backend_pid" ]]; then kill "$backend_pid" 2>/dev/null || true; fi
  if [[ -n "$frontend_pid" ]]; then kill "$frontend_pid" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
echo "Iniciando FastAPI local en 127.0.0.1:8000"
(cd backend && "./${PYTHON#backend/}" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
backend_pid=$!
echo "Iniciando Vite local en 127.0.0.1:5173"
npm run dev -- --host 127.0.0.1 &
frontend_pid=$!
# wait -n exits when either process fails; trap terminates the other.
wait -n "$backend_pid" "$frontend_pid"
