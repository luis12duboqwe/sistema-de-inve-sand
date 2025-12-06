#!/bin/bash

# Script de inicio rápido del frontend

echo "🚀 Iniciando Frontend..."
echo ""

# Verificar Node
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js no está instalado"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm no está instalado"
    exit 1
fi

# Verificar si existen node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Error al instalar dependencias"
        exit 1
    fi
else
    echo "✅ Dependencias ya instaladas"
fi

# Iniciar servidor de desarrollo
echo ""
echo "✅ Todo listo! Iniciando servidor de desarrollo..."
echo "🌐 URL: http://localhost:5173"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo ""

npm run dev
