#!/bin/bash

# Script para iniciar el backend en GitHub Codespaces
# Configura CORS apropiadamente para Codespaces

set -e

echo "🚀 Iniciando backend en GitHub Codespaces..."

cd /workspaces/spark-template/backend

# Activar venv si existe
if [ -d "venv" ]; then
    echo "✅ Activando venv..."
    source venv/bin/activate
else
    echo "❌ venv no encontrado. Ejecuta: bash setup-complete.sh"
    exit 1
fi

# Verificar que los paquetes estén instalados
echo "📦 Verificando dependencias..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Instalando dependencias..."
    pip install -q -r requirements.txt
fi

# Inicializar DB si no existe
if [ ! -f "inventory.db" ]; then
    echo "🗄️  Inicializando base de datos..."
    python3 init_db.py --with-data
fi

# Importante: En Codespaces, uvicorn debe escuchar en 0.0.0.0
# y CORS debe permitir todas las origins (ya configurado en config.py)
echo ""
echo "=========================================="
echo "Backend corriendo en Codespaces"
echo "=========================================="
echo ""
echo "El servidor escucha en 0.0.0.0:8000"
echo "Documentación: http://localhost:8000/docs"
echo ""

# Iniciar servidor sin --reload en producción
# --reload puede causar problemas en Codespaces
uvicorn app.main:app --host 0.0.0.0 --port 8000 --access-log
