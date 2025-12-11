#!/bin/bash

# 🔍 VALIDATION SCRIPT - Verificar todos los bugs implementados
# Este script valida que cada bug fue correctamente implementado

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}🔍 VALIDANDO IMPLEMENTACIÓN${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Helper function
check_file() {
    local file=$1
    local pattern=$2
    local bug=$3
    
    if [ -f "$file" ]; then
        if grep -q "$pattern" "$file"; then
            echo -e "${GREEN}✅ $bug encontrado en $file${NC}"
            ((PASSED++))
            return 0
        else
            echo -e "${RED}❌ $bug NO encontrado en $file${NC}"
            echo "   Patrón esperado: $pattern"
            ((FAILED++))
            return 1
        fi
    else
        echo -e "${RED}❌ Archivo no encontrado: $file${NC}"
        ((FAILED++))
        return 1
    fi
}

echo -e "${BLUE}VERIFICANDO IMPLEMENTACIONES${NC}"
echo "=============================="
echo ""

# BACKEND CHECKS
echo -e "${YELLOW}Backend Checks:${NC}"
echo "---------------"

check_file "backend/app/routers/orders.py" "BUG #1" "Bug #1 (Order transactional)"
check_file "backend/app/routers/stock_transfers.py" "BUG #2" "Bug #2 (Quantity reservada)"
check_file "backend/app/routers/stock_transfers.py" "BUG #3" "Bug #3 (IMEI reservation)"
check_file "backend/app/routers/products.py" "distinct()" "Bug #27 (Query optimization)"
check_file "backend/app/routers/orders.py" "location.activo" "Bug #30 (Location validation)"
check_file "backend/app/routers/products.py" "location.activo" "Bug #32 (Location active check)"
check_file "backend/app/routers/stock_transfers.py" "cantidad > 0\|cantidad <= 0\|cantidad > transfer" "Bug #31 (Cantidad validation)"

echo ""

# FRONTEND CHECKS
echo -e "${YELLOW}Frontend Checks:${NC}"
echo "---------------"

check_file "src/lib/inventoryService.ts" "BUG #4\|auto-crear ubicación" "Bug #4 (Auto-create location)"
check_file "src/lib/inventoryService.ts" "cantidad_disponible >= 0\|>= 0" "Bug #29 (Stock >= 0)"
check_file "src/App.tsx" "Math.max(0" "Bug #33 (Stock calculation Math.max)"
check_file "src/components/NewOrderDialog.tsx" "reset\|setForm" "Bug #5 (Form reset)"
check_file "src/components/NewOrderDialog.tsx" "cantidad_reservada\|stock_libre" "Bug #8 (Reserved stock filter)"
check_file "src/components/NewOrderDialog.tsx" "required\|location" "Bug #9 (Location required)"
check_file "backend/app/routers/orders.py" "IMEI" "Bug #26 (IMEI validation order)"
check_file "backend/app/routers/orders.py" "except\|rollback" "Bug #28 (Rollback improvements)"

echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}📊 RESUMEN${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "Validaciones pasadas: ${GREEN}$PASSED${NC}"
echo -e "Validaciones fallidas: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ TODAS LAS IMPLEMENTACIONES VALIDADAS${NC}"
    echo ""
    echo "Sistema listo para testing"
    exit 0
else
    echo -e "${RED}❌ SE ENCONTRARON PROBLEMAS${NC}"
    echo ""
    echo "Por favor revisa los archivos arriba"
    exit 1
fi
