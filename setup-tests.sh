#!/bin/bash

# Script para preparar el entorno de pruebas

echo "🔧 Preparando entorno de pruebas..."
echo ""

# Verificar si estamos en el directorio correcto
if [ ! -f "test-backend.py" ]; then
    echo "❌ Error: Ejecuta este script desde la raíz del proyecto"
    exit 1
fi

# Instalar requests en el entorno del backend
echo "📦 Instalando dependencias de testing en el backend..."
cd backend

if [ -d "venv" ]; then
    echo "✓ Usando entorno virtual existente"
    source venv/bin/activate
else
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
fi

echo "📥 Instalando requests..."
pip install -q requests

echo ""
echo "✅ ¡Listo! Ahora puedes ejecutar:"
echo ""
echo "   cd .."
echo "   python3 test-backend.py"
echo ""

deactivate
cd ..
