# Guía de Producción: PostgreSQL, Backups y Monitoreo

Este documento es un guide paso a paso para preparar tu sistema para producción con:
1. **PostgreSQL** (reemplaza SQLite)
2. **Backups Automáticos** (diarios/semanales)
3. **Monitoreo con Sentry** (captura de errores)

**Tiempo estimado:** 45 minutos

---

## ✅ REQUISITOS

### Sistema Operativo (Linux/macOS)
```bash
# En producción, usar Linux VPS (Linode, DigitalOcean, AWS)
# Para desarrollo local, instalar:
# - PostgreSQL 14+
# - Python 3.11+
# - Git
```

### Paquetes necesarios
```bash
# Instalar dependencias (ya actualizadas en requirements.txt)
cd backend
pip install -r requirements.txt

# Verificar que psycopg2 está instalado
python3 -c "import psycopg2; print('✓ psycopg2 listo')"

# Verificar que sentry-sdk está instalado
python3 -c "import sentry_sdk; print('✓ sentry-sdk listo')"
```

---

## 🗄️ PASO 1: MIGRAR A POSTGRESQL

### 1.1 Instalar PostgreSQL

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15

# Verificar
psql --version
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Verificar
psql --version
```

**Windows:**
- Descargar instalador desde https://www.postgresql.org/download/windows/
- Instalar con pgAdmin incluido

### 1.2 Crear usuario y base de datos

```bash
# Conectar a PostgreSQL
psql -U postgres

# Dentro de psql:
CREATE USER inventario_prod WITH PASSWORD 'cambiar_esto_ahora_123';
CREATE DATABASE inventario_prod OWNER inventario_prod;
GRANT ALL PRIVILEGES ON DATABASE inventario_prod TO inventario_prod;
\q
```

### 1.3 Ejecutar migración automática

```bash
cd backend

# Asegúrate que las 2 BDs existen y están pobladas
# SQLite: inventory.db (actual)
# PostgreSQL: ya creada arriba

# Ejecutar migración
python3 migrate_sqlite_to_postgres.py \
  --source-db inventory.db \
  --dest-url postgresql://inventario_prod:cambiar_esto_ahora_123@localhost:5432/inventario_prod
```

**Si la migración falla:**
- Verifica que PostgreSQL está running: `psql -U postgres -l`
- Verifica credenciales de user `inventario_prod`
- Revisa logs en `logs/migration_*.log`

### 1.4 Actualizar configuración

En `backend/.env`:
```bash
# Cambiar de:
DATABASE_URL=sqlite:///inventory.db

# A:
DATABASE_URL=postgresql://inventario_prod:cambiar_esto_ahora_123@localhost:5432/inventario_prod
```

### 1.5 Reiniciar servidor

```bash
# Matar proceso antiguo
pkill -f "uvicorn"

# Iniciar con PostgreSQL
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Verificar:**
```bash
curl http://localhost:8000/docs

# Si ves Swagger UI = ✅ Funciona con PostgreSQL
```

---

## 💾 PASO 2: BACKUPS AUTOMÁTICOS

### 2.1 Preparar script

```bash
# Hacer ejecutable
chmod +x backend/backup_database.sh

# Probar manualmente
DB_USER=inventario_prod \
DB_NAME=inventario_prod \
DB_PASSWORD="cambiar_esto_ahora_123" \
BACKUP_DIR=/var/backups/inventario \
./backend/backup_database.sh
```

**Si funciona:** Verás archivo `.sql.gz` en `/var/backups/inventario/`

### 2.2 Configurar Crontab

```bash
# Editar crontab
crontab -e

# Agregar línea para backup DIARIO a las 2 AM:
0 2 * * * DB_USER=inventario_prod DB_NAME=inventario_prod DB_PASSWORD="cambiar_esto_ahora_123" BACKUP_DIR=/var/backups/inventario /path/to/backend/backup_database.sh

# Agregar línea para backup SEMANAL (domingo 3 AM):
0 3 * * 0 DB_USER=inventario_prod DB_NAME=inventario_prod DB_PASSWORD="cambiar_esto_ahora_123" BACKUP_DIR=/var/backups/inventario /path/to/backend/backup_database.sh --weekly
```

**Verificar que se creó:**
```bash
crontab -l
```

### 2.3 Verificar backups

```bash
# Ver backups existentes
ls -lh /var/backups/inventario/

# Ver logs
tail -f /var/backups/inventario/backup.log
```

### 2.4 Restaurar desde backup si falla algo

