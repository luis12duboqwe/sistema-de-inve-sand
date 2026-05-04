#!/bin/bash

# ============================================================================
# Setup Production - Configurador de los 4 pasos necesarios
# ============================================================================
# Uso: ./setup-production.sh
# Este script guía al usuario a través de:
# 1. ✅ Dependencias (ya completadas)
# 2. PostgreSQL - Generar script de migración
# 3. Backup automático - Configurar crontab
# 4. Sentry - Generar plantilla .env
# ============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║      CONFIGURACIÓN DE PRODUCCIÓN - Sistema de Inventario        ║"
echo "║                    v2.0 Multi-Ubicación                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ============================================================================
# PASO 1: Validar que las dependencias están instaladas
# ============================================================================
echo -e "${YELLOW}[PASO 1/4] Validar dependencias...${NC}"
if python3 -c "import sentry_sdk; import psycopg2" 2>/dev/null; then
    echo -e "${GREEN}✅ Dependencias instaladas correctamente${NC}"
    echo "   - sentry-sdk 1.45.1"
    echo "   - psycopg2-binary 2.9.9"
else
    echo -e "${RED}❌ Falta instalar dependencias${NC}"
    echo "Ejecuta: cd backend && pip install -r requirements.txt"
    exit 1
fi
echo ""

# ============================================================================
# PASO 2: PostgreSQL - Preparar migración
# ============================================================================
echo -e "${YELLOW}[PASO 2/4] Configurar PostgreSQL...${NC}"
echo ""
echo "Se encontró script de migración en:"
echo "  $BACKEND_DIR/migrate_sqlite_to_postgres.py"
echo ""
echo "Pasos para ejecutar:"
echo ""
echo -e "${BLUE}  1. Instalar PostgreSQL (si no lo tienes):${NC}"
echo "     macOS:   brew install postgresql"
echo "     Ubuntu:  sudo apt install postgresql postgresql-contrib"
echo "     Windows: Descargar desde https://www.postgresql.org/download/"
echo ""
echo -e "${BLUE}  2. Crear usuario y base de datos:${NC}"
echo "     psql -U postgres -c \"CREATE USER inventory_user WITH PASSWORD 'tu_password';\" "
echo "     psql -U postgres -c \"CREATE DATABASE inventory_db OWNER inventory_user;\""
echo ""
echo -e "${BLUE}  3. Ejecutar migración (reemplaza URL con tus datos):${NC}"
echo "     cd backend"
echo "     python3 migrate_sqlite_to_postgres.py \\"
echo "       --dest-url postgresql://inventory_user:tu_password@localhost:5432/inventory_db"
echo ""
echo -e "${BLUE}  4. Actualizar .env:${NC}"
echo "     DATABASE_URL=postgresql+psycopg2://inventory_user:tu_password@localhost:5432/inventory_db"
echo ""

