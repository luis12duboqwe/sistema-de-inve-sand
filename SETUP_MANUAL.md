# 🔧 Pasos de Setup - Debido a Problemas de Entorno Virtual

El Codespace tiene problemas con `python3 -m venv`. He preparado dos soluciones:

## ✅ Solución Recomendada: Instalación Directa

Este script instala **directamente en Python del sistema** sin crear virtualenv:

```bash
bash setup.sh
```

**Qué hace:**
1. Da permisos a scripts
2. Limpia venv antiguo si existe
3. Instala FastAPI, uvicorn, SQLAlchemy directamente
4. Crea base de datos SQLite
5. Inicia npm install en background

**Tiempo estimado:** 2-3 minutos

## 📋 Si bash setup.sh da error, ejecuta manualmente:

### Paso 1: Backend Setup
```bash
cd backend
python3 -m pip install --upgrade pip
python3 -m pip install fastapi uvicorn sqlalchemy pydantic
python3 init_db.py --with-data
cd ..
```

### Paso 2: Frontend Setup
```bash
npm install
```

---

## 🚀 Después del Setup: Inicia los Servidores

### Terminal 1 - Backend
```bash
./start-backend.sh
```

Esperado:
```
✅ Python 3.11.2 encontrado
📦 Verificando dependencias...
🚀 Iniciando FastAPI en puerto 8000...
```

### Terminal 2 - Frontend
```bash
./start-frontend.sh
```

Esperado:
```
✅ Node.js vXX.X.X encontrado
✅ npm X.X.X encontrado
🚀 Iniciando servidor Vite...
🌐 Aplicación: http://localhost:5173
```

### Terminal 3 (Navegador)
```
http://localhost:5173
```

---

## ⚠️ Si npm install aún se ejecuta

El setup inicia npm en background. Si ves "npm not found", espera 1-2 minutos y retry:

```bash
./start-frontend.sh
```

---

## 🔍 Verificar que Todo Funcione

### Backend API
```bash
curl http://localhost:8000/docs
```

### Frontend
```bash
# En navegador:
http://localhost:5173
```

### Conexión API-Frontend
En navegador (F12 Console):
```javascript
fetch('http://localhost:8000/api/products')
  .then(r => r.json())
  .then(d => console.log('✅ API Connected!', d))
  .catch(e => console.error('❌ API Error:', e))
```

---

## 🛠️ Troubleshooting

| Problema | Solución |
|----------|----------|
| "python3: No module named pip" | `sudo apt install python3-pip` (Linux) |
| "npm not found" | `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh \| bash` |
| "Port 8000 already in use" | `lsof -i :8000` y mata el proceso |
| "CORS error en frontend" | Backend debe estar corriendo en http://localhost:8000 |
| "FastAPI error on startup" | Revisa `backend/inventory.db` existe y es válida |

---

## 📊 Estado Actual del Sistema

✅ **Backend:** Listo (FastAPI 0.115.0)
✅ **Frontend:** Listo (React + TypeScript)
✅ **Database:** V2.0 model (Locations + SalesProfiles)
✅ **Scripts:** Optimizados para instalación directa
✅ **Documentación:** Completa

**Próximo paso:** Ejecuta `bash setup.sh` 🚀
