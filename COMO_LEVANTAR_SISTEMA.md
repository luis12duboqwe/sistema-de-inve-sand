# 🚀 Cómo Levantar el Sistema - GUÍA RÁPIDA

## ⚡ Forma Más Rápida (TODO EN UNO)

```bash
chmod +x start-all.sh
./start-all.sh
```

Este script:
- ✅ Detecta si es primera vez y configura todo automáticamente
- ✅ Inicia backend y frontend juntos
- ✅ Muestra logs de ambos en la misma terminal
- 🛑 Ctrl+C detiene ambos servicios

---

## Primera Vez - Configuración Completa

### Opción 1: Script Automático (Recomendado)

```bash
# 1. Hacer scripts ejecutables
chmod +x setup-complete.sh

# 2. Ejecutar configuración completa
./setup-complete.sh
```

Este script automáticamente:
- ✅ Instala `python3-venv`
- ✅ Crea el entorno virtual
- ✅ Instala todas las dependencias Python
- ✅ Instala todas las dependencias npm
- ✅ Inicializa la base de datos con datos de prueba

---

### Opción 2: Paso a Paso Manual

```bash
# 1. Instalar python3-venv
sudo apt update
sudo apt install -y python3.11-venv python3-full

# 2. Configurar backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python3 init_db.py --with-data
deactivate
cd ..

# 3. Configurar frontend
npm install
```

---

## Iniciar el Sistema (Después de Configuración)

### Necesitas 2 Terminales:

**Terminal 1 - Backend:**
```bash
cd /workspaces/spark-template/backend
source venv/bin/activate
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /workspaces/spark-template
npm run dev
```

### O usa los scripts rápidos:

```bash
# Terminal 1
./start-backend.sh

# Terminal 2
./start-frontend.sh
```

---

## URLs de Acceso

- 🖥️ **Frontend:** http://localhost:5173
- 🔧 **Backend API:** http://localhost:8000
- 📖 **API Docs (Swagger):** http://localhost:8000/docs
- 📚 **API Docs (ReDoc):** http://localhost:8000/redoc

---

## Solución de Problemas

### Error: `ERR_BLOCKED_BY_CLIENT` o `Failed to fetch`

**Causa:** Bloqueador de anuncios o backend no está corriendo.

**Solución:**
1. Verifica que el backend esté corriendo: http://localhost:8000/docs
2. Desactiva bloqueadores de anuncios para localhost
3. Verifica que existe el archivo `.env`:
   ```bash
   cat .env
   # Debe mostrar: VITE_API_URL=http://localhost:8000/api
   ```
4. Si no existe `.env`, créalo:
   ```bash
   cp .env.example .env
   npm run dev  # Reinicia el frontend
   ```

**📖 [Ver Guía Completa de Solución de Problemas](SOLUCION_PROBLEMAS.md)**

---

### Error: `ModuleNotFoundError: No module named 'sqlalchemy'`
**Solución:** No activaste el entorno virtual
```bash
cd backend
source venv/bin/activate
```

### Error: `python3-venv not available`
**Solución:** Instala python3-venv
```bash
sudo apt install -y python3.11-venv python3-full
```

### Error: `venv/bin/activate: No such file or directory`
**Solución:** Crea el entorno virtual primero
```bash
cd backend
python3 -m venv venv
```

### Backend no arranca
**Solución:** Verifica que estés en el entorno virtual
```bash
cd backend
source venv/bin/activate
# Deberías ver (venv) al inicio del prompt
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Scripts Útiles

```bash
./setup-complete.sh      # Configuración completa (primera vez)
./test-system.sh         # Verificar estado del sistema
./start-backend.sh       # Iniciar backend
./start-frontend.sh      # Iniciar frontend
./validate-system.sh     # Validar configuración
```

---

## Verificar que Todo Funciona

1. ✅ Backend corriendo: Abre http://localhost:8000/docs
2. ✅ Frontend corriendo: Abre http://localhost:5173
3. ✅ Base de datos: Deberías ver productos y órdenes de prueba

---

## Siguiente Paso

Lee `NUEVO_SISTEMA_UBICACIONES.md` para entender el sistema V2.0 multi-ubicación.
