#!/bin/bash

# Script de inicio rápido del backend

echo "🚀 Iniciando Backend..."
echo ""

cd backend

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado"
    exit 1
fi

# Verificar si existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Error al crear entorno virtual"
        exit 1
    fi
fi

# Activar entorno virtual
echo "⚡ Activando entorno virtual..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Error al activar entorno virtual"
    exit 1
fi

# Actualizar pip
echo "🔄 Actualizando pip..."
python -m pip install --upgrade pip -q

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar dependencias"
    deactivate
    exit 1
fi

# Inicializar base de datos si no existe
if [ ! -f "inventory.db" ]; then
    echo "🗄️  Inicializando base de datos..."
    python init_db.py
    if [ $? -ne 0 ]; then
        echo "⚠️  Advertencia: Error al inicializar BD (se creará automáticamente)"
    fi
fi

# Iniciar servidor
echo ""
echo "✅ Todo listo! Iniciando servidor en http://localhost:8000"
echo "📚 Documentación API: http://localhost:8000/docs"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo ""

python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
