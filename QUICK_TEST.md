# 📝 Comandos de Prueba Rápida

## 🚀 Inicio Rápido

### Opción 1: Scripts Automáticos (Recomendado)

**Linux/Mac:**
```bash
# 1. Dar permisos (solo primera vez)
chmod +x *.sh

# 2. Ejecutar pruebas completas
./test-system.sh

# 3. Iniciar servicios
./start-backend.sh   # Terminal 1
./start-frontend.sh  # Terminal 2
```

**Windows:**
```cmd
start-backend.bat   # Terminal 1
start-frontend.bat  # Terminal 2
```

### Opción 2: Manual

#### Backend
```bash
cd backend

# Crear entorno virtual (solo primera vez)
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows

# Instalar dependencias
pip install -r requirements.txt

# Inicializar BD (solo primera vez)
python3 init_db.py

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
# Instalar dependencias (solo primera vez)
npm install

# Iniciar servidor de desarrollo
npm run dev
```

## 🧪 Pruebas

### Pruebas Automatizadas del Backend
```bash
# Backend debe estar corriendo primero
pip install requests  # Solo primera vez
python3 test-backend.py
```

### Pruebas Manuales

1. **Health Check:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Ver documentación API:**
   - http://localhost:8000/docs
   - http://localhost:8000/redoc

3. **Crear perfil:**
   ```bash
   curl -X POST http://localhost:8000/api/profiles \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Mi Tienda",
       "email": "admin@mitienda.com",
       "phone": "+1234567890",
       "password": "admin123",
       "business_name": "Mi Negocio"
     }'
   ```

4. **Login:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@mitienda.com",
       "password": "admin123"
     }'
   ```

5. **Crear producto (necesita token):**
   ```bash
   TOKEN="tu_token_aqui"
   curl -X POST http://localhost:8000/api/products \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "iPhone 15 Pro",
       "barcode": "IP15PRO001",
       "price": 999.99,
       "cost": 750.00,
       "stock": 10,
       "category": "Smartphones"
     }'
   ```

## 🔍 Verificar Estado

### Verificar puertos en uso
```bash
# Linux/Mac
lsof -i :8000  # Backend
lsof -i :5173  # Frontend

# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :5173
```

### Matar procesos si es necesario
```bash
# Linux/Mac
kill -9 <PID>

# Windows
taskkill /PID <PID> /F
```

### Ver logs en tiempo real
```bash
# Backend
tail -f backend/logs/app.log  # Si existe

# Frontend (abrir DevTools en navegador)
# Presiona F12 > Console
```

## 🎯 Checklist de Funcionalidad

Después de iniciar ambos servidores, verifica:

- [ ] Frontend carga en http://localhost:5173
- [ ] Backend responde en http://localhost:8000/health
- [ ] Docs API accesible en http://localhost:8000/docs
- [ ] Puedes crear un perfil desde la UI
- [ ] Puedes hacer login
- [ ] Puedes crear productos
- [ ] Puedes crear pedidos
- [ ] Dashboard muestra estadísticas
- [ ] No hay errores en consola (F12)

## 🐛 Solución de Problemas

### Error: Puerto en uso
```bash
# Encuentra y mata el proceso
lsof -i :8000  # Buscar PID
kill -9 <PID>  # Matar proceso
```

### Error: Base de datos bloqueada
```bash
cd backend
rm inventory.db  # Eliminar DB
python3 init_db.py  # Recrear DB
```

### Error: Módulos no encontrados (Backend)
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Error: Módulos no encontrados (Frontend)
```bash
rm -rf node_modules package-lock.json
npm install
```

### Error: CORS
- Verifica que el backend esté corriendo
- Verifica la configuración CORS en `backend/app/main.py`

### Frontend no compila
```bash
npm run optimize  # Optimizar dependencias de Vite
npm run dev
```

## 📊 Monitoreo

### Ver uso de recursos
```bash
# CPU y memoria
top

# Específico de Node/Python
ps aux | grep node
ps aux | grep python
```

### Tamaño de la base de datos
```bash
du -h backend/inventory.db
```

### Logs del sistema
```bash
# Backend
# Los errores aparecen en la terminal donde se ejecuta uvicorn

# Frontend  
# Abrir DevTools (F12) > Console
```

## 🎨 Pruebas de UI

1. **Desktop (1920x1080)**
   - Abrir navegador en pantalla completa
   - Probar todas las funciones

2. **Tablet (768x1024)**
   - F12 > Toggle device toolbar
   - Seleccionar iPad
   - Probar navegación

3. **Mobile (375x667)**
   - F12 > Toggle device toolbar
   - Seleccionar iPhone SE
   - Probar menú mobile

## 📈 Pruebas de Rendimiento

### Crear datos de prueba masivos
```bash
# Backend debe estar corriendo
python3 -c "
import requests
token = 'tu_token_aqui'
headers = {'Authorization': f'Bearer {token}'}
for i in range(100):
    requests.post('http://localhost:8000/api/products', 
        json={'name': f'Producto {i}', 'price': 99.99, 'stock': 10},
        headers=headers)
"
```

### Medir tiempo de carga
- Abrir DevTools (F12)
- Network tab
- Recargar página
- Ver "DOMContentLoaded" y "Load" times

## ✅ Comandos de Verificación Final

```bash
# 1. Backend activo
curl http://localhost:8000/health

# 2. Frontend activo
curl http://localhost:5173

# 3. Pruebas automatizadas
python3 test-backend.py

# 4. TypeScript sin errores
npx tsc --noEmit

# 5. ESLint
npm run lint
```

## 🔗 URLs Importantes

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- API Docs (ReDoc): http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## 📚 Documentación Adicional

- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Guía completa de pruebas
- [INTEGRATION.md](./INTEGRATION.md) - Integración con chatbots
- [SECURITY.md](./SECURITY.md) - Seguridad y autenticación
- [REALTIME_SYNC.md](./REALTIME_SYNC.md) - Sincronización en tiempo real
- [backend/README.md](./backend/README.md) - Documentación del backend
