#!/bin/bash
# Script de prueba para la funcionalidad de transferencia de stock

echo "🧪 Prueba de Transferencia de Stock Entre Perfiles"
echo "=================================================="
echo ""

# Variables de configuración
API_URL="${VITE_API_URL:-http://localhost:8000}"
BASE_URL="$API_URL/api"

echo "📍 API URL: $BASE_URL"
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir resultados
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# 1. Verificar que el backend esté corriendo
echo "1️⃣  Verificando conexión con backend..."
curl -s -f "$BASE_URL/../" > /dev/null 2>&1
print_result $? "Backend está corriendo"
echo ""

# 2. Listar perfiles disponibles
echo "2️⃣  Listando perfiles disponibles..."
PROFILES=$(curl -s "$BASE_URL/profiles")
echo "$PROFILES" | python3 -m json.tool 2>/dev/null || echo "Error al parsear JSON"
echo ""

# 3. Listar productos del primer perfil
echo "3️⃣  Listando productos disponibles..."
PRODUCTS=$(curl -s "$BASE_URL/products?per_page=3")
echo "$PRODUCTS" | python3 -m json.tool 2>/dev/null | head -40
echo ""

# 4. Verificar endpoint de transferencias
echo "4️⃣  Verificando endpoint de transferencias..."
curl -s -f "$BASE_URL/stock-transfers?page=1&per_page=10" > /dev/null 2>&1
print_result $? "Endpoint /api/stock-transfers está disponible"
echo ""

# 5. Listar transferencias existentes
echo "5️⃣  Listando transferencias existentes..."
TRANSFERS=$(curl -s "$BASE_URL/stock-transfers?per_page=5")
echo "$TRANSFERS" | python3 -m json.tool 2>/dev/null || echo "No hay transferencias aún"
echo ""

# Ejemplo de creación de transferencia (comentado por seguridad)
cat << 'EOF'

📝 Ejemplo de creación de transferencia:

curl -X POST "$BASE_URL/stock-transfers" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "from_profile_slug": "softmobile",
    "to_profile_slug": "hardmobile",
    "cantidad": 5,
    "notas": "Prueba de transferencia",
    "created_by": "Sistema"
  }'

Para ejecutar este ejemplo:
1. Verifica que tengas al menos 2 perfiles activos
2. Verifica que el producto exista y tenga stock suficiente
3. Ajusta los valores según tu base de datos
4. Ejecuta el comando curl

EOF

echo ""
echo "=================================================="
echo "✅ Prueba completada"
echo ""
echo "Para usar la funcionalidad en la UI:"
echo "1. Abre la aplicación frontend"
echo "2. Ve a la pestaña 'Productos'"
echo "3. Selecciona un perfil específico"
echo "4. Haz clic en el botón de transferencia (↔) en cualquier producto"
echo ""
