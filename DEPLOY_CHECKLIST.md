# Quick Deploy Checklist

Copia y pega estos comandos en orden para deployer a producción.

## Paso 1: Preparar entorno

```bash
# Clonar repo (si es la primera vez)
git clone <tu-repo> && cd sistema-de-inve-sand

# Instalar dependencias
pip install -r backend/requirements.txt

# Copiar configuración
cp backend/.env.production.example backend/.env

# ⚠️ EDITAR .env con valores reales
nano backend/.env
# Cambiar: DATABASE_URL, SECRET_KEY, CORS_ORIGINS, SENTRY_DSN, etc.
```

## Paso 2: Preparar PostgreSQL

```bash
# Crear BD (oncesolamente)
psql -U postgres << EOF
CREATE USER inventario_prod WITH PASSWORD 'tu_password_aqui';
CREATE DATABASE inventario_prod OWNER inventario_prod;
GRANT ALL PRIVILEGES ON DATABASE inventario_prod TO inventario_prod;
EOF

# Migrar datos desde SQLite (si tienes datos actuales)
cd backend
python3 migrate_sqlite_to_postgres.py \
  --source-db inventory.db \
  --dest-url postgresql://inventario_prod:tu_password_aqui@localhost:5432/inventario_prod
```

## Paso 3: Configurar Backups

```bash
# Hacer script ejecutable
chmod +x backend/backup_database.sh

# Agregar a crontab (backup diario a las 2 AM)
crontab -e
# Pegar esta línea:
# 0 2 * * * DB_USER=inventario_prod DB_NAME=inventario_prod DB_PASSWORD="tu_password_aqui" BACKUP_DIR=/var/backups/inventario /path/to/backend/backup_database.sh
```

## Paso 4: Configurar Sentry (Monitoreo)

```bash
# 1. Crear cuenta en https://sentry.io (gratuito)
# 2. Crear proyecto Python/FastAPI
# 3. Copiar DSN del proyecto
# 4. En backend/.env:
#    SENTRY_DSN=https://...@sentry.io/...

# Verificar que funciona
python3 -c "from app.utils.sentry_config import init_sentry; init_sentry()"
```

## Paso 5: Verificar que está todo listo

```bash
# En producción:
python3 backend/check_production_readiness.py

# Si todo muestra ✅, estás listo
```

## Paso 6: Iniciar servidor

```bash
# Opción A: Desarrollo (con reload)
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Opción B: Producción (con gunicorn + workers)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app.main:app

# Opción C: Systemd service (para que inicie al bootear)
# Ver: https://github.com/tiangolo/uvicorn/blob/master/docs/deployment/systemd.md
```

## Paso 7: Servir frontend

```bash
# Build una sola vez
npm run build

# Servir con nginx o Apache (ver DEPLOYMENT.md)
# O si es desarrollo:
npm run dev
```

---

## Verificaciones importantes

```bash
# API debe responder
curl http://localhost:8000/docs

# PostgreSQL debe estar corriendo
psql -U inventario_prod -d inventario_prod -c "SELECT COUNT(*) FROM orders;"

# Sentry debe capturar eventos
# Ver: https://sentry.io/organizations/

# Backups deben ejecutarse
ls -lh /var/backups/inventario/
```

---

## En caso de emergencia (rollback)

```bash
# Si algo falló, volver al release anterior con PostgreSQL:
1. Restaurar el último backup válido de PostgreSQL
2. Revertir al tag/imagen anterior de backend y frontend
3. Reiniciar servicios y validar /health

# Si PostgreSQL se cayó:
sudo systemctl restart postgresql

# Si Sentry causa lentitud:
En .env: SENTRY_TRACES_SAMPLE_RATE=0.01 (0.1 = 10%)
```

---

**Status:** ✅ Listo para producción  
**Contacto:** @usuario o email@example.com  
**Docs completas:** Ver `docs/PRODUCCION_COMPLETA.md`
