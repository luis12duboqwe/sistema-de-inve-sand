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

# Verificar configuración PostgreSQL
if [ -z "$DATABASE_URL" ] && [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL no está configurado"
    echo "   Este backend ahora funciona solo con PostgreSQL"
    exit 1
fi

case "$DATABASE_URL" in
  postgresql*) ;;
  *)
    echo "❌ Error: DATABASE_URL debe usar PostgreSQL"
    echo "   Valor actual: $DATABASE_URL"
    exit 1
    ;;
esac

echo "🗄️  Inicializando tablas en PostgreSQL..."
python init_db.py
echo "✅ Base de datos inicializada"

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
