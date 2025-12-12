#!/bin/bash

# Script de inicio del backend desde el directorio backend/

echo "🚀 Iniciando Sistema de Inventario API V2.0"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    echo "✅ Entorno virtual creado"
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip silenciosamente
python -m pip install --upgrade pip -q 2>/dev/null || true

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -q -r requirements.txt

# Verificar base de datos
if [ ! -f "inventory.db" ]; then
    echo "🗄️  Inicializando base de datos vacía (V2.0)..."
    python init_db.py
    echo "✅ Base de datos inicializada"
fi

echo ""
echo "✅ Instalación completa"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Iniciando servidor..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   API REST:        http://localhost:8000"
echo "   Documentación:   http://localhost:8000/docs"
echo "   ReDoc:           http://localhost:8000/redoc"
echo ""
echo "💡 Para detener el servidor: Ctrl+C"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
