# ⚡ INICIO RÁPIDO - Sistema Multi-Ubicación V2.0

## 🚀 Iniciar el Sistema (2 Pasos)

### PASO 1: Iniciar Backend

```bash
cd backend
source venv/bin/activate  # Si ya existe venv, sino: python3 -m venv venv
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O usa el script:
```bash
./start-backend.sh
```

### PASO 2: Iniciar Frontend (en otra terminal)

```bash
npm run dev
```

O usa el script:
```bash
./start-frontend.sh
```

**URLs:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs

---

## 📋 Primera Configuración (Solo si es tu primera vez)

### A. Migrar Datos (Si vienes de V1.0)

```bash
cd backend
python3 migrate_to_locations_model.py
```

Este script automáticamente:
- ✅ Convierte Profiles antiguos en Locations (tiendas)
- ✅ Crea una Bodega Central
- ✅ Crea un SalesProfile por defecto
- ✅ Migra todo el stock
- ✅ Actualiza todas las órdenes

### B. O Inicializar Base de Datos Nueva

```bash
cd backend
python3 init_db.py --with-data
```

Esto crea:
- 2 ubicaciones de ejemplo (Tienda 1, Bodega Central)
- 1 perfil de venta (Bot WhatsApp)
- Productos de ejemplo con stock

---

## 🏪 Configurar tu Sistema

### 1. Crear Ubicaciones (desde la UI o API)

```bash
# Usa el archivo de ejemplos
# Ver: api-examples-nuevo-sistema.json

# O copia estos comandos:

# Tienda 1
curl -X POST http://localhost:8000/api/locations \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Tienda 1 - Centro",
    "tipo": "tienda",
    "direccion": "Tu dirección aquí",
    "activo": true
  }'

# Repetir para Tienda 2, Tienda 3, y Bodega
```

#### B. Crear tus 10 perfiles de venta (bots/vendedores)

```bash
# Bot WhatsApp 1
curl -X POST http://localhost:8000/api/sales-profiles \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bot WhatsApp 1",
    "slug": "bot-whatsapp-1",
    "tipo": "bot_ia",
    "canales": ["whatsapp"],
    "active": true
  }'

# Repetir para crear más bots...
```

#### C. Ver que todo funciona

**Desde la UI:**
- Ve a la pestaña "Ubicaciones"
- Click en "Nueva Ubicación"
- Completa: Nombre, Tipo (tienda/bodega/oficina), Dirección
- Repite para crear todas tus ubicaciones

**Desde la API:**
```bash
curl -X POST http://localhost:8000/api/locations \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Tienda Centro",
    "tipo": "tienda",
    "direccion": "Calle Principal #123",
    "activo": true
  }'
```

### 2. Crear Perfiles de Venta

**Desde la UI:**
- Ve a la pestaña "Perfiles de Venta"
- Click en "Nuevo Perfil"
- Completa: Nombre, Tipo (bot_ia/vendedor_humano), Canales
- Repite para cada vendedor/bot

**Desde la API:**
```bash
curl -X POST http://localhost:8000/api/sales-profiles \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bot WhatsApp Tienda 1",
    "slug": "bot-whatsapp-t1",
    "tipo": "bot_ia",
    "canales": ["whatsapp", "facebook"],
    "active": true
  }'
```

### 3. Agregar Productos

**Desde la UI:**
- Ve a la pestaña "Productos"
- Click en "Agregar Producto"
- Completa información del producto
- Selecciona ubicación para stock inicial
- El producto será visible para TODOS los perfiles de venta

---

## 📚 Documentación Completa

- **[NUEVO_SISTEMA_UBICACIONES.md](./NUEVO_SISTEMA_UBICACIONES.md)** - Arquitectura completa
- **[SISTEMA_TRANSFERENCIAS_V2.md](./SISTEMA_TRANSFERENCIAS_V2.md)** - Transferencias con reservas
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - Guía de pruebas
- **[api-examples-nuevo-sistema.json](./api-examples-nuevo-sistema.json)** - Ejemplos API
- **[Backend README](./backend/README.md)** - Documentación backend

---

## 🆘 Solución de Problemas

### Backend no inicia

```bash
cd backend
pip3 install -r requirements.txt
python3 -c "from app import models, schemas; print('✅ Módulos OK')"
```

### Error en migración

```bash
# Hacer backup
cp backend/inventory.db backend/inventory.db.backup

# Ejecutar con logs
cd backend
python3 migrate_to_locations_model.py 2>&1 | tee migracion.log
```

### Probar endpoints

Abre http://localhost:8000/docs en tu navegador para la documentación interactiva.

---

## ✅ Checklist Post-Instalación

- [ ] Backend corriendo en puerto 8000
- [ ] Frontend corriendo en puerto 5173
- [ ] Base de datos inicializada
- [ ] Ubicaciones creadas (tiendas/bodegas)
- [ ] Perfiles de venta configurados
- [ ] Productos agregados con stock
- [ ] Primera orden de prueba realizada
- [ ] Transferencia de prueba ejecutada

---

## 🎯 Endpoints Clave

```
📍 Ubicaciones:
GET    /api/locations
POST   /api/locations
GET    /api/locations/{id}/stock

🤖 Perfiles de Venta:
GET    /api/sales-profiles
POST   /api/sales-profiles
GET    /api/sales-profiles/{id}/orders

📦 Productos (Globales):
GET    /api/products
POST   /api/products

🛒 Órdenes:
POST   /api/orders
{
  "sales_profile_id": 1,
  "source_location_id": 1,
  ...
}

🔄 Transferencias:
POST   /api/stock-transfers
{
  "from_location_id": 4,
  "to_location_id": 1,
  ...
}
```

---

**¡Listo para empezar! 🚀**
