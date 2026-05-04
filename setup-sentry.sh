#!/bin/bash

# ============================================================================
# Sentry Setup Helper - Configurador interactivo para Sentry
# ============================================================================
# Uso: ./setup-sentry.sh
# ============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        SETUP Sentry - Error Tracking & Monitoring              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ============================================================================
# INFORMACIÓN SOBRE SENTRY
# ============================================================================
echo -e "${YELLOW}¿QUÉ ES SENTRY?${NC}"
echo ""
echo "Sentry es una plataforma para monitorear errores en producción."
echo "Automáticamente captura y reporta:"
echo "  - Excepciones no controladas"
echo "  - Errores en base de datos"
echo "  - Transacciones lentas"
echo "  - Cambios en performance"
echo ""
echo "Tier GRATUITO include:"
echo "  ✓ 5,000 errores/mes"
echo "  ✓ 1 proyecto"
echo "  ✓ Alertas básicas"
echo "  ✓ Integración con GitHub, Slack, etc."
echo ""

# ============================================================================
# PASO 1: VERIFICAR SI TIENES CUENTA
# ============================================================================
echo -e "${YELLOW}PASO 1: Verificar/Crear cuenta Sentry${NC}"
echo ""

read -p "¿Ya tienes cuenta en Sentry.io? (s/n): " -n 1 -r HAS_ACCOUNT
echo ""

if [[ ! $HAS_ACCOUNT =~ ^[Ss]$ ]]; then
    echo -e "${BLUE}Abre tu navegador y sigue estos pasos:${NC}"
    echo ""
    echo "  1. Ir a https://sentry.io"
    echo "  2. Click en 'Sign Up' (arriba a la derecha)"
    echo "  3. Registrarse con Email/GitHub/Google"
    echo "  4. Crear un proyecto:"
    echo "     - Platform: 'Python'"
    echo "     - Framework: 'FastAPI'"
    echo "  5. Copiar el DSN que aparece"
    echo ""
    echo "🔗 https://sentry.io"
    echo ""
    read -p "Presiona Enter cuando tengas tu DSN..."
fi

echo ""

# ============================================================================
# PASO 2: OBTENER EL DSN
# ============================================================================
echo -e "${YELLOW}PASO 2: Proporcionar Sentry DSN${NC}"
echo ""
echo "El DSN se ve como:"
echo -e "${PURPLE}https://xxxxxxxxxxxxxxxx@oxxxxxxxx.ingest.sentry.io/xxxxxx${NC}"
echo ""

read -p "Pega tu DSN aquí: " SENTRY_DSN

if [[ -z "$SENTRY_DSN" ]]; then
    echo -e "${RED}❌ DSN vacío, configuración cancelada${NC}"
    exit 1
fi

