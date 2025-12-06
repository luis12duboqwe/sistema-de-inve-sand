#!/bin/bash

# Script de ejecución de pruebas para Dev Container
# Este script se ejecuta dentro del Dev Container de VSCode

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  🧪 EJECUTANDO PRUEBAS DEL SISTEMA - DEV CONTAINER                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

# Función para test exitoso
pass_test() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

# Función para test fallido
fail_test() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

# Función para info
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "1️⃣  VERIFICANDO ENTORNO DEV CONTAINER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verificar herramientas
if command -v node &> /dev/null; then
    pass_test "Node.js: $(node --version)"
else
    fail_test "Node.js no encontrado"
fi

if command -v npm &> /dev/null; then
    pass_test "npm: $(npm --version)"
else
    fail_test "npm no encontrado"
fi

if command -v python3 &> /dev/null; then
    pass_test "Python: $(python3 --version)"
else
    fail_test "Python no encontrado"
fi

if command -v pip3 &> /dev/null; then
    pass_test "pip: $(pip3 --version | head -1)"
else
    fail_test "pip no encontrado"
fi

echo ""
echo "2️⃣  VERIFICANDO ESTRUCTURA DEL PROYECTO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Frontend
[ -f "package.json" ] && pass_test "package.json" || fail_test "package.json"
[ -f "vite.config.ts" ] && pass_test "vite.config.ts" || fail_test "vite.config.ts"
[ -d "src" ] && pass_test "Directorio src/" || fail_test "Directorio src/"
[ -f "src/App.tsx" ] && pass_test "src/App.tsx" || fail_test "src/App.tsx"

# Backend
[ -d "backend" ] && pass_test "Directorio backend/" || fail_test "Directorio backend/"
[ -f "backend/requirements.txt" ] && pass_test "requirements.txt" || fail_test "requirements.txt"
[ -f "backend/app/main.py" ] && pass_test "app/main.py" || fail_test "app/main.py"

echo ""
echo "3️⃣  VERIFICANDO DEPENDENCIAS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Frontend dependencies
if [ -d "node_modules" ]; then
    pass_test "node_modules instalado"
else
    info "Instalando dependencias del frontend..."
    npm install &> /dev/null
    if [ $? -eq 0 ]; then
        pass_test "Dependencias frontend instaladas"
    else
        fail_test "Error instalando dependencias frontend"
    fi
fi

# Backend dependencies
if [ -d "backend/venv" ]; then
    pass_test "Entorno virtual Python existe"
else
    info "Creando entorno virtual Python..."
    cd backend
    python3 -m venv venv &> /dev/null
    if [ $? -eq 0 ]; then
        pass_test "Entorno virtual creado"
    else
        fail_test "Error creando entorno virtual"
    fi
    cd ..
fi

echo ""
echo "4️⃣  VERIFICANDO CONFIGURACIÓN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[ -f "tsconfig.json" ] && pass_test "TypeScript configurado" || fail_test "tsconfig.json"
[ -f "tailwind.config.js" ] && pass_test "Tailwind configurado" || fail_test "tailwind.config.js"

# Verificar BD
if [ -f "backend/inventory.db" ]; then
    pass_test "Base de datos existe"
else
    info "Base de datos será creada al iniciar el backend"
fi

echo ""
echo "5️⃣  SCRIPTS DISPONIBLES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[ -f "start-backend.sh" ] && pass_test "start-backend.sh" || fail_test "start-backend.sh"
[ -f "start-frontend.sh" ] && pass_test "start-frontend.sh" || fail_test "start-frontend.sh"
[ -f "test-backend.py" ] && pass_test "test-backend.py" || fail_test "test-backend.py"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  📊 RESUMEN"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${GREEN}Tests exitosos: $TESTS_PASSED${NC}"
echo -e "${RED}Tests fallidos: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ¡Sistema listo para iniciar!${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "PRÓXIMOS PASOS:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1️⃣  Dar permisos a los scripts:"
    echo "    chmod +x start-backend.sh start-frontend.sh"
    echo ""
    echo "2️⃣  Iniciar Backend (Terminal 1):"
    echo "    ./start-backend.sh"
    echo "    → Backend estará en: http://localhost:8000"
    echo "    → API Docs en: http://localhost:8000/docs"
    echo ""
    echo "3️⃣  Iniciar Frontend (Terminal 2):"
    echo "    ./start-frontend.sh"
    echo "    → Frontend estará en: http://localhost:5173"
    echo ""
    echo "4️⃣  Probar la API (Terminal 3, después de iniciar backend):"
    echo "    pip install requests"
    echo "    python3 test-backend.py"
    echo ""
    echo "5️⃣  Abrir en navegador:"
    echo "    http://localhost:5173"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📚 DOCUMENTACIÓN:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  • VISUAL_TEST_GUIDE.txt  - Guía visual completa"
    echo "  • TESTING_GUIDE.md       - Checklist de pruebas"
    echo "  • QUICK_TEST.md          - Comandos rápidos"
    echo "  • SYSTEM_STATUS_REPORT.txt - Estado del sistema"
    echo ""
else
    echo -e "${YELLOW}⚠️  Hay algunos problemas que resolver${NC}"
    echo ""
    echo "Revisa los errores arriba y:"
    echo "  • Instala las herramientas faltantes"
    echo "  • Verifica la estructura de archivos"
    echo "  • Ejecuta: npm install"
    echo ""
fi
