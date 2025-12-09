# 🚀 Quick Start - Sistema de Inventario Multi-Ubicación V2.0

## ⚡ Inicio Rápido (3 Pasos)

### 1️⃣ Setup Inicial
Instala dependencias de Python y Node.js:

```bash
bash setup.sh
```

**Qué hace:**
- ✅ Da permisos a scripts
- ✅ Instala paquetes Python (FastAPI, SQLAlchemy, etc.)
- ✅ Crea BD SQLite con V2.0
- ✅ Inicia npm install (en background)

> **Si npm aún se está instalando:** espera 1-2 minutos antes de ejecutar el paso 2.

### 2️⃣ Backend (Terminal 1)

```bash
./start-backend.sh
```

Verás:
```
✅ Python 3.11.2 encontrado
📦 Verificando dependencias...
📊 Verificando base de datos...
✅ BD existe

🚀 Iniciando FastAPI en puerto 8000...
```

**URLs Backend:**
- API: http://localhost:8000
- Swagger (testing): http://localhost:8000/docs
- ReDoc (docs): http://localhost:8000/redoc

### 3️⃣ Frontend (Terminal 2)

```bash
./start-frontend.sh
```

Verás:
```
✅ Node.js v18.x.x encontrado
✅ npm x.x.x encontrado
✅ Dependencias ya instaladas

🚀 Iniciando servidor Vite...
🌐 Aplicación: http://localhost:5173
```

**Abre en el navegador:**
```
http://localhost:5173
```

---

## 📋 Requisitos

- **Python 3.11+** - Verifica con `python3 --version`
- **Node.js 18+** - Verifica con `node --version`
- **npm** - Verifica con `npm --version`

---

## 🎯 Modos de Operación

### Local Mode (Por defecto)
- ✅ Datos en navegador (IndexedDB + localStorage)
- ✅ No requiere backend
- ✅ Perfecto para desarrollo rápido
- ⚠️ Datos se pierden si borras cache

### API Mode
- ✅ Datos en servidor FastAPI
- ✅ Persistencia en SQLite
- ✅ Multi-usuario
- ✅ Requiere backend corriendo

**Cambiar modo:** Abre Settings (⚙️) en la app → "Usar API backend" → Reload página

---

## 🛠️ Solución de Problemas

### Error: "Python3 not found"
```bash
# Instala Python 3.11+ desde https://www.python.org/
# O en Linux/Mac:
# Linux: sudo apt install python3
# Mac: brew install python3
```

### Error: "npm not found"
```bash
# Instala Node.js desde https://nodejs.org/ (incluye npm)
```

### FastAPI no responde
```bash
# Verifica que esté escuchando en puerto 8000
lsof -i :8000

# O reinicia manualmente en backend/:
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### npm install sigue ejecutándose
```bash
# Espera a que termine (~2 min)
# O cancela setup y ejecuta manualmente:
npm install

# Luego inicia frontend:
npm run dev
```

### Base de datos corrupta
```bash
# Borra e inicializa nuevamente:
cd backend
rm inventory.db
python3 init_db.py --with-data
cd ..

# Luego reinicia backend
./start-backend.sh
```

---

## 📁 Estructura de Carpetas

```
spark-template/
├── backend/               # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py       # Entrada FastAPI
│   │   ├── models.py     # V2.0 schema (Location, SalesProfile, etc)
│   │   ├── routers/      # Endpoints por recurso
│   │   └── config.py     # Configuración
│   ├── init_db.py        # Inicializar BD
│   └── requirements.txt   # Dependencias Python
│
├── src/                   # React + TypeScript
│   ├── App.tsx           # Componente principal
│   ├── components/       # 42 componentes React
│   ├── lib/
│   │   ├── apiClient.ts  # HTTP client
│   │   ├── inventoryService.ts  # Lógica local
│   │   └── inventoryServiceFactory.ts  # Dual-mode
│   └── hooks/            # Custom hooks (useKV, etc)
│
├── setup.sh              # Setup inicial
├── start-backend.sh      # Inicia FastAPI
└── start-frontend.sh     # Inicia Vite
```

---

## 🔑 Funcionalidades V2.0

### Ubicaciones Múltiples
- Tienda 1, Tienda 2, Bodega Central
- Cada ubicación tiene su propio stock
- Transferencias automáticas entre ubicaciones

### Perfiles de Ventas
- Bot IA (automático)
- Vendedor Humano (manual)
- Sistema Automático (integraciones)
- Cada perfil maneja múltiples canales (WhatsApp, Facebook, Instagram)

### Productos Global
- Catálogo unificado
- Stock calculado como suma de todas las ubicaciones
- Múltiples IMEIs por producto

### Órdenes Inteligentes
- Rastreo completo (qué, dónde, quién, cuándo)
- Historial de stock automático
- Métodos de pago múltiples

---

## 🧪 Testing

### Verificar Backend
```bash
curl http://localhost:8000/docs
```
Abre Swagger UI para probar endpoints interactivamente.

### Verificar Frontend
```bash
# Abre http://localhost:5173 en navegador
# Debería cargar la aplicación React
```

---

## 📚 Documentación Completa

- **Arquitectura V2.0**: `NUEVO_SISTEMA_UBICACIONES.md`
- **API Examples**: `api-examples-nuevo-sistema.json`
- **Guía de Testing**: `TESTING_GUIDE.md`
- **Integración**: `INTEGRATION.md`

---

## ⚡ Atajos Útiles

| Atajo | Acción |
|-------|--------|
| `Ctrl+K` | Paleta de comandos (búsqueda global) |
| `Ctrl+N` | Nuevo producto |
| `Ctrl+O` | Nueva orden |
| `Ctrl+S` | Sincronizar datos |
| `?` | Ayuda dentro de la app |

---

## 🐛 Debugging

### Ver logs del backend
```bash
# Terminal backend mostrará todos los logs
# Busca "INFO:", "ERROR:", "WARNING:"
```

### Ver logs del frontend
```bash
# En navegador: F12 → Console
# Busca errores en rojo
```

### Conexión API
```bash
# En navegador Console:
fetch('http://localhost:8000/api/products')
  .then(r => r.json())
  .then(d => console.log(d))
```

---

## 🎓 Próximos Pasos

1. **Crea tu primera ubicación**
   - Settings → Locations → Add New

2. **Crea perfil de ventas**
   - Settings → Sales Profiles → Add New

3. **Agrega productos**
   - Products → Add Product

4. **Prueba una venta**
   - Orders → New Order

5. **Transfiere stock**
   - Products → Stock by Location

---

## 💡 Tips Pro

- **Cambio rápido de modo**: Settings → "Usar API backend" → Reload
- **Limpiar datos locales**: DevTools → Application → Storage → Clear All
- **Migrar BD desde V1**: Ejecuta `python migrate_to_locations_model.py` en backend/
- **Aumentar logs**: En backend edita `app/main.py` y agrega `logging.basicConfig(level=DEBUG)`

---

**¿Problemas?** Revisa los logs en ambas terminales y abre una issue en GitHub.

**Happy Inventory Managing! 📦**
