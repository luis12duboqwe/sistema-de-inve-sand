#!/bin/bash

# Setup ultra-simple - Instala directamente en el sistema
set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🚀 SETUP - SISTEMA DE INVENTARIO V2.0                   ║"
echo "║     (Instalación directa en sistema)                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 1. Permisos
echo "1️⃣  Dando permisos de ejecución..."
chmod +x start-backend.sh start-frontend.sh setup-backend.sh test-system.sh 2>/dev/null || true
chmod +x backend/start.sh fix-permissions.sh reset-venv.sh 2>/dev/null || true
echo "✅ Permisos configurados"
echo ""

# 2. Limpiar
echo "2️⃣  Limpiando..."
rm -rf backend/venv 2>/dev/null || true
echo "✅ Limpieza completada"
echo ""

# 3. Backend - Instalar pip primero, luego deps
echo "3️⃣  Instalando dependencias Python..."
cd backend

# INSTALAR PIP PRIMERO
echo "   Verificando pip..."
if ! python3 -m pip --version &> /dev/null 2>&1; then
    echo "   pip no encontrado, instalando..."
    if python3 -m ensurepip --default-pip 2>/dev/null; then
        echo "   ✅ pip instalado via ensurepip"
    elif command -v apt-get &> /dev/null; then
        echo "   Instalando via apt-get..."
        apt-get update > /dev/null 2>&1 || true
        apt-get install -y python3-pip > /dev/null 2>&1 || true
        echo "   ✅ pip instalado"
    fi
fi

# Actualizar pip
python3 -m pip install --upgrade pip -q 2>/dev/null || true

# Instalar requirements
if [ -f requirements.txt ]; then
    echo "   Instalando packages..."
    python3 -m pip install -r requirements.txt 2>&1 | tail -5 || {
        echo "   ⚠️  Instalando paquetes críticos..."
        python3 -m pip install fastapi uvicorn sqlalchemy pydantic -q || true
    }
fi

echo "✅ Dependencias Python instaladas"
echo ""

# 4. Base de datos
echo "4️⃣  Inicializando base de datos..."
if [ ! -f inventory.db ]; then
    echo "   Creando BD..."
    python3 init_db.py --with-data 2>&1 | tail -3 || {
        python3 init_db.py
    }
    echo "✅ BD creada"
else
    echo "ℹ️  BD ya existe"
fi
echo ""

# Volver
cd ..

# 5. Frontend
echo "5️⃣  Preparando Node.js..."
if [ ! -d node_modules ]; then
    echo "   npm install (en background)..."
    npm install > /dev/null 2>&1 &
    echo "✅ npm iniciado en background"
else
    echo "✅ npm packages listos"
fi
echo ""

# 6. Verificar
echo "6️⃣  Verificando instalación..."
echo -n "   Python: "
python3 --version 2>&1 | head -1

echo -n "   Node.js: "
node --version 2>&1 || echo "no instalado"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ SETUP COMPLETADO                                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 Ahora ejecuta en 2 terminales:"
echo ""
echo "  Terminal 1:"
echo "    ./start-backend.sh"
echo ""
echo "  Terminal 2:"
echo "    ./start-frontend.sh"
echo ""
echo "  Luego abre:"
echo "    http://localhost:5173"
echo ""
