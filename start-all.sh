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

echo "🎬 Iniciando sistema en 2 procesos..."
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
echo ""
echo "🛑 Presiona Ctrl+C para detener ambos"
echo ""
echo "=========================================="
echo ""

# Esperar
wait
