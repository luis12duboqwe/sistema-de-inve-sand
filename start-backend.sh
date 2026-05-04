#!/bin/bash
# Backend start script - Usa entorno virtual

set -e

echo "🚀 Backend - Sistema de Inventario Multi-Ubicación V2.0"
echo ""

# Ir a backend
cd "$(dirname "$0")/backend" 2>/dev/null || cd backend

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no instalado"
    exit 1
fi

echo "✅ Python $(python3 --version | cut -d' ' -f2) encontrado"
echo ""

# Verificar si existe el entorno virtual (soporta venv y .venv)
VENV_DIR=""
if [ -d "venv" ]; then
    VENV_DIR="venv"
elif [ -d ".venv" ]; then
    VENV_DIR=".venv"
else
    echo "❌ Error: Entorno virtual no encontrado"
    echo ""
    echo "Por favor ejecuta primero:"
    echo "  ./setup-complete.sh"
    echo ""
    echo "O manualmente:"
    echo "  cd backend"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo "📦 Activando entorno virtual ($VENV_DIR)..."
source "$VENV_DIR/bin/activate"

# Verificar que las dependencias estén instaladas
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Dependencias no instaladas, instalando..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "   ✅ Dependencias instaladas"
else
    echo "   ✅ FastAPI ya disponible"
fi

echo "✅ Dependencias listas"
echo ""

# Verificar base de datos
echo "📊 Verificando base de datos..."
if [ ! -f "inventory.db" ]; then
    echo "   Creando BD vacía (V2.0)..."
    python3 init_db.py
    echo "   ✅ BD creada"
else
    echo "   ✅ BD existe"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🚀 Iniciando FastAPI en puerto 8000...                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📍 URLs:"
echo "   API: http://localhost:8000"
echo "   Swagger: http://localhost:8000/docs"
echo "   ReDoc: http://localhost:8000/redoc"
echo ""
echo "⚠️  Presiona Ctrl+C para detener"
echo ""

# Iniciar FastAPI
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
