#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

CONTAINER_NAME="inventory-postgres"
POSTGRES_IMAGE="postgres:16"
POSTGRES_USER="${POSTGRES_USER:-inventory_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-inventory_pass}"
POSTGRES_DB="${POSTGRES_DB:-inventory_db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

echo "=========================================="
echo "🚀 INICIO TODO EN UNO (POSTGRESQL)"
echo "=========================================="
echo ""

check_port_free() {
    local port="$1"
    local service_name="$2"
    if lsof -ti:"$port" >/dev/null 2>&1; then
        echo "❌ Puerto $port en uso ($service_name)."
        echo "   Libéralo o cambia el puerto con variable de entorno."
        echo "   Ejemplo: BACKEND_PORT=8001 FRONTEND_PORT=5174 ./start-all-postgres.sh"
        exit 1
    fi
}

if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker no está instalado o no está en PATH."
    exit 1
fi

if [ ! -d "backend/venv" ] && [ ! -d "backend/.venv" ]; then
    echo "❌ No se encontró entorno virtual en backend (venv o .venv)."
    echo "   Ejecuta primero: ./start-backend.sh"
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo "❌ node_modules no existe. Ejecuta: npm install"
    exit 1
fi

check_port_free "$BACKEND_PORT" "backend"
check_port_free "$FRONTEND_PORT" "frontend"

echo "🐘 Preparando PostgreSQL ($CONTAINER_NAME)..."

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker start "$CONTAINER_NAME" >/dev/null
    fi
    echo "   ✅ Contenedor existente en uso"
else
    docker run -d \
      --name "$CONTAINER_NAME" \
      -e POSTGRES_USER="$POSTGRES_USER" \
      -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
      -e POSTGRES_DB="$POSTGRES_DB" \
      -p "$POSTGRES_PORT":5432 \
      "$POSTGRES_IMAGE" >/dev/null
    echo "   ✅ Contenedor creado"
fi

echo "⏳ Esperando PostgreSQL listo..."
for i in {1..30}; do
    if docker exec "$CONTAINER_NAME" pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1; then
        echo "   ✅ PostgreSQL disponible"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "❌ PostgreSQL no respondió a tiempo"
        docker logs --tail 50 "$CONTAINER_NAME" || true
        exit 1
    fi
    sleep 1
done

DATABASE_URL="postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"

cleanup() {
    echo ""
    echo "🛑 Deteniendo backend y frontend..."
    pkill -P $$ 2>/dev/null || true
    echo "   ℹ️ PostgreSQL queda ejecutándose en Docker ($CONTAINER_NAME)."
    exit 0
}

trap cleanup INT TERM

VENV_DIR="venv"
if [ ! -d "backend/$VENV_DIR" ] && [ -d "backend/.venv" ]; then
    VENV_DIR=".venv"
fi

echo "🔧 Iniciando backend en puerto $BACKEND_PORT..."
(
    cd backend
    source "$VENV_DIR/bin/activate"
    DATABASE_URL="$DATABASE_URL" uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
) 2>&1 | sed 's/^/[BACKEND] /' &

sleep 3

echo "🎨 Iniciando frontend en puerto $FRONTEND_PORT..."
npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" 2>&1 | sed 's/^/[FRONTEND] /' &

echo ""
echo "=========================================="
echo "✅ SISTEMA INICIADO (POSTGRESQL)"
echo "=========================================="
echo ""
echo "🌐 URLs:"
echo "  Frontend:  http://localhost:${FRONTEND_PORT}"
echo "  Backend:   http://localhost:${BACKEND_PORT}"
echo "  API Docs:  http://localhost:${BACKEND_PORT}/docs"
echo ""
echo "🗄️ Base de datos:"
echo "  Docker:    ${CONTAINER_NAME}"
echo "  URL:       ${DATABASE_URL}"
echo ""
echo "🛑 Presiona Ctrl+C para detener backend/frontend"
echo "   (PostgreSQL sigue corriendo en Docker)"
echo ""
echo "=========================================="
echo ""

wait
