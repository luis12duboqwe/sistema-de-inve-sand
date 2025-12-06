#!/bin/bash
# Script de prueba simple

echo "================================"
echo "🧪 PRUEBA RÁPIDA DEL SISTEMA"
echo "================================"
echo ""

# Verificar herramientas
echo "1. Verificando herramientas..."
echo -n "  Node.js: "
node --version 2>/dev/null || echo "❌ NO INSTALADO"

echo -n "  npm: "
npm --version 2>/dev/null || echo "❌ NO INSTALADO"

echo -n "  Python: "
python3 --version 2>/dev/null || echo "❌ NO INSTALADO"

echo -n "  pip: "
pip3 --version 2>/dev/null || echo "❌ NO INSTALADO"

echo ""
echo "2. Verificando archivos..."
[ -f "package.json" ] && echo "  ✓ package.json" || echo "  ✗ package.json"
[ -f "vite.config.ts" ] && echo "  ✓ vite.config.ts" || echo "  ✗ vite.config.ts"
[ -d "src" ] && echo "  ✓ src/" || echo "  ✗ src/"
[ -d "backend" ] && echo "  ✓ backend/" || echo "  ✗ backend/"
[ -f "backend/requirements.txt" ] && echo "  ✓ backend/requirements.txt" || echo "  ✗ backend/requirements.txt"
[ -f "backend/app/main.py" ] && echo "  ✓ backend/app/main.py" || echo "  ✗ backend/app/main.py"

echo ""
echo "3. Verificando dependencias..."
if [ -d "node_modules" ]; then
    echo "  ✓ node_modules instalado"
else
    echo "  ⚠ node_modules no encontrado"
    echo "    Ejecuta: npm install"
fi

echo ""
echo "================================"
echo "✅ VERIFICACIÓN COMPLETADA"
echo "================================"
echo ""
echo "Para iniciar el sistema:"
echo "  Backend:  ./start-backend.sh"
echo "  Frontend: ./start-frontend.sh"
echo ""
