# 🚀 QUICK START - Producción v2.0

> Las **4 mejoras de producción** ya están implementadas. Ahora configúralas en 6 pasos.

## ✅ Estado Actual

-  **Dependencias**: ✅ Instaladas (sentry-sdk, psycopg2)
- **Cost Tracking**: ✅ Implementado (costo_unitario en órdenes)
- **PostgreSQL**: 📋 Script listo para ejecutar
- **Backups**: 📋 Script+crontab listo
- **Sentry**: 📋 Script interactivo listo

---

## 6 Pasos para Producción

### PASO 1: Configurar PostgreSQL (5 min)

```bash
./setup-postgres.sh
```

Esto hará:
- Crear usuario PostgreSQL
- Crear base de datos
- Migrar datos de SQLite a PostgreSQL
- Guardar DATABASE_URL en .env

### PASO 2: Verificar Migración (1 min)

```bash
cd backend
psql -U inventory_user -d inventory_db -c "SELECT COUNT(*) FROM products;"
```

Debe mostrar el número de productos que tenías.

### PASO 3: Configurar Sentry (3 min)

```bash
./setup-sentry.sh
```

Esto hará:
- Guiar para crear cuenta en Sentry.io
- Guardar DSN en .env
- Verificar conexión
- Explicar integraciones (Slack, GitHub, Email)

### PASO 4: Configurar Backup Automático (2 min)

```bash
# Ver ubicación del script
cd backend
ls -la backup_database.sh

# Editar tu crontab
crontab -e
```

Pega UNA de estas líneas:

**Opción A: Backup diario a las 2 AM**
```
0 2 * * * /path/absoluto/al/backend/backup_database.sh >> /var/log/inventory-backup.log 2>&1
```

**Opción B: Diario 2 AM + Semanal domingo 3 AM**
```
0 2 * * * /path/absoluto/al/backend/backup_database.sh >> /var/log/inventory-backup.log 2>&1
0 3 * * 0 /path/absoluto/al/backend/backup_database.sh --weekly >> /var/log/inventory-backup.log 2>&1
```

Para encontrar la ruta absoluta:
```bash
pwd  # Desde el directorio backend
```

### PASO 5: Generar SECRET_KEY

```bash
openssl rand -hex 32
```

Copia el resultado y pégalo en `backend/.env`:
```
SECRET_KEY=<resultado_aqui>
```

### PASO 6: Iniciar Servidor

```bash
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Abre en tu navegador:
- 📊 Swagger UI: http://localhost:8000/docs
- 📚 ReDoc: http://localhost:8000/redoc
- ❤️ Health: http://localhost:8000/api/health

---

## Archivos Creados

| Archivo | Propósito |
|---------|-----------|
| `setup-postgres.sh` | Script interactivo para PostgreSQL |
| `setup-sentry.sh` | Script interactivo para Sentry |
| `setup-production.sh` | Guiacompl completa de los 4 pasos |
| `backend/.env.production` | Template con TODOS los valores |
| `backend/migrate_sqlite_to_postgres.py` | Script migración BD |
| `backend/backup_database.sh` | Script backup automático |
| `backend/app/utils/sentry_config.py` | Configuración de Sentry |

---

## Validaciones Rápidas

```bash
# Verificar dependencias
python3 -c "import sentry_sdk; import psycopg2; print('✅ OK')"

# Verificar migración de datos
psql -U inventory_user -d inventory_db -c "\dt"  # Lista tablas

# Verificar backup
ls -la /var/backups/inventory/  # Si ya ejecutaste backup

# Verificar Sentry
grep SENTRY_DSN backend/.env | head -1  # Debe mostrar DSN
```

---

## Variables .env Necesarias (Mínimas)

```env
# Base de datos (PostgreSQL)
DATABASE_URL=postgresql+psycopg2://inventory_user:password@localhost:5432/inventory_db

# JWT (generar con: openssl rand -hex 32)
SECRET_KEY=xxxxx

# Sentry (obtener de https://sentry.io)
SENTRY_DSN=https://xxxxx@oxxxxx.ingest.sentry.io/xxxxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

Ver `backend/.env.production` para configuración completa.

---

## Troubleshooting

### "PostgreSQL no encontrado"
```bash
# macOS
brew install postgresql

# Ubuntu
sudo apt install postgresql postgresql-contrib

# Iniciar servicio
sudo service postgresql start
```

### "Error: user 'inventory_user' does not exist"
```bash
# Ejecutar setup-postgres.sh nuevamente
./setup-postgres.sh
```

### "ModuleNotFoundError: sentry_sdk"
```bash
cd backend
pip install -r requirements.txt
```

### "Connection refused en PostgreSQL"
```bash
# Verificar que PostgreSQL está corriendo
psql -U postgres -l

# Si no aparece, iniciar servicio
sudo service postgresql start
```

---

## Monitoreo en Producción

Una vez en vivo, verás en **Sentry**:

- 🔴 **Errores** en tiempo real
- ⚠️ **Advertencias** de stock bajo
- 🐌 **Performance** degradado
- 📊 **Tendencias** de errores
- 🔗 **Integración** con GitHub/Slack

```python
# Ejemplo: Capturar evento personalizado
from app.utils.sentry_config import capture_message

capture_message(
    "Stock bajo en producto",
    level="warning",
    context={"product_id": 123, "stock": 5}
)
```

---

## Cuál es el Siguiente Paso después de Producción?

1. **Systemd Service**: Auto-arrancar servidor en reboot
2. **Nginx Reverse Proxy**: HTTPS, CDN, balanceo
3. **Monitoreo de Resources**: CPU, RAM, Disk
4. **Disaster Recovery**: Restore automático de backups
5. **Auto-Scaling**: Si el tráfico crece

Pero por ahora, **¡ya tienes producción lista!** 🎉

---

**Documentación completa**: Ver `docs/PRODUCCION_COMPLETA.md` para más detalles.
