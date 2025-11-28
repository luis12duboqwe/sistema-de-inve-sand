#!/bin/bash

echo "🚀 Iniciando Sistema de Inventario API"
echo "========================================"
echo ""

if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

echo "🔧 Activando entorno virtual..."
source venv/bin/activate

echo "📥 Instalando dependencias..."
pip install -r requirements.txt

echo ""
echo "✅ Instalación completa"
echo ""
echo "🌐 Iniciando servidor..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "💡 Para inicializar datos de ejemplo:"
echo "   curl -X POST http://localhost:8000/api/init-data"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
