#!/bin/bash

# ════════════════════════════════════════════════════════════════════════════
# 🚀 CHECKLIST DE PRODUCCIÓN - Sistema de Inventario v2.0
# ════════════════════════════════════════════════════════════════════════════
# Este archivo ayuda a rastrear el progreso de configuración para producción
# ════════════════════════════════════════════════════════════════════════════

echo "
╔════════════════════════════════════════════════════════════════════════╗
║                CHECKLIST DE CONFIGURACIÓN DE PRODUCCIÓN                ║
║                   Sistema de Inventario v2.0                          ║
╚════════════════════════════════════════════════════════════════════════╝
"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_DIR="backend"
TOTAL_STEPS=8
COMPLETED=0

# Función para marcar un paso
check_step() {
    local step_name=$1
    local check_command=$2
    
    if eval "$check_command" &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} $step_name"
        ((COMPLETED++))
        return 0
    else
        echo -e "${RED}[✗]${NC} $step_name"
        return 1
    fi
}

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}VERIFICACIONES DE INSTALACIÓN${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# 1. Verificar sentry-sdk
check_step "sentry-sdk instalado" "python3 -c 'import sentry_sdk'"

# 2. Verificar psycopg2
check_step "psycopg2-binary instalado" "python3 -c 'import psycopg2'"

# 3. Verificar script PostgreSQL
check_step "Script setup-postgres.sh existe" "[ -f './setup-postgres.sh' ]"

# 4. Verificar script Sentry
check_step "Script setup-sentry.sh existe" "[ -f './setup-sentry.sh' ]"

# 5. Verificar script migración
check_step "Script migrate_sqlite_to_postgres.py existe" "[ -f '$BACKEND_DIR/migrate_sqlite_to_postgres.py' ]"

# 6. Verificar script backup
check_step "Script backup_database.sh existe" "[ -f '$BACKEND_DIR/backup_database.sh' ] && [ -x '$BACKEND_DIR/backup_database.sh' ]"

# 7. Verificar template .env.production
check_step "Archivo .env.production existe" "[ -f '$BACKEND_DIR/.env.production' ]"

# 8. Verificar Sentry config en main.py
check_step "init_sentry() en app/main.py" "grep -q 'init_sentry()' '$BACKEND_DIR/app/main.py'"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}VERIFICACIONES DE CONFIGURACIÓN${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

TOTAL_STEPS=$((TOTAL_STEPS + 7))

# 9. Verificar .env con DATABASE_URL
if grep -q "^DATABASE_URL=" "$BACKEND_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}[✓]${NC} DATABASE_URL configurado en .env"
    ((COMPLETED++))
else
    echo -e "${YELLOW}[⚠]${NC} DATABASE_URL NO está en .env (ejecuta ./setup-postgres.sh)"
fi

# 10. Verificar SENTRY_DSN
if grep -q "^SENTRY_DSN=" "$BACKEND_DIR/.env" 2>/dev/null; then
    SENTRY_DSN=$(grep "^SENTRY_DSN=" "$BACKEND_DIR/.env" | cut -d'=' -f2)
    if [[ "$SENTRY_DSN" != *"YOUR_DSN_HERE"* ]] && [[ ! -z "$SENTRY_DSN" ]]; then
        echo -e "${GREEN}[✓]${NC} SENTRY_DSN configurado"
        ((COMPLETED++))
    else
        echo -e "${YELLOW}[⚠]${NC} SENTRY_DSN vacio/placeholder (ejecuta ./setup-sentry.sh)"
    fi
else
    echo -e "${YELLOW}[⚠]${NC} SENTRY_DSN NO está en .env"
fi

# 11. Verificar SECRET_KEY
if grep -q "^SECRET_KEY=" "$BACKEND_DIR/.env" 2>/dev/null; then
    SECRET_KEY=$(grep "^SECRET_KEY=" "$BACKEND_DIR/.env" | cut -d'=' -f2)
    if [[ ! -z "$SECRET_KEY" ]] && [[ "$SECRET_KEY" != "GENERATE_WITH_OPENSSL"* ]]; then
        echo -e "${GREEN}[✓]${NC} SECRET_KEY configurado"
        ((COMPLETED++))
    else
        echo -e "${YELLOW}[⚠]${NC} SECRET_KEY vacio (ejecuta: openssl rand -hex 32)"
    fi
else
    echo -e "${YELLOW}[⚠]${NC} SECRET_KEY NO está en .env"
fi

# 12. Verificar crontab para backup
if crontab -l 2>/dev/null | grep -q "backup_database.sh"; then
    echo -e "${GREEN}[✓]${NC} Backup configurado en crontab"
    ((COMPLETED++))
else
    echo -e "${YELLOW}[⚠]${NC} Backup NO configurado en crontab (ejecuta: crontab -e)"
fi

# 13. Verificar PostgreSQL conectividad
if grep -q "^DATABASE_URL=postgresql" "$BACKEND_DIR/.env" 2>/dev/null; then
    DB_URL=$(grep "^DATABASE_URL=" "$BACKEND_DIR/.env" | cut -d'=' -f2-)
    PG_USER=$(python3 - <<PY
from urllib.parse import urlparse
url = urlparse("$DB_URL")
print(url.username or "")
PY
)
    PG_PASSWORD=$(python3 - <<PY
from urllib.parse import urlparse
url = urlparse("$DB_URL")
print(url.password or "")
PY
)
    PG_HOST=$(python3 - <<PY
from urllib.parse import urlparse
url = urlparse("$DB_URL")
print(url.hostname or "localhost")
PY
)
    PG_PORT=$(python3 - <<PY
from urllib.parse import urlparse
url = urlparse("$DB_URL")
print(url.port or 5432)
PY
)
    PG_DB=$(python3 - <<PY
from urllib.parse import urlparse
url = urlparse("$DB_URL")
print((url.path or "").lstrip("/"))
PY
)

    if command -v psql &> /dev/null; then
        if PGPASSWORD="$PG_PASSWORD" psql -U "$PG_USER" -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -c "SELECT 1" &> /dev/null 2>&1; then
            echo -e "${GREEN}[✓]${NC} PostgreSQL conectado y funcional"
            ((COMPLETED++))
        else
            echo -e "${YELLOW}[⚠]${NC} PostgreSQL configurado pero NO conecta"
        fi
    else
        echo -e "${YELLOW}[⚠]${NC} PostgreSQL client (psql) no instalado"
    fi
else
    echo -e "${YELLOW}[✓]${NC} PostgreSQL aún no configurado (es el siguiente paso)"
fi

# 14. Verificar que backend compilada (imports)
if python3 -c "import sys; sys.path.insert(0, '$BACKEND_DIR'); from app.main import app" 2>/dev/null; then
    echo -e "${GREEN}[✓]${NC} Backend compila sin errores"
    ((COMPLETED++))
else
    echo -e "${RED}[✗]${NC} Backend tiene errores de compilación"
fi

# 15. Verificar que frontend compila
if [ -f "package.json" ]; then
    if npm run build &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} Frontend compila correctamente"
        ((COMPLETED++))
    else
        echo -e "${YELLOW}[⚠]${NC} Frontend tiene errores de build (npm run build)"
    fi
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}RESUMEN DE PROGRESO${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

PROGRESS=$((COMPLETED * 100 / TOTAL_STEPS))
echo -e "Pasos completados: ${GREEN}$COMPLETED${NC}/$TOTAL_STEPS ($PROGRESS%)"
echo ""

if [ $COMPLETED -eq $TOTAL_STEPS ]; then
    echo -e "${GREEN}✅ SISTEMA COMPLETAMENTE CONFIGURADO PARA PRODUCCIÓN${NC}"
    echo ""
    echo "El siguiente paso es iniciar el servidor:"
    echo "  $ cd backend"
    echo "  $ python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo ""
elif [ $COMPLETED -ge $((TOTAL_STEPS * 75 / 100)) ]; then
    echo -e "${YELLOW}⚠️  Casi listo - Faltan pasos finales${NC}"
    echo ""
    echo "Próximos pasos:"
    echo "  1. ./setup-postgres.sh"
    echo "  2. ./setup-sentry.sh"
    echo "  3. crontab -e (agregar backup)"
    echo "  4. openssl rand -hex 32 (generar SECRET_KEY)"
    echo ""
else
    echo -e "${RED}❌ Aún quedan pasos importantes${NC}"
    echo ""
    echo "Ejecuta en orden:"
    echo "  1. pip install -r $BACKEND_DIR/requirements.txt"
    echo "  2. ./setup-postgres.sh"
    echo "  3. ./setup-sentry.sh"
    echo "  4. crontab -e"
    echo ""
fi

echo ""
echo "Para ver esta checklist nuevamente:"
echo "  $ bash /workspaces/sistema-de-inve-sand/check-production-setup.sh"
echo ""
