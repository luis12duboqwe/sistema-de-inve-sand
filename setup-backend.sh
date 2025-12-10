#!/bin/bash

echo "🔧 Configurando Backend desde cero..."
echo ""

# Ir al directorio backend
cd /workspaces/spark-template/backend

# Verificar Python
echo "1️⃣  Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION encontrado"
echo ""

# Eliminar entorno virtual antiguo si existe y está corrupto
if [ -d "venv" ]; then
    echo "🗑️  Eliminando entorno virtual anterior..."
    rm -rf venv
fi

# Crear nuevo entorno virtual
echo "2️⃣  Creando entorno virtual..."
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo "❌ Error: No se pudo crear el directorio venv"
    exit 1
fi

if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Error: venv/bin/activate no existe"
    echo "Contenido de venv:"
    ls -la venv/
    exit 1
fi

echo "✅ Entorno virtual creado"
echo ""

# Activar entorno virtual
echo "3️⃣  Activando entorno virtual..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Error al activar entorno virtual"
    exit 1
fi

echo "✅ Entorno virtual activado"
echo ""

# Verificar pip
echo "4️⃣  Verificando pip..."
python -m pip --version
echo ""

# Actualizar pip
echo "5️⃣  Actualizando pip..."
python -m pip install --upgrade pip
echo ""

# Instalar dependencias
echo "6️⃣  Instalando dependencias de requirements.txt..."
echo "   Esto puede tomar unos minutos..."
echo ""
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar dependencias"
    exit 1
fi

echo ""
echo "✅ Todas las dependencias instaladas"
echo ""

# Verificar instalación de paquetes clave
echo "7️⃣  Verificando paquetes instalados..."
python -c "import fastapi; print('✅ FastAPI:', fastapi.__version__)"
python -c "import sqlalchemy; print('✅ SQLAlchemy:', sqlalchemy.__version__)"
python -c "import uvicorn; print('✅ Uvicorn:', uvicorn.__version__)"
echo ""

# Inicializar base de datos
echo "8️⃣  Inicializando base de datos..."
python init_db.py

if [ $? -eq 0 ]; then
    echo "✅ Base de datos inicializada"
else
    echo "⚠️  Error al inicializar BD (se creará automáticamente al iniciar)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 ¡BACKEND CONFIGURADO EXITOSAMENTE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Para iniciar el backend ejecuta:"
echo "  bash /workspaces/spark-template/start-backend.sh"
echo ""
echo "O manualmente:"
echo "  cd /workspaces/spark-template/backend"
echo "  source venv/bin/activate"
echo "  python -m uvicorn app.main:app --reload --port 8000"
echo ""

deactivate