# Validar formato básico
if [[ ! "$SENTRY_DSN" =~ ^https:// ]]; then
    echo -e "${RED}❌ DSN inválido (debe comenzar con https://)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ DSN recibido${NC}"
echo ""

# ============================================================================
# PASO 3: CONFIGURAR VARIABLES ADICIONALES
# ============================================================================
echo -e "${YELLOW}PASO 3: Configurar variables Sentry${NC}"
echo ""

read -p "Ambiente (default: production): " SENTRY_ENV
SENTRY_ENV=${SENTRY_ENV:-production}

read -p "Tasa de muestreo de transacciones (0.1-1.0, default: 0.1): " SAMPLE_RATE
SAMPLE_RATE=${SAMPLE_RATE:-0.1}

# Validar sample rate
if ! [[ $SAMPLE_RATE =~ ^0\.[0-9]+$|^1\.0$ ]]; then
    echo -e "${YELLOW}⚠️  Valor inválido, usando 0.1${NC}"
    SAMPLE_RATE=0.1
fi

echo ""
echo "Configuración a usar:"
echo "  DSN: $SENTRY_DSN"
echo "  Ambiente: $SENTRY_ENV"
echo "  Sample Rate: $SAMPLE_RATE (10% de transacciones)"
echo ""

# ============================================================================
# PASO 4: GUARDAR EN .env
# ============================================================================
echo -e "${YELLOW}PASO 4: Guardar configuración${NC}"
echo ""

BACKEND_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/backend" && pwd )"

if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "Creando $BACKEND_DIR/.env desde template..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

# Actualizar o agregar variables SENTRY
if grep -q "^SENTRY_DSN=" "$BACKEND_DIR/.env"; then
    sed -i.bak "s|^SENTRY_DSN=.*|SENTRY_DSN=$SENTRY_DSN|" "$BACKEND_DIR/.env"
else
    echo "SENTRY_DSN=$SENTRY_DSN" >> "$BACKEND_DIR/.env"
fi

if grep -q "^SENTRY_ENVIRONMENT=" "$BACKEND_DIR/.env"; then
    sed -i.bak "s|^SENTRY_ENVIRONMENT=.*|SENTRY_ENVIRONMENT=$SENTRY_ENV|" "$BACKEND_DIR/.env"
else
    echo "SENTRY_ENVIRONMENT=$SENTRY_ENV" >> "$BACKEND_DIR/.env"
fi

if grep -q "^SENTRY_TRACES_SAMPLE_RATE=" "$BACKEND_DIR/.env"; then
    sed -i.bak "s|^SENTRY_TRACES_SAMPLE_RATE=.*|SENTRY_TRACES_SAMPLE_RATE=$SAMPLE_RATE|" "$BACKEND_DIR/.env"
else
    echo "SENTRY_TRACES_SAMPLE_RATE=$SAMPLE_RATE" >> "$BACKEND_DIR/.env"
fi

echo -e "${GREEN}✅ Configuración guardada en $BACKEND_DIR/.env${NC}"

# Limpiar archivo .bak
rm -f "$BACKEND_DIR/.env.bak"

echo ""

# ============================================================================
# PASO 5: VERIFICAR INSTALACIÓN
# ============================================================================
echo -e "${YELLOW}PASO 5: Verificar instalación${NC}"
echo ""

if python3 -c "import sentry_sdk; print('✅ sentry-sdk instalado')" 2>/dev/null; then
    echo -e "${GREEN}✅ SDK de Sentry está disponible${NC}"
else
    echo -e "${RED}❌ sentry-sdk no está instalado${NC}"
    echo "Instálalo con: pip install sentry-sdk[fastapi]"
    exit 1
fi

echo ""

# ============================================================================
# PASO 6: TEST DE CONEXIÓN
# ============================================================================
echo -e "${YELLOW}PASO 6: Probar conexión${NC}"
echo ""

read -p "¿Quieres hacer un test de conexión a Sentry? (s/n): " -n 1 -r TEST_CONN
echo ""

if [[ $TEST_CONN =~ ^[Ss]$ ]]; then
    echo "Enviando evento de prueba a Sentry..."
    
    python3 << 'EOF'
import os
import sentry_sdk
from dotenv import load_dotenv

# Cargar .env
dotenv_path = os.path.join("backend", ".env")
load_dotenv(dotenv_path)

sentry_dsn = os.getenv("SENTRY_DSN")
if not sentry_dsn:
    print("❌ SENTRY_DSN no configurado")
    exit(1)

try:
    # Inicializar Sentry
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        environment="test",
    )
    
    # Enviar mensaje de prueba
    sentry_sdk.capture_message("🧪 Test de conexión desde setup-sentry.sh", level="info")
    print("✅ Evento enviado a Sentry")
    print("")
    print("Verifica en: https://sentry.io")
    print("Busca el evento con mensaje: '🧪 Test de conexión desde setup-sentry.sh'")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
EOF
fi

echo ""

# ============================================================================
# INFORMACIÓN DE INTEGRACIÓN
# ============================================================================
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  SETUP COMPLETADO ✅                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

echo -e "${YELLOW}INTEGRACIONES RECOMENDADAS:${NC}"
echo ""
echo "1️⃣  Alertas en Slack:"
echo "   - En proyecto Sentry → Settings → Integrations"
echo "   - Busca 'Slack' y conecta tu workspace"
echo ""
echo "2️⃣  Alertas en GitHub:"
echo "   - En proyecto Sentry → Integrations → GitHub"
echo "   - Automáticamente abrirá issues en GitHub"
echo ""
echo "3️⃣  Alertas por Email:"
echo "   - En proyecto Sentry → Alerts"
echo "   - Crea alertas para errores críticos"
echo ""

echo -e "${YELLOW}MONITOREO EN TIEMPO REAL:${NC}"
echo ""
echo "El servidor capturá automáticamente:"
echo "  ❌ Excepciones no controladas"
echo "  ⚠️  Errores en base de datos"
echo "  🐌 Transacciones lentas (>1s)"
echo "  📊 Performance degradation"
echo ""
echo "💡 Tip: Puedes capturar eventos manualmente:"
echo ""
echo "   from app.utils.sentry_config import capture_message"
echo "   capture_message('Stock bajo!', level='warning', context={'product_id': 123})"
echo ""

echo -e "${YELLOW}PRÓXIMOS PASOS:${NC}"
echo ""
echo "1. Iniciar servidor: python3 -m uvicorn app.main:app --reload"
echo "2. Ir a https://sentry.io y ver los eventos en vivo"
echo "3. Configurar alertas según tus necesidades"
echo ""

echo -e "${GREEN}¡Monitoreo de errores en producción configurado! 🚀${NC}"
echo ""