```bash
# Descomprimir
gunzip inventory_prod_daily_20260311_020000.sql.gz

# Restaurar
psql -U inventario_prod -d inventario_prod < inventory_prod_daily_20260311_020000.sql

# Verificar
psql -U inventario_prod -d inventario_prod -c "SELECT COUNT(*) FROM orders;"
```

---

## 🔍 PASO 3: SENTRY (MONITOREO)

### 3.1 Crear cuenta Sentry

1. Ir a https://sentry.io/signup/
2. Registrarse (gratuito hasta 5000 eventos/mes)
3. Crear proyecto:
   - Platform: **Python**
   - Framework: **FastAPI**
4. Copiar **DSN** (ejemplo): `https://abc123@sentry.io/123456`

### 3.2 Actualizar .env

```bash
# En backend/.env:
SENTRY_DSN=https://abc123@sentry.io/123456
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### 3.3 Reiniciar servidor

```bash
pkill -f "uvicorn"
cd backend
python3 -m uvicorn app.main:app --reload
```

**En logs verás:**
```
✓ Sentry inicializado correctamente
```

### 3.4 Probar que Sentry funciona

```bash
# Simular error en Python
python3 << 'EOF'
from app.utils.sentry_config import capture_message
capture_message("Test: Sistema listo para producción", level="warning")
print("✓ Mensaje enviado a Sentry")
EOF
```

**Verificar en Sentry dashboard:**
- Ir a https://sentry.io
- Buscar "Test: Sistema listo para producción"
- Si lo ves = ✅ Sentry funciona

### 3.5 Cambiar en routers para capturar errores

Ejemplo en `backend/app/routers/orders.py`:

```python
from app.utils.sentry_config import capture_exception

try:
    # Tu código...
except Exception as e:
    event_id = capture_exception(e, {"order_id": order_id})
    logger.error(f"Error en orden (Sentry: {event_id})")
    raise
```

---

## 🚀 CHEQUEO FINAL ANTES DE PRODUCCIÓN

```bash
# 1. Verificar BD
psql -U inventario_prod -d inventario_prod -c "SELECT COUNT(*) FROM orders;"

# 2. Verificar API
curl http://localhost:8000/healthcheck

# 3. Verificar Sentry
cat backend/.env | grep SENTRY_DSN

# 4. Verificar backups
ls -lh /var/backups/inventario/ | head -5

# 5. Verificar crontab
crontab -l | grep backup

# 6. Logs
tail -50 backend/logs/*.log | grep -E "ERROR|SENTRY|PostgreSQL"
```

---

## 📋 DEPLOYMENT EN PRODUCCIÓN (Servicios recomendados)

### Opción A: Railway.app (Recomendado para principiantes)
1. Conectar repositorio a https://railway.app
2. Railway crea PostgreSQL automáticamente
3. `DATABASE_URL` se configura automáticamente
4. Deploy con `git push`

### Opción B: Render.com
1. Crear servicio PostgreSQL
2. Crear servicio Web
3. Agregar `DATABASE_URL` en variables de entorno
4. Deploy automático con `git push`

### Opción C: AWS/DigitalOcean/Linode (Avanzado)
1. Crearun VPS con Ubuntu 22.04
2. Instalar PostgreSQL y Python
3. Configurar systemd service para que inicie al bootear
4. Habilitar firewall (solo puerto 443)
5. Usar Nginx como reverse proxy

---

## 🆘 TROUBLESHOOTING

### "psycopg2: connection refused"
```bash
# Verificar que PostgreSQL está running
sudo systemctl status postgresql

# Si no está corriendo:
sudo systemctl start postgresql
```

### "password authentication failed for user"
```bash
# Verificar contraseña
psql -U inventario_prod -h localhost -d inventario_prod

# Si la contraseña cambió, actualizar .env
```

### Sentry no captura errores
```bash
# Verificar que SENTRY_DSN está en .env
echo $SENTRY_DSN

# Si está vacío, copiar nuevamente
# Reiniciar: pkill -f uvicorn
```

### Backups no se ejecutan
```bash
# Ver errores de cron
grep CRON /var/log/syslog | tail -20

# O usar:
sudo journalctl -u cron -n 50
```

---

## 📞 SOPORTE

- **PostgreSQL docs:** https://www.postgresql.org/docs/
- **Sentry docs:** https://docs.sentry.io/
- **Railway:** https://docs.railway.app/
- **Render:** https://render.com/docs

---

**Status:** ✅ Sistema listo para producción
**Último update:** 11 de Marzo de 2026
