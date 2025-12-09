# 🚀 Guía Rápida para Empezar

## ⚡ Solución Rápida (Recomendado)

Si tienes error de permisos o problemas de venv, ejecuta esto **una sola vez**:

```bash
python3 setup-simple.py
```

Este script hará todo automáticamente:
- ✅ Da permisos a los scripts
- ✅ Limpia el venv anterior (si lo hay)
- ✅ Crea nuevo entorno virtual (intenta varias opciones si falla)
- ✅ Instala dependencias de Python
- ✅ Inicializa la base de datos
- ✅ Instala dependencias de Node.js (background)

## 🎯 Después de `setup-simple.py`, ejecuta:

### Terminal 1 - Backend
```bash
./start-backend.sh
```

### Terminal 2 - Frontend
```bash
./start-frontend.sh
```

### Abre en navegador
```
http://localhost:5173
```

---

## 🆘 Si Tienes Problemas

### Error al crear venv
```bash
python3 setup-simple.py
```

El script intenta:
1. `python3 -m venv` (estándar)
2. `python3 -m virtualenv` (alternativa)
3. Instala virtualenv si no está y lo intenta de nuevo

### "pip: Permission denied"
```bash
python3 setup-simple.py
```

### "No module named 'fastapi'"
```bash
python3 setup-simple.py
```

### "npm: command not found"
- Instala Node.js desde https://nodejs.org/
- Necesita Node 18+

---

## 📱 URLs del Sistema

Una vez que todo está corriendo:

- **Frontend**: http://localhost:5173 ← Abre aquí
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (interactivo)
- **ReDoc**: http://localhost:8000/redoc

---

## 📝 Archivos de Setup

| Archivo | Propósito | Cuándo usar |
|---------|-----------|-----------|
| `setup-simple.py` | Setup completo con fallovers | Primera vez o problemas graves |
| `setup.py` | Setup avanzado | Si prefieres más control |
| `start-backend.sh` | Iniciar backend | Todos los días |
| `start-frontend.sh` | Iniciar frontend | Todos los días |
| `reset_venv.py` | Limpiar/recrear venv | Si hay problemas con pip |

---

## ✅ Verificación

Para verificar que todo está configurado:

```bash
chmod +x test-system.sh
./test-system.sh
```

Esto chequeará:
- ✅ Node.js y npm
- ✅ Python y pip
- ✅ Estructura del proyecto
- ✅ Compilación TypeScript
- ✅ ESLint

---

## 💡 Tips

1. **Backend toma más tiempo en primera ejecución** (compilación)
2. **Usa Ctrl+C para detener** cualquier servidor
3. **El frontend recarga automáticamente** cuando cambias código (HMR)
4. **La BD es SQLite** - se crea automáticamente en `backend/inventory.db`
5. **npm install en background** - Mientras frontend compila, npm sigue instalando

---

**¡Listo! Sigue estos pasos y el sistema debería funcionar sin problemas.** 🎉
