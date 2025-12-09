#!/bin/bash

echo "=========================================="
echo "🚀 CONFIGURACIÓN COMPLETA DEL SISTEMA"
echo "=========================================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función para logs
info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

# Verificar si estamos en el directorio correcto
if [ ! -f "package.json" ] || [ ! -d "backend" ]; then
    error "Por favor ejecuta este script desde la raíz del proyecto"
    exit 1
fi

echo "PASO 1: Instalando python3-venv"
echo "--------------------------------"
info "Instalando python3-venv y python3-full..."
sudo apt update
sudo apt install -y python3.11-venv python3-full
if [ $? -eq 0 ]; then
    success "python3-venv instalado"
else
    error "Error instalando python3-venv"
    exit 1
fi

echo ""
echo "PASO 2: Configurando Backend"
echo "-----------------------------"

cd backend

# Limpiar venv anterior si está corrupto
if [ -d "venv" ] && [ ! -f "venv/bin/activate" ]; then
    warn "Eliminando entorno virtual corrupto..."
    rm -rf venv
fi

# Crear entorno virtual
if [ ! -d "venv" ]; then
    info "Creando entorno virtual..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        success "Entorno virtual creado"
    else
        error "Error creando entorno virtual"
        exit 1
    fi
else
    success "Entorno virtual ya existe"
fi

# Activar entorno virtual
info "Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
info "Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
info "Instalando dependencias Python (esto puede tomar unos minutos)..."
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    success "Dependencias Python instaladas"
else
    error "Error instalando dependencias Python"
    deactivate
    exit 1
fi

# Inicializar base de datos
if [ ! -f "inventory.db" ]; then
    info "Inicializando base de datos con datos de prueba..."
    python3 init_db.py --with-data
    if [ $? -eq 0 ]; then
        success "Base de datos inicializada"
    else
        error "Error inicializando base de datos"
        deactivate
        exit 1
    fi
else
    success "Base de datos ya existe"
fi

deactivate
cd ..

echo ""
echo "PASO 3: Configurando Frontend"
echo "------------------------------"

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    info "Creando archivo .env..."
    cp .env.example .env
    success "Archivo .env creado"
else
    success "Archivo .env ya existe"
fi

# Instalar dependencias npm
if [ ! -d "node_modules" ]; then
    info "Instalando dependencias npm (esto puede tomar unos minutos)..."
    npm install
    if [ $? -eq 0 ]; then
        success "Dependencias npm instaladas"
    else
        error "Error instalando dependencias npm"
        exit 1
    fi
else
    success "node_modules ya existe"
fi

echo ""
echo "=========================================="
echo "✅ ¡CONFIGURACIÓN COMPLETADA!"
echo "=========================================="
echo ""
echo "Para iniciar el sistema, abre 2 terminales:"
echo ""
echo "📍 TERMINAL 1 - Backend:"
echo "  cd /workspaces/spark-template/backend"
echo "  source venv/bin/activate"
echo "  python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📍 TERMINAL 2 - Frontend:"
echo "  cd /workspaces/spark-template"
echo "  npm run dev"
echo ""
echo "🌐 URLs:"
echo "  Frontend: http://localhost:5173"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "💡 O usa los scripts rápidos:"
echo "  ./start-backend.sh   (Terminal 1)"
echo "  ./start-frontend.sh  (Terminal 2)"
echo ""
