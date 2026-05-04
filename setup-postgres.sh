#!/bin/bash

# ============================================================================
# PostgreSQL Setup Helper - Facilita la migración de SQLite a PostgreSQL
# ============================================================================
# Uso: ./setup-postgres.sh
# ============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        SETUP PostgreSQL - Sistema de Inventario v2.0            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ============================================================================
# VERIFICACIÓN PREVIA
# ============================================================================
echo -e "${YELLOW}Verificando requisitos...${NC}"

# Verificar que PostgreSQL está instalado
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL no está instalado${NC}"
    echo ""
    echo "Para instalar sigue estas instrucciones según tu SO:"
    echo ""
    echo -e "${BLUE}macOS (con Homebrew):${NC}"
    echo "  brew install postgresql"
    echo "  brew services start postgresql"
    echo ""
    echo -e "${BLUE}Ubuntu/Debian:${NC}"
    echo "  sudo apt update"
    echo "  sudo apt install postgresql postgresql-contrib"
    echo "  sudo service postgresql start"
    echo ""
    echo -e "${BLUE}Windows:${NC}"
    echo "  1. Descargar desde https://www.postgresql.org/download/windows/"
    echo "  2. Ejecutar instalador y seguir pasos"
    echo "  3. Recorda la contraseña del usuario 'postgres'"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ PostgreSQL encontrado${NC}"

# Verificar que el usuario postgres existe
if ! psql -U postgres -l &> /dev/null; then
    echo -e "${YELLOW}⚠️  No se puede conectar como usuario 'postgres'${NC}"
    echo "Esto es normal si PostgreSQL acaba de instalarse."
    echo ""
    echo -e "${BLUE}Para solucionar, intenta:${NC}"
    echo "  - Inicia sesión con: sudo -u postgres psql"
    echo "  - O asegúrate que el servicio está corriendo"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}✅ PostgreSQL está operativo${NC}"
echo ""

# ============================================================================
# ENTRADA DE DATOS
# ============================================================================
echo -e "${YELLOW}Configuración de conexión:${NC}"
echo ""

read -p "Usuario PostgreSQL a crear (default: inventory_user): " PG_USER
PG_USER=${PG_USER:-inventory_user}

read -p "Contraseña (será escondida): " -s PG_PASSWORD
echo ""
read -p "Confirma contraseña: " -s PG_PASSWORD_CONFIRM
echo ""

