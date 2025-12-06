#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║  🧪 PROBANDO EL SISTEMA COMPLETO                                    ║"
echo "║                                                                      ║"
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

pass_test() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1️⃣  VERIFICANDO ESTRUCTURA DEL PROYECTO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Frontend
[ -f "package.json" ] && pass_test "package.json existe" || fail_test "package.json no encontrado"
[ -f "vite.config.ts" ] && pass_test "vite.config.ts existe" || fail_test "vite.config.ts no encontrado"
[ -d "src" ] && pass_test "Directorio src/ existe" || fail_test "Directorio src/ no encontrado"
[ -f "src/App.tsx" ] && pass_test "src/App.tsx existe" || fail_test "src/App.tsx no encontrado"

# Backend
[ -d "backend" ] && pass_test "Directorio backend/ existe" || fail_test "Directorio backend/ no encontrado"
[ -f "backend/requirements.txt" ] && pass_test "backend/requirements.txt existe" || fail_test "backend/requirements.txt no encontrado"
[ -f "backend/app/main.py" ] && pass_test "backend/app/main.py existe" || fail_test "backend/app/main.py no encontrado"
[ -f "backend/init_db.py" ] && pass_test "backend/init_db.py existe" || fail_test "backend/init_db.py no encontrado"

echo ""
echo "2️⃣  VERIFICANDO DEPENDENCIAS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Node modules
if [ -d "node_modules" ]; then
    pass_test "node_modules instalado ($(du -sh node_modules 2>/dev/null | cut -f1))"
else
    warn "node_modules no encontrado - ejecuta: npm install"
fi

# Python venv
if [ -d "backend/venv" ] || [ -d "backend/.venv" ]; then
    pass_test "Entorno virtual Python existe"
else
    warn "Entorno virtual no encontrado - ejecuta: cd backend && python3 -m venv venv"
fi

echo ""
echo "3️⃣  VERIFICANDO ARCHIVOS DE CONFIGURACIÓN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[ -f "tsconfig.json" ] && pass_test "tsconfig.json configurado" || warn "tsconfig.json no encontrado"
[ -f "tailwind.config.js" ] && pass_test "tailwind.config.js configurado" || warn "tailwind.config.js no encontrado"
[ -f "eslint.config.js" ] && pass_test "eslint.config.js configurado" || warn "eslint.config.js no encontrado"

echo ""
echo "4️⃣  VERIFICANDO SCRIPTS DE INICIO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[ -f "start-backend.sh" ] && pass_test "start-backend.sh existe" || fail_test "start-backend.sh no encontrado"
[ -f "start-frontend.sh" ] && pass_test "start-frontend.sh existe" || fail_test "start-frontend.sh no encontrado"
[ -f "test-system.sh" ] && pass_test "test-system.sh existe" || fail_test "test-system.sh no encontrado"

# Verificar permisos
if [ -x "start-backend.sh" ]; then
    pass_test "start-backend.sh tiene permisos de ejecución"
else
    warn "start-backend.sh necesita permisos: chmod +x start-backend.sh"
fi

echo ""
echo "5️⃣  VERIFICANDO HERRAMIENTAS DEL SISTEMA"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    pass_test "Node.js instalado: $NODE_VERSION"
else
    fail_test "Node.js no está instalado"
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    pass_test "npm instalado: v$NPM_VERSION"
else
    fail_test "npm no está instalado"
fi

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    pass_test "Python instalado: $PYTHON_VERSION"
else
    fail_test "Python no está instalado"
fi

if command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version | cut -d' ' -f2)
    pass_test "pip instalado: v$PIP_VERSION"
else
    fail_test "pip no está instalado"
fi

echo ""
echo "6️⃣  VERIFICANDO COMPONENTES PRINCIPALES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Contar archivos importantes
COMPONENTS_COUNT=$(find src/components -name "*.tsx" 2>/dev/null | wc -l)
if [ "$COMPONENTS_COUNT" -gt 0 ]; then
    pass_test "Componentes React: $COMPONENTS_COUNT archivos"
else
    warn "No se encontraron componentes React"
fi

HOOKS_COUNT=$(find src/hooks -name "*.ts" -o -name "*.tsx" 2>/dev/null | wc -l)
if [ "$HOOKS_COUNT" -gt 0 ]; then
    pass_test "Custom Hooks: $HOOKS_COUNT archivos"
