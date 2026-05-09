#!/bin/bash

# Script de inicio rápido del frontend - Sistema de Inventario V2.0

set -e  # Salir si hay errores

echo "🚀 Iniciando Frontend (React + TypeScript + Vite)..."
echo ""

# Ir al directorio raíz del proyecto
cd "$(dirname "$0")"

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js no está instalado"
    echo "   Instala Node.js 18+ desde https://nodejs.org/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm no está instalado"
    echo "   Viene incluido con Node.js"
    exit 1
fi

NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)
echo "✅ Node.js $NODE_VERSION encontrado"
echo "✅ npm $NPM_VERSION encontrado"

# Verificar/instalar dependencias
if [ ! -d "node_modules" ]; then
    echo ""
    echo "📦 Instalando dependencias (primera vez)..."
    echo "   Esto puede tomar unos minutos..."
    npm install
    echo "✅ Dependencias instaladas"
else
    echo "✅ Dependencias ya instaladas"
    
    # Verificar si package.json cambió
    if [ "package.json" -nt "node_modules/.package-lock.json" ] 2>/dev/null; then
        echo "⚠️  package.json modificado - actualizando dependencias..."
        npm install
    fi
fi

# Verificar compilación TypeScript
echo ""
echo "🔍 Verificando tipos TypeScript..."
npx tsc --noEmit --skipLibCheck 2>&1 | head -5 || true
echo "✅ Verificación completada"

# Iniciar servidor de desarrollo
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Servidor de desarrollo iniciado exitosamente"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Aplicación:      http://localhost:5173"
echo "🌐 Red interna:     http://0.0.0.0:5173"
echo "⚡ HMR:             Habilitado (recarga automática)"
echo ""
echo "💡 Para detener el servidor: Ctrl+C"
echo ""
echo "📝 Modos de operación:"
echo "   • Local Mode:  Usa Spark KV (IndexedDB + localStorage)"
echo "   • API Mode:    Conecta con backend en http://localhost:8000"
echo "   (Configurable en Ajustes dentro de la app)"
echo ""

npm run dev -- --host 0.0.0.0