if [ "$PG_PASSWORD" != "$PG_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}❌ Las contraseñas no coinciden${NC}"
    exit 1
fi

read -p "Nombre de base de datos (default: inventory_db): " PG_DB
PG_DB=${PG_DB:-inventory_db}

read -p "Host PostgreSQL (default: localhost): " PG_HOST
PG_HOST=${PG_HOST:-localhost}

read -p "Puerto PostgreSQL (default: 5432): " PG_PORT
PG_PORT=${PG_PORT:-5432}

echo ""
echo "Configuración a usar:"
echo "  Usuario: $PG_USER"
echo "  Base de datos: $PG_DB"
echo "  Host: $PG_HOST"
echo "  Puerto: $PG_PORT"
echo ""

read -p "¿Proceder con esta configuración? (s/n): " -n 1 -r CONFIRM
echo ""
if [[ ! $CONFIRM =~ ^[Ss]$ ]]; then
    exit 1
fi

echo ""

# ============================================================================
# CREAR USUARIO Y BASE DE DATOS
# ============================================================================
echo -e "${YELLOW}Creando usuario y base de datos...${NC}"

# Crear usuario si no existe
psql -U postgres -tc "SELECT 1 FROM pg_user WHERE usename = '$PG_USER'" | grep -q 1 || \
psql -U postgres -c "CREATE USER $PG_USER WITH PASSWORD '$PG_PASSWORD';"

echo -e "${GREEN}✅ Usuario '$PG_USER' listo${NC}"

# Crear base de datos si no existe
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$PG_DB'" | grep -q 1 || \
psql -U postgres -c "CREATE DATABASE $PG_DB OWNER $PG_USER;"

echo -e "${GREEN}✅ Base de datos '$PG_DB' creada${NC}"

# Dar permisos
psql -U postgres -c "ALTER USER $PG_USER WITH CREATEDB;"

echo ""

# ============================================================================
# PRUEBA DE CONEXIÓN
# ============================================================================
echo -e "${YELLOW}Probando conexión...${NC}"

if psql -U $PG_USER -h $PG_HOST -p $PG_PORT -d $PG_DB -c "SELECT 1" &> /dev/null; then
    echo -e "${GREEN}✅ Conexión exitosa${NC}"
else
    echo -e "${RED}❌ Error al conectarse${NC}"
    echo "Verifica el usuario, contraseña y permisos"
    exit 1
fi

echo ""

# ============================================================================
# GENERAR CONNECTION STRING
# ============================================================================
CONNECTION_STRING="postgresql+psycopg2://$PG_USER:$PG_PASSWORD@$PG_HOST:$PG_PORT/$PG_DB"

echo -e "${BLUE}Tu DATABASE_URL para .env:${NC}"
echo ""
echo -e "${YELLOW}$CONNECTION_STRING${NC}"
echo ""

# ============================================================================
# GUARDAR EN .env
# ============================================================================
read -p "¿Guardar en backend/.env? (s/n): " -n 1 -r SAVE_ENV
echo ""

if [[ $SAVE_ENV =~ ^[Ss]$ ]]; then
    BACKEND_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/backend" && pwd )"
    
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
        echo "Creado $BACKEND_DIR/.env desde .env.example"
    fi
    
    # Actualizar o agregar DATABASE_URL
    if grep -q "^DATABASE_URL=" "$BACKEND_DIR/.env"; then
        sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$CONNECTION_STRING|" "$BACKEND_DIR/.env"
    else
        echo "DATABASE_URL=$CONNECTION_STRING" >> "$BACKEND_DIR/.env"
    fi
    
    echo -e "${GREEN}✅ DATABASE_URL agregada a $BACKEND_DIR/.env${NC}"
fi

echo ""

# ============================================================================
# EJECUTAR MIGRACIÓN
# ============================================================================
read -p "¿Ejecutar migración de SQLite a PostgreSQL ahora? (s/n): " -n 1 -r MIGRATE
echo ""

if [[ $MIGRATE =~ ^[Ss]$ ]]; then
    BACKEND_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/backend" && pwd )"
    
    if [ -f "$BACKEND_DIR/migrate_sqlite_to_postgres.py" ]; then
        echo -e "${YELLOW}Ejecutando migración...${NC}"
        echo ""
        cd "$BACKEND_DIR"
        
        python3 migrate_sqlite_to_postgres.py \
            --dest-url "$CONNECTION_STRING"
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✅ Migración completada exitosamente${NC}"
        else
            echo ""
            echo -e "${RED}❌ Error durante la migración${NC}"
            echo "Revisa los logs anteriores para más detalles"
        fi
    else
        echo -e "${RED}❌ Script de migración no encontrado${NC}"
        echo "Esperaba: $BACKEND_DIR/migrate_sqlite_to_postgres.py"
    fi
else
    echo -e "${YELLOW}Migración omitida${NC}"
    echo ""
    echo "Puedes ejecutarla después con:"
    echo "  cd backend"
    echo "  python3 migrate_sqlite_to_postgres.py --dest-url \"$CONNECTION_STRING\""
fi

echo ""

# ============================================================================
# PRÓXIMOS PASOS
# ============================================================================
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  SETUP COMPLETADO ✅                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "REPASO DE CREDENCIALES GUARDADAS:"
echo "  Usuario: $PG_USER"
echo "  Base de datos: $PG_DB"
echo ""
echo "PRÓXIMOS PASOS:"
echo ""
echo -e "${YELLOW}1. Verificar que los datos migraron correctamente:${NC}"
echo "   psql -U $PG_USER -h $PG_HOST -d $PG_DB -c \"SELECT COUNT(*) FROM products;\""
echo ""
echo -e "${YELLOW}2. Actualizar variables de entorno adicionales:${NC}"
echo "   - Editar backend/.env con SECRET_KEY y SENTRY_DSN"
echo "   - Ver template en backend/.env.production"
echo ""
echo -e "${YELLOW}3. Iniciar servidor:${NC}"
echo "   cd backend"
echo "   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo -e "${YELLOW}4. Verificar salud:${NC}"
echo "   curl http://localhost:8000/api/health"
echo ""