read -p "¿Ya completaste los pasos de PostgreSQL? (s/n): " -n 1 -r POSTGRES_DONE
echo ""
if [[ ! $POSTGRES_DONE =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}Completa los pasos de PostgreSQL primero, luego ejecuta este script nuevamente${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL configurado${NC}"
echo ""

# ============================================================================
# PASO 3: Backup automático - Configurar crontab
# ============================================================================
echo -e "${YELLOW}[PASO 3/4] Configurar backup automático...${NC}"
echo ""
echo "Se encontró script de backup en:"
echo "  $BACKEND_DIR/backup_database.sh"
echo ""
echo "Para agregar a crontab, ejecuta:"
echo ""
echo -e "${BLUE}  crontab -e${NC}"
echo ""
echo "Luego pega UNA de estas opciones:"
echo ""
echo -e "${YELLOW}OPCIÓN A: Backup diario a las 2 AM${NC}"
echo "  0 2 * * * $BACKEND_DIR/backup_database.sh >> /var/log/inventory-backup.log 2>&1"
echo ""
echo -e "${YELLOW}OPCIÓN B: Backup diario 2 AM + semanal domingos 3 AM${NC}"
echo "  0 2 * * * $BACKEND_DIR/backup_database.sh >> /var/log/inventory-backup.log 2>&1"
echo "  0 3 * * 0 $BACKEND_DIR/backup_database.sh --weekly >> /var/log/inventory-backup.log 2>&1"
echo ""
echo "Para ver entradas actuales: crontab -l"
echo ""

read -p "¿Ya completaste la configuración de crontab? (s/n): " -n 1 -r CRON_DONE
echo ""
if [[ ! $CRON_DONE =~ ^[Ss]$ ]]; then
    echo -e "${YELLOW}Configura el crontab primero, luego ejecuta este script nuevamente${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backup automático configurado${NC}"
echo ""

# ============================================================================
# PASO 4: Sentry - Preparar variables de entorno
# ============================================================================
echo -e "${YELLOW}[PASO 4/4] Configurar Sentry...${NC}"
echo ""
echo "Pasos para configurar Sentry:"
echo ""
echo -e "${BLUE}  1. Crear cuenta (si no tienes):${NC}"
echo "     Ir a https://sentry.io y registrarse (free tier disponible)"
echo ""
echo -e "${BLUE}  2. Crear proyecto:${NC}"
echo "     - Plataforma: Python"
echo "     - Framework: FastAPI"
echo "     - Copiar el DSN (se ve como: https://xxxxx@oxxxxx.ingest.sentry.io/xxxxxx)"
echo ""
echo -e "${BLUE}  3. Agregación a .env:${NC}"
echo "     SENTRY_DSN=https://tu_dsn_aqui"
echo "     SENTRY_ENVIRONMENT=production"
echo "     SENTRY_TRACES_SAMPLE_RATE=0.1"
echo ""

read -p "¿Ya creaste tu proyecto en Sentry? (s/n): " -n 1 -r SENTRY_DONE
echo ""

if [[ $SENTRY_DONE =~ ^[Ss]$ ]]; then
    read -p "Pega tu SENTRY_DSN aquí: " SENTRY_DSN
    if [[ ! -z "$SENTRY_DSN" ]]; then
        # Actualizar o crear .env si no existe
        if [ ! -f "$BACKEND_DIR/.env" ]; then
            echo "Creando $BACKEND_DIR/.env..."
            cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
        fi
        
        # Agregar/actualizar Sentry variables
        if grep -q "SENTRY_DSN=" "$BACKEND_DIR/.env"; then
            sed -i.bak "s|^SENTRY_DSN=.*|SENTRY_DSN=$SENTRY_DSN|" "$BACKEND_DIR/.env"
        else
            echo "SENTRY_DSN=$SENTRY_DSN" >> "$BACKEND_DIR/.env"
        fi
        
        if grep -q "SENTRY_ENVIRONMENT=" "$BACKEND_DIR/.env"; then
            sed -i.bak "s|^SENTRY_ENVIRONMENT=.*|SENTRY_ENVIRONMENT=production|" "$BACKEND_DIR/.env"
        else
            echo "SENTRY_ENVIRONMENT=production" >> "$BACKEND_DIR/.env"
        fi
        
        if grep -q "SENTRY_TRACES_SAMPLE_RATE=" "$BACKEND_DIR/.env"; then
            sed -i.bak "s|^SENTRY_TRACES_SAMPLE_RATE=.*|SENTRY_TRACES_SAMPLE_RATE=0.1|" "$BACKEND_DIR/.env"
        else
            echo "SENTRY_TRACES_SAMPLE_RATE=0.1" >> "$BACKEND_DIR/.env"
        fi
        
        echo -e "${GREEN}✅ Sentry configurado en .env${NC}"
    fi
else
    echo -e "${YELLOW}Crea tu proyecto en Sentry primero para habilitar monitoreo de errores${NC}"
fi
echo ""

# ============================================================================
# Resumen Final
# ============================================================================
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  CONFIGURACIÓN COMPLETADA ✅                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "PRÓXIMOS PASOS:"
echo ""
echo -e "${YELLOW}1. Iniciar el servidor:${NC}"
echo "   cd backend"
echo "   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo -e "${YELLOW}2. Acceder al API:${NC}"
echo "   http://localhost:8000/docs (Swagger UI)"
echo "   http://localhost:8000/redoc (ReDoc)"
echo ""
echo -e "${YELLOW}3. Monitorear:${NC}"
echo "   - Errores en Sentry: https://sentry.io"
echo "   - Backups en: /var/backups/inventory/ (verificar con: ls -la)"
echo ""
echo -e "${YELLOW}4. Verificación de salud:${NC}"
echo "   curl http://localhost:8000/api/health"
echo ""
echo -e "${GREEN}Sistema de producción completamente configurado! 🚀${NC}"
echo ""
