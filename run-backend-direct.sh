#!/bin/bash

# Script directo sin depender de venv existente

echo "🚀 Iniciando Backend (modo directo)..."
echo ""

cd /workspaces/spark-template/backend

# Verificar si venv existe
if [ ! -d "venv" ]; then
    echo "❌ Entorno virtual no encontrado"
    echo ""
    echo "Ejecuta primero:"
    echo "  bash /workspaces/spark-template/setup-backend.sh"
    echo ""
    exit 1
fi

# Verificar si activate existe
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ venv/bin/activate no encontrado"
    echo "El entorno virtual está corrupto"
    echo ""
    echo "Ejecuta:"
    echo "  bash /workspaces/spark-template/setup-backend.sh"
    echo ""
    exit 1
fi

# Activar entorno virtual
echo "⚡ Activando entorno virtual..."
source venv/bin/activate

# Verificar que se activó correctamente
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Error: No se pudo activar el entorno virtual"
    exit 1
fi

echo "✅ Entorno virtual activado: $VIRTUAL_ENV"
echo ""

# Verificar uvicorn
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "⚠️  uvicorn no encontrado, instalando dependencias..."
    pip install -r requirements.txt
fi

# Iniciar servidor
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Iniciando servidor en http://localhost:8000"
echo "📚 Documentación API: http://localhost:8000/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Presiona Ctrl+C para detener"
echo ""

python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
