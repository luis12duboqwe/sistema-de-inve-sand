# 🚀 INICIO RÁPIDO - Sistema de Inventario V2.0

**⏱️ Tiempo total:** 5-10 minutos

---

## 🔥 Método Rápido (Recomendado)

### Terminal 1: Setup
```bash
bash setup.sh
```

Espera a que termine. Verás algo como:
```
✅ Permisos configurados
✅ Limpieza completada
✅ Dependencias Python instaladas
✅ BD creada
✅ npm iniciado en background
```

### Terminal 2: Backend
```bash
./start-backend.sh
```

Verás:
```
✅ Python 3.11.2 encontrado
📦 Verificando dependencias...
🚀 Iniciando FastAPI en puerto 8000...
```

**Déjalo corriendo** → no cierres esta terminal.

### Terminal 3: Frontend
```bash
./start-frontend.sh
```

Verás:
```
✅ Node.js vXX.X.X encontrado
✅ npm X.X.X encontrado
🚀 Iniciando servidor Vite...
🌐 Aplicación: http://localhost:5173
```

### 🌐 Abre en Navegador
```
http://localhost:5173
```

---

## ❌ Si bash setup.sh da error

### Solución A: Setup Manual
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 init_db.py --with-data
cd ..
npm install
```

Luego sigue con Terminal 2 y 3 (Backend y Frontend).

### Solución B: Paso a Paso
```bash
# Terminal 1 - Backend setup
cd backend
python3 -m pip install fastapi uvicorn sqlalchemy pydantic
python3 init_db.py --with-data

# Terminal 2 - Frontend setup
npm install

# Espera 2 minutos, luego:
# Terminal 1 - Backend
./start-backend.sh

# Terminal 2 - Frontend
./start-frontend.sh

# Terminal 3 - Navegador
http://localhost:5173
```

---

## ✅ Verificar que Todo Funciona

### Backend
```bash
curl http://localhost:8000/docs
```
Debería abrir Swagger UI en tu navegador.

### Frontend
```bash
http://localhost:5173
```
Debería cargar la aplicación React.

### Conexión API ↔ Frontend
En el navegador (F12 → Console):
```javascript
fetch('http://localhost:8000/api/products')
  .then(r => r.json())
  .then(d => console.log('✅ API OK:', d))
```

---

## 🔧 Puertos y URLs

| Servicio | URL | Descripción |
|----------|-----|-------------|
| Frontend | http://localhost:5173 | **↑ Abre esto en navegador** |
| Backend API | http://localhost:8000 | Servidor FastAPI |
| Swagger (Docs) | http://localhost:8000/docs | Probar endpoints |
| ReDoc | http://localhost:8000/redoc | Documentación |

---

## 🛠️ Troubleshooting Rápido

| Error | Solución |
|-------|----------|
| "No module named pip" | `bash install-pip.sh` (o `python3 -m ensurepip --upgrade`) |
| "Permission denied: ./start-backend.sh" | `chmod +x start-backend.sh start-frontend.sh` |
| "python3 not found" | Instala Python 3.11+ desde https://python.org |
| "npm not found" | Instala Node.js desde https://nodejs.org |
| "Port 8000 already in use" | `lsof -i :8000` y cierra el proceso que lo usa |
| "Port 5173 already in use" | `lsof -i :5173` y cierra el proceso que lo usa |
| "npm install still running" | Espera 1-2 minutos y retry `./start-frontend.sh` |
| "CORS error on frontend" | Asegúrate que backend esté corriendo en http://localhost:8000 |
| "Database locked" | Borra `backend/inventory.db` y reinicia todo |

---

## 📋 Requisitos Mínimos

- **Python 3.11+** → `python3 --version`
- **Node.js 18+** → `node --version`  
- **npm 9+** → `npm --version`
- **2GB RAM** (mínimo)
- **500MB disco** (para dependencies)

---

## 🎯 Próximos Pasos (Después de Iniciar)

1. **Crear Ubicación** → ⚙️ Settings → Locations → Add New
2. **Crear Perfil de Ventas** → Settings → Sales Profiles → Add New
3. **Agregar Productos** → Products → Add Product
4. **Hacer una Orden** → Orders → New Order
5. **Transferir Stock** → Products → Stock by Location

---

## 📚 Documentación Completa

- **Guía Completa**: [QUICK_START_FINAL.md](./QUICK_START_FINAL.md)
- **Setup Manual**: [SETUP_MANUAL.md](./SETUP_MANUAL.md)
- **Arquitectura V2.0**: [NUEVO_SISTEMA_UBICACIONES.md](./NUEVO_SISTEMA_UBICACIONES.md)
- **API Examples**: [api-examples-nuevo-sistema.json](./api-examples-nuevo-sistema.json)

---

## 💡 Tips

✨ **Nota de Usuario:** El primer `npm install` puede tomar 1-2 minutos. Es normal.

⚡ **Modo Rápido:** Si solo quieres probar:
```bash
# Instala deps directamente (sin venv)
cd backend && pip install -r requirements.txt && python3 init_db.py
cd .. && npm install
./start-backend.sh   # Terminal 1
./start-frontend.sh  # Terminal 2
```

🔄 **Reiniciar Sistema:** Si algo se daña:
```bash
# Limpiar e inicializar
rm -rf backend/venv backend/inventory.db node_modules
bash setup.sh
./start-backend.sh
./start-frontend.sh
```

---

**¿Problemas?** Revisa los logs en ambas terminales. Busca mensajes de error en rojo.

**Happy Inventory Managing! 📦✨**