else
    warn "No se encontraron hooks personalizados"
fi

echo ""
echo "7️⃣  CONTANDO LÍNEAS DE CÓDIGO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Frontend
FRONTEND_LINES=$(find src -name "*.tsx" -o -name "*.ts" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
if [ ! -z "$FRONTEND_LINES" ] && [ "$FRONTEND_LINES" != "0" ]; then
    info "Frontend (TypeScript/React): $FRONTEND_LINES líneas"
fi

# Backend
BACKEND_LINES=$(find backend/app -name "*.py" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
if [ ! -z "$BACKEND_LINES" ] && [ "$BACKEND_LINES" != "0" ]; then
    info "Backend (Python): $BACKEND_LINES líneas"
fi

echo ""
echo "8️⃣  VERIFICANDO BASE DE DATOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "backend/inventory.db" ]; then
    DB_SIZE=$(du -h backend/inventory.db 2>/dev/null | cut -f1)
    pass_test "Base de datos SQLite existe ($DB_SIZE)"
else
    warn "Base de datos no inicializada - se creará al iniciar el backend"
fi

echo ""
echo "9️⃣  VERIFICANDO DOCUMENTACIÓN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[ -f "README.md" ] && pass_test "README.md" || warn "README.md no encontrado"
[ -f "TESTING_GUIDE.md" ] && pass_test "TESTING_GUIDE.md" || warn "TESTING_GUIDE.md no encontrado"
[ -f "INTEGRATION.md" ] && pass_test "INTEGRATION.md" || warn "INTEGRATION.md no encontrado"
[ -f "SECURITY.md" ] && pass_test "SECURITY.md" || warn "SECURITY.md no encontrado"

echo ""
echo "🔟 VERIFICANDO SI LOS SERVICIOS ESTÁN CORRIENDO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verificar backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
    pass_test "Backend está corriendo en puerto 8000"
    info "Respuesta: $HEALTH_RESPONSE"
else
    warn "Backend NO está corriendo en puerto 8000"
    info "Inicia con: ./start-backend.sh"
fi

# Verificar frontend
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    pass_test "Frontend está corriendo en puerto 5173"
else
    warn "Frontend NO está corriendo en puerto 5173"
    info "Inicia con: ./start-frontend.sh"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  📊 RESUMEN DE LA VERIFICACIÓN"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${GREEN}Tests exitosos: $TESTS_PASSED${NC}"
echo -e "${RED}Tests fallidos: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ¡Sistema verificado correctamente!${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "SIGUIENTE PASO:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Verificar si los servicios están corriendo
    BACKEND_RUNNING=$(curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "yes" || echo "no")
    FRONTEND_RUNNING=$(curl -s http://localhost:5173 > /dev/null 2>&1 && echo "yes" || echo "no")
    
    if [ "$BACKEND_RUNNING" = "no" ] || [ "$FRONTEND_RUNNING" = "no" ]; then
        echo "Para iniciar el sistema:"
        echo ""
        if [ "$BACKEND_RUNNING" = "no" ]; then
            echo "  Terminal 1 - Backend:"
            echo "    ./start-backend.sh"
            echo ""
        fi
        if [ "$FRONTEND_RUNNING" = "no" ]; then
            echo "  Terminal 2 - Frontend:"
            echo "    ./start-frontend.sh"
            echo ""
        fi
        echo "Luego abre en navegador: http://localhost:5173"
    else
        echo -e "${GREEN}✅ Backend y Frontend ya están corriendo!${NC}"
        echo ""
        echo "🌐 Abre en navegador: http://localhost:5173"
        echo "📚 Documentación API: http://localhost:8000/docs"
    fi
else
    echo -e "${YELLOW}⚠️  Hay algunos problemas que necesitan atención${NC}"
    echo ""
    echo "Revisa los errores arriba y:"
    echo "  • Instala las herramientas faltantes"
    echo "  • Ejecuta: npm install"
    echo "  • Verifica la estructura de archivos"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 Documentación disponible:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • START_HERE.txt        - Instrucciones rápidas"
echo "  • TESTING_GUIDE.md      - Guía completa de pruebas"
echo "  • SYSTEM_STATUS_REPORT.txt - Estado del sistema"
echo "  • VISUAL_TEST_GUIDE.txt - Guía visual paso a paso"
echo ""
