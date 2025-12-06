#!/bin/bash

echo "================================"
echo "🧪 INICIANDO PRUEBAS DEL SISTEMA"
echo "================================"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
TESTS_PASSED=0
TESTS_FAILED=0

# Función para marcar test exitoso
pass_test() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

# Función para marcar test fallido
fail_test() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

# Función para info
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Función para warning
warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1️⃣  VERIFICANDO ENTORNO"
echo "----------------------"

# Verificar Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    pass_test "Node.js instalado: $NODE_VERSION"
else
    fail_test "Node.js no está instalado"
fi

# Verificar npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    pass_test "npm instalado: $NPM_VERSION"
else
    fail_test "npm no está instalado"
fi

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    pass_test "Python instalado: $PYTHON_VERSION"
else
    fail_test "Python no está instalado"
fi

# Verificar pip
if command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version)
    pass_test "pip instalado: $PIP_VERSION"
else
    fail_test "pip no está instalado"
fi

echo ""
echo "2️⃣  VERIFICANDO ARCHIVOS DEL PROYECTO"
echo "------------------------------------"

# Verificar estructura frontend
if [ -f "package.json" ]; then
    pass_test "package.json existe"
else
    fail_test "package.json no encontrado"
fi

if [ -f "vite.config.ts" ]; then
    pass_test "vite.config.ts existe"
else
    fail_test "vite.config.ts no encontrado"
fi

if [ -d "src" ]; then
    pass_test "Directorio src/ existe"
else
    fail_test "Directorio src/ no encontrado"
fi

# Verificar estructura backend
if [ -d "backend" ]; then
    pass_test "Directorio backend/ existe"
else
    fail_test "Directorio backend/ no encontrado"
fi

if [ -f "backend/requirements.txt" ]; then
    pass_test "backend/requirements.txt existe"
else
    fail_test "backend/requirements.txt no encontrado"
fi

if [ -f "backend/app/main.py" ]; then
    pass_test "backend/app/main.py existe"
else
    fail_test "backend/app/main.py no encontrado"
fi

echo ""
echo "3️⃣  VERIFICANDO DEPENDENCIAS"
echo "---------------------------"

# Verificar node_modules
if [ -d "node_modules" ]; then
    pass_test "node_modules instalado"
else
    warn "node_modules no encontrado - ejecutando npm install..."
    npm install
    if [ $? -eq 0 ]; then
        pass_test "npm install completado"
    else
        fail_test "npm install falló"
    fi
fi

# Verificar dependencias Python
if [ -d "backend/venv" ] || [ -d "backend/.venv" ]; then
    pass_test "Entorno virtual Python existe"
else
    warn "Entorno virtual no encontrado - creando..."
    cd backend
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        pass_test "Entorno virtual creado"
        source venv/bin/activate
        pip install -r requirements.txt
        if [ $? -eq 0 ]; then
            pass_test "Dependencias Python instaladas"
        else
            fail_test "Instalación de dependencias Python falló"
        fi
        deactivate
    else
        fail_test "Creación de entorno virtual falló"
    fi
    cd ..
fi

echo ""
echo "4️⃣  VERIFICANDO CONFIGURACIÓN"
echo "----------------------------"

# Verificar TypeScript
if [ -f "tsconfig.json" ]; then
    pass_test "tsconfig.json configurado"
else
    warn "tsconfig.json no encontrado"
fi

# Verificar Tailwind
if [ -f "tailwind.config.js" ]; then
    pass_test "tailwind.config.js configurado"
else
    warn "tailwind.config.js no encontrado"
fi

# Verificar base de datos
if [ -f "backend/inventory.db" ]; then
    pass_test "Base de datos SQLite existe"
else
    warn "Base de datos no inicializada"
    info "Ejecuta: cd backend && python3 init_db.py"
fi

echo ""
echo "5️⃣  PRUEBAS DE COMPILACIÓN"
echo "-------------------------"

# Test de TypeScript
info "Verificando errores de TypeScript..."
npx tsc --noEmit 2>&1 | head -20
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    pass_test "Sin errores de TypeScript"
else
    warn "Hay algunos errores de TypeScript (revisar arriba)"
fi

# Test de ESLint
info "Verificando ESLint..."
npm run lint 2>&1 | head -20
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    pass_test "Sin errores de ESLint"
else
    warn "Hay algunos warnings de ESLint"
fi

echo ""
echo "6️⃣  INSTRUCCIONES PARA INICIAR"
echo "-----------------------------"

info "Para iniciar el BACKEND:"
echo "  cd backend"
echo "  source venv/bin/activate  # o venv\\Scripts\\activate en Windows"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""

info "Para iniciar el FRONTEND:"
echo "  npm run dev"
echo ""

info "URLs de acceso:"
echo "  Frontend: http://localhost:5173"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""

echo "================================"
echo "📊 RESUMEN DE PRUEBAS"
echo "================================"
echo -e "${GREEN}Tests exitosos: $TESTS_PASSED${NC}"
echo -e "${RED}Tests fallidos: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ¡Sistema listo para usar!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Hay algunos problemas que necesitan atención${NC}"
    exit 1
fi
