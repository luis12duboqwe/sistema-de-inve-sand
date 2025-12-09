#!/bin/bash
# Backend start script - Instala pip y dependencias si es necesario

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

# INSTALAR PIP PRIMERO SI NO EXISTE
echo "📦 Verificando pip..."
if ! python3 -m pip --version &> /dev/null 2>&1; then
    echo "   pip no encontrado, instalando..."
    
    # Intentar ensurepip
    if python3 -m ensurepip --default-pip 2>/dev/null; then
        echo "   ✅ pip instalado"
    elif command -v apt-get &> /dev/null; then
        echo "   Usando apt-get para instalar python3-pip..."
        sudo apt-get update > /dev/null 2>&1
        sudo apt-get install -y python3-pip > /dev/null 2>&1
        echo "   ✅ pip instalado"
    else
        echo "   ❌ No se pudo instalar pip"
        exit 1
    fi
else
    echo "   ✅ pip disponible"
fi

echo ""

# Instalar FastAPI y deps si faltan
echo "📦 Verificando dependencias Python..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "   Instalando FastAPI, uvicorn, SQLAlchemy..."
    python3 -m pip install -q fastapi uvicorn sqlalchemy pydantic 2>/dev/null || {
        python3 -m pip install fastapi uvicorn sqlalchemy pydantic
    }
    echo "   ✅ Dependencias instaladas"
else
    echo "   ✅ FastAPI ya disponible"
fi

# BD
echo "📊 Verificando base de datos..."
if [ ! -f "inventory.db" ]; then
    echo "   Creando BD con V2.0..."
    python3 init_db.py --with-data 2>&1 | tail -3 || python3 init_db.py
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
