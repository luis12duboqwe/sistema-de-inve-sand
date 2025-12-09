# 🔧 Solución de Problemas - Sistema de Inventario

## 🚨 Error: `ERR_BLOCKED_BY_CLIENT` o `Failed to fetch` ⭐ MÁS COMÚN

### Causa Principal
**Un bloqueador de anuncios está bloqueando las peticiones al backend.**

Los bloqueadores como uBlock Origin, Adblock Plus, etc., bloquean URLs que contienen palabras como:
- `/api/`
- `/ads/`
- `/tracking/`
- Etc.

### ✅ Solución Inmediata (2 minutos)

#### Opción 1: Desactivar Bloqueador (Recomendado)

**uBlock Origin:**
1. Clic en el **ícono de uBlock** 🛡️ en la barra de herramientas
2. Clic en el **botón grande de apagado** (power button)
3. Recarga la página (F5)

**Adblock Plus:**
1. Clic en el **ícono de Adblock** 🚫
2. Seleccionar **"Pausar Adblock Plus"**
3. Recarga la página (F5)

**Brave Browser:**
1. Clic en el **ícono del león** (Brave Shields)
2. **Desactivar "Shields"** para este sitio
3. Recarga la página (F5)

#### Opción 2: Lista Blanca (Permanente)

**uBlock Origin:**
1. Clic en el ícono de uBlock
2. Clic en el **engranaje** ⚙️ (Abrir el panel de control)
3. Ir a la pestaña **"Lista blanca"**
4. Agregar:
   ```
   localhost:5173
   localhost:8000
   ```
5. Clic en **"Aplicar cambios"**
6. Recarga la página (F5)

**Adblock Plus:**
1. Clic en el ícono de Adblock
2. **Configuración** → **Lista blanca**
3. Agregar: `localhost`
4. Guardar

#### Opción 3: Modo Incógnito (Temporal)

Los bloqueadores suelen estar desactivados en modo incógnito:

- **Chrome/Edge:** `Ctrl + Shift + N`
- **Firefox:** `Ctrl + Shift + P`
- **Safari:** `Cmd + Shift + N` (Mac)

Luego abre: http://localhost:5173

### 🔍 Verificación

Después de desactivar el bloqueador, verifica:

✅ **Dashboard sin advertencia amarilla**
✅ **Consola sin errores** (F12 → Console)
✅ **Pestañas de estadísticas funcionan**

### 📖 Ver Guía Visual

Lee: `ERROR_BLOQUEADOR.txt` para instrucciones detalladas

---

## ❌ Error: `ModuleNotFoundError: No module named 'sqlalchemy'`

### Causa
No activaste el entorno virtual de Python.

### Solución
```bash
cd backend
source venv/bin/activate
# Deberías ver (venv) al inicio del prompt
```

---

## ❌ Error: `python3-venv not available`

### Causa
Falta el paquete `python3-venv`.

### Solución
```bash
sudo apt update
sudo apt install -y python3.11-venv python3-full
```

---

## ❌ Error: `venv/bin/activate: No such file or directory`

### Causa
El entorno virtual no existe.

### Solución
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

O usa el script automático:
```bash
./setup-complete.sh
```

---

## ❌ Frontend muestra pantalla en blanco

### Causa
1. Error de JavaScript en el navegador
2. Backend no está respondiendo

### Solución

1. **Abrir consola del navegador** (F12)
   - Busca errores en la pestaña "Console"
   
2. **Verificar backend:**
   ```bash
   curl http://localhost:8000/api/locations
   ```
   
3. **Verificar .env:**
   ```bash
   cat .env
   # Debe contener: VITE_API_URL=http://localhost:8000/api
   ```

4. **Limpiar caché y reiniciar:**
   ```bash
   # Presiona Ctrl+C
   rm -rf node_modules/.vite
   npm run dev
   ```

---

## ❌ Backend no inicia - Puerto en uso

### Error
```
Error: Address already in use
```

### Causa
Otro proceso está usando el puerto 8000.

### Solución

**Opción 1: Matar el proceso**
```bash
lsof -ti:8000 | xargs kill -9
```

**Opción 2: Usar otro puerto**
```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Luego actualiza `.env`:
```
VITE_API_URL=http://localhost:8001/api
```

---

## ❌ Base de datos vacía / Sin datos

### Solución
```bash
cd backend
source venv/bin/activate
python3 init_db.py --with-data
```

---

## ❌ Frontend no inicia - Puerto 5173 en uso

### Solución

**Opción 1: Matar el proceso**
```bash
lsof -ti:5173 | xargs kill -9
npm run dev
```

**Opción 2: Vite asignará otro puerto automáticamente**
- Vite mostrará algo como: `http://localhost:5174`
- Usa ese puerto en el navegador

---

## 🔍 Verificar estado completo del sistema

```bash
./test-system.sh
```

Este script verifica:
- ✅ Node.js y npm instalados
- ✅ Python y pip instalados
- ✅ Archivos del proyecto presentes
- ✅ Dependencias instaladas
- ✅ Base de datos inicializada

---

## 🆘 Solución Nuclear (Reiniciar Todo)

Si nada funciona, resetea completamente:

```bash
# 1. Detener todo (Ctrl+C en ambas terminales)

# 2. Limpiar backend
cd backend
rm -rf venv inventory.db
cd ..

# 3. Limpiar frontend
rm -rf node_modules .vite

# 4. Reinstalar todo
./setup-complete.sh

# 5. Iniciar
./start-all.sh
```

---

## 📞 Verificaciones Rápidas

### Backend funcionando?
```bash
curl http://localhost:8000/api/locations
```

### Frontend funcionando?
Abre: http://localhost:5173

### Logs del backend
Busca errores en la terminal donde corre el backend

### Logs del frontend
- Abre DevTools (F12) → Console
- Busca errores en rojo

---

## 💡 Tips

1. **Siempre activa el entorno virtual** antes de trabajar con el backend
2. **Reinicia el frontend** después de cambiar `.env`
3. **Usa 2 terminales separadas** para ver los logs de cada servicio
4. **Desactiva bloqueadores** para localhost durante desarrollo
5. **Verifica que ambos servicios estén corriendo** antes de reportar problemas

---

## 📚 Documentación Relacionada

- `COMO_LEVANTAR_SISTEMA.md` - Guía de inicio
- `SCRIPTS_ACTUALIZADOS.md` - Scripts disponibles
- `README.md` - Información general
