#!/bin/bash

# Script para limpiar y recrear el entorno virtual de Python
# Resuelve problemas de permisos en el venv

echo "════════════════════════════════════════════════════════════"
echo "🔧 LIMPIEZA Y CONFIGURACIÓN DEL ENTORNO VIRTUAL"
echo "════════════════════════════════════════════════════════════"
echo ""

# Ir al directorio del backend
cd backend

# 1. Limpiar venv anterior
if [ -d "venv" ]; then
    echo "🗑️  Eliminando entorno virtual antiguo..."
    rm -rf venv
    echo "✅ Entorno virtual eliminado"
else
    echo "ℹ️  No hay entorno virtual anterior"
fi

echo ""

# 2. Crear nuevo venv
echo "📦 Creando nuevo entorno virtual..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Error al crear entorno virtual"
    exit 1
fi

echo "✅ Entorno virtual creado"
echo ""

# 3. Activar venv
echo "⚡ Activando entorno virtual..."
source venv/bin/activate

# 4. Actualizar pip
echo "🔄 Actualizando pip..."
python -m pip install --upgrade pip -q

# 5. Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -q -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error al instalar dependencias"
    deactivate
    exit 1
fi

echo "✅ Dependencias instaladas"
echo ""

# 6. Inicializar base de datos
echo "🗄️  Inicializando base de datos..."
python init_db.py --with-data

if [ $? -ne 0 ]; then
    echo "⚠️  Advertencia: Hubo un problema inicializando la BD"
else
    echo "✅ Base de datos inicializada"
fi

echo ""

# Desactivar venv
deactivate

echo "════════════════════════════════════════════════════════════"
echo "✅ CONFIGURACIÓN COMPLETADA"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Ahora puedes ejecutar:"
echo "  ./start-backend.sh   - Iniciar el backend"
echo "  ./start-frontend.sh  - Iniciar el frontend"
echo ""
