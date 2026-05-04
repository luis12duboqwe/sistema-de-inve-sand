#!/bin/bash

echo "=========================================="
echo "🚀 INICIO RÁPIDO - TODO EN UNO"
echo "=========================================="
echo ""

# Verificar si ya está configurado
if [ ! -d "backend/venv" ] || [ ! -d "node_modules" ]; then
    echo "⚙️  Primera vez - Configurando sistema..."
    echo ""
    
    # Verificar python3-venv
    if ! dpkg -l | grep -q python3.*-venv; then
        echo "📦 Instalando python3-venv..."
        sudo apt update && sudo apt install -y python3.11-venv python3-full
    fi
    
    # Ejecutar setup completo
    chmod +x setup-complete.sh
    ./setup-complete.sh
    
    echo ""
    echo "✅ Configuración completada"
    echo ""
fi

echo "🎬 Iniciando sistema en 3 procesos..."
echo ""

# Hacer scripts ejecutables
chmod +x start-backend.sh start-frontend.sh

# Función para cleanup
cleanup() {
    echo ""
    echo "🛑 Deteniendo servicios..."
    pkill -P $$ 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# ============================================================
# Iniciar PostgreSQL via Docker (si está configurado)
# ============================================================
if grep -q "postgresql" backend/.env 2>/dev/null; then
    if command -v docker &>/dev/null; then
        echo "🐘 Iniciando PostgreSQL (Docker)..."

        # Si el contenedor ya existe, solo iniciarlo; si no, levantarlo con compose
        if docker ps -a --format '{{.Names}}' | grep -q "^inventory-postgres$"; then
            docker start inventory-postgres > /dev/null 2>&1
        elif [ -f "docker-compose.yml" ]; then
            docker compose up -d postgres > /dev/null 2>&1
        fi

        # Esperar a que PostgreSQL esté listo (hasta 20 segundos)
        echo -n "   Esperando conexión a PostgreSQL"
        for i in $(seq 1 20); do
            if docker exec inventory-postgres pg_isready -U inventory_user -q 2>/dev/null; then
                echo " ✅"
                break
            fi
            echo -n "."
            sleep 1
        done
        echo ""
    else
        echo "⚠️  Docker no encontrado. Asegúrate que PostgreSQL esté corriendo manualmente."
        echo ""
    fi
fi

# Iniciar backend
echo "🔧 Iniciando backend en puerto 8000..."
cd backend
source venv/bin/activate
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | sed 's/^/[BACKEND] /' &
BACKEND_PID=$!
cd ..

# Esperar 3 segundos
sleep 3

# Iniciar frontend
echo "🎨 Iniciando frontend en puerto 5173..."
npm run dev 2>&1 | sed 's/^/[FRONTEND] /' &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "✅ SISTEMA INICIADO"
echo "=========================================="
echo ""
echo "🌐 URLs:"
echo "  Frontend:  http://localhost:5173"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  pgAdmin:   http://localhost:5050  (admin@example.com / admin)"
echo ""
echo "🛑 Presiona Ctrl+C para detener ambos"
echo ""
echo "=========================================="
echo ""

# Esperar
wait
