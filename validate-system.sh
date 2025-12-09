#!/bin/bash
# System validation script - Verify everything is ready

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🔍 VALIDACIÓN DEL SISTEMA                               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python
echo "1️⃣  Verificando Python..."
if command -v python3 &> /dev/null; then
    VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo "   ✅ Python $VERSION"
else
    echo "   ❌ Python3 no encontrado"
fi

# Check Node
echo "2️⃣  Verificando Node.js..."
if command -v node &> /dev/null; then
    VERSION=$(node --version 2>&1)
    echo "   ✅ Node $VERSION"
else
    echo "   ❌ Node.js no encontrado"
fi

# Check npm
echo "3️⃣  Verificando npm..."
if command -v npm &> /dev/null; then
    VERSION=$(npm --version 2>&1)
    echo "   ✅ npm $VERSION"
else
    echo "   ❌ npm no encontrado"
fi

# Check Backend files
echo "4️⃣  Verificando archivos del backend..."
if [ -f "backend/requirements.txt" ]; then
    echo "   ✅ requirements.txt existe"
else
    echo "   ❌ requirements.txt no encontrado"
fi

if [ -f "backend/app/main.py" ]; then
    echo "   ✅ app/main.py existe"
else
    echo "   ❌ app/main.py no encontrado"
fi

# Check Frontend files
echo "5️⃣  Verificando archivos del frontend..."
if [ -f "package.json" ]; then
    echo "   ✅ package.json existe"
else
    echo "   ❌ package.json no encontrado"
fi

if [ -f "src/App.tsx" ]; then
    echo "   ✅ src/App.tsx existe"
else
    echo "   ❌ src/App.tsx no encontrado"
fi

# Check Scripts
echo "6️⃣  Verificando scripts de inicio..."
for script in setup.sh start-backend.sh start-frontend.sh; do
    if [ -x "$script" ] 2>/dev/null; then
        echo "   ✅ $script (ejecutable)"
    elif [ -f "$script" ]; then
        echo "   ⚠️  $script (existe pero no es ejecutable)"
        echo "      Solución: chmod +x $script"
    else
        echo "   ❌ $script no encontrado"
    fi
done

# Check Database
echo "7️⃣  Verificando base de datos..."
if [ -f "backend/inventory.db" ]; then
    SIZE=$(du -h backend/inventory.db | cut -f1)
    echo "   ✅ BD existe ($SIZE)"
else
    echo "   ℹ️  BD no creada (se crea en primer run)"
fi

# Check Port availability
echo "8️⃣  Verificando puertos..."
if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "   ✅ Puerto 8000 disponible"
else
    echo "   ⚠️  Puerto 8000 ya en uso"
fi

if ! lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null ; then
    echo "   ✅ Puerto 5173 disponible"
else
    echo "   ⚠️  Puerto 5173 ya en uso"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ VALIDACIÓN COMPLETADA                                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo ""
echo "1. Ejecuta: bash setup.sh"
echo "2. Espera a que termine"
echo "3. Terminal 1: ./start-backend.sh"
echo "4. Terminal 2: ./start-frontend.sh"
echo "5. Abre: http://localhost:5173"
echo ""
