# 🔧 Solución: Error de importación de 'requests'

## Problema
```
La importación "requests" no se ha podido resolver desde el origen
```

## Solución Rápida

### Opción 1: Script Automático (Recomendado) ⭐

```bash
chmod +x setup-tests.sh
./setup-tests.sh
```

Este script:
- ✅ Activa el entorno virtual del backend
- ✅ Instala el módulo `requests`
- ✅ Te deja listo para ejecutar las pruebas

### Opción 2: Manual

```bash
# 1. Ir al directorio backend
cd backend

# 2. Activar entorno virtual
source venv/bin/activate

# 3. Instalar requests
pip install requests

# 4. Volver al directorio raíz
cd ..

# 5. Ejecutar pruebas (backend debe estar corriendo)
python3 test-backend.py
```

### Opción 3: Instalar en entorno global

```bash
# Usar pip3 para instalación global
pip3 install requests

# O si usas conda
conda install requests
```

## ¿Por qué pasa esto?

El módulo `requests` es necesario solo para las **pruebas automatizadas del API** (`test-backend.py`). No es necesario para ejecutar el backend o frontend normalmente.

El backend usa su propio entorno virtual (`backend/venv/`) donde se instalan las dependencias. Para ejecutar pruebas que usan `requests`, necesitas instalarlo en ese entorno.

## Verificar que funcionó

Después de instalar, ejecuta:

```bash
python3 -c "import requests; print('✅ requests instalado correctamente')"
```

Si ves el mensaje de éxito, ya puedes ejecutar:

```bash
python3 test-backend.py
```

## Nota Importante

- ⚠️ El **backend debe estar corriendo** antes de ejecutar `test-backend.py`
- ⚠️ Inicia el backend con: `./start-backend.sh`
- ⚠️ El backend debe estar en: http://localhost:8000

## Alternativa sin requests

Si no quieres instalar `requests`, puedes probar el backend manualmente:

1. **Abrir documentación de la API**: http://localhost:8000/docs
2. **Probar endpoints** desde la interfaz Swagger
3. **Ver health check**: http://localhost:8000/health

O usar `curl`:

```bash
# Health check
curl http://localhost:8000/health

# Crear perfil
curl -X POST http://localhost:8000/api/profiles \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","password":"test123","phone":"+1234567890"}'
```

## ✅ Solución Aplicada

He actualizado los siguientes archivos:

1. ✅ `test-backend.py` - Mensaje de error más claro
2. ✅ `backend/requirements.txt` - Incluye `requests` como dependencia de testing
3. ✅ `setup-tests.sh` - Nuevo script para configurar testing automáticamente
4. ✅ `START_HERE.txt` - Instrucciones actualizadas
5. ✅ `TEST_SUMMARY.md` - Documentación actualizada

Ahora el sistema te guiará mejor cuando falte el módulo `requests`.
