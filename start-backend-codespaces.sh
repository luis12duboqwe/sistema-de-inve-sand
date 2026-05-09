#!/bin/bash

# Script para iniciar el backend en GitHub Codespaces
# Configura CORS apropiadamente para Codespaces

set -e

echo "🚀 Iniciando backend en GitHub Codespaces..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ No se encontró el backend en: $BACKEND_DIR"
    exit 1
fi

cd "$BACKEND_DIR"

# Activar venv si existe (soporta venv y .venv)
if [ -d "venv" ]; then
    VENV_DIR="venv"
elif [ -d ".venv" ]; then
    VENV_DIR=".venv"
else
    echo "❌ Entorno virtual no encontrado. Ejecuta setup-complete.sh"
    exit 1
fi

echo "✅ Activando entorno virtual ($VENV_DIR)..."
source "$VENV_DIR/bin/activate"

# Verificar que los paquetes estén instalados
echo "📦 Verificando dependencias..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Instalando dependencias..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Preparar esquema de base de datos configurada en backend/.env
echo "🗄️  Verificando esquema de base de datos..."
python3 init_db.py

# Importante: En Codespaces, uvicorn debe escuchar en 0.0.0.0
# y CORS debe permitir todas las origins (ya configurado en config.py)
echo ""
echo "=========================================="
echo "Backend corriendo en Codespaces"
echo "=========================================="
echo ""
echo "El servidor escucha en 0.0.0.0:8000"
echo "Documentación: http://localhost:8000/docs"
echo "Directorio backend: $BACKEND_DIR"
echo ""

# Iniciar servidor sin --reload en producción
# --reload puede causar problemas en Codespaces
uvicorn app.main:app --host 0.0.0.0 --port 8000 --access-log
