# ⚡ INICIO RÁPIDO - Sistema Multi-Ubicación

## 🚀 En 3 Pasos

### PASO 1: Migrar Datos (5 minutos)

```bash
cd /workspaces/spark-template/backend
python3 migrate_to_locations_model.py
```

Este script automáticamente:
- ✅ Convierte tus Profiles antiguos en Locations (tiendas)
- ✅ Crea una Bodega Central
- ✅ Crea un SalesProfile por defecto
- ✅ Migra todo el stock
- ✅ Actualiza todas las órdenes

### PASO 2: Iniciar Backend (1 minuto)

```bash
cd /workspaces/spark-template/backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### PASO 3: Configurar tu Sistema (15 minutos)

#### A. Crear tus 3 tiendas + bodega

```bash
# Usa el archivo de ejemplos
# Ver: api-examples-nuevo-sistema.json

# O copia estos comandos:

# Tienda 1
curl -X POST http://localhost:8000/api/locations \
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

```bash
# Ver ubicaciones
curl http://localhost:8000/api/locations

# Ver perfiles de venta
curl http://localhost:8000/api/sales-profiles

# Ver productos (ahora globales)
curl http://localhost:8000/api/products
```

---

## 📚 Documentación Completa

- **Guía Completa:** `NUEVO_SISTEMA_UBICACIONES.md`
- **Resumen Visual:** `RESUMEN_VISUAL.md`
- **Ejemplos API:** `api-examples-nuevo-sistema.json`
- **Script Migración:** `backend/migrate_to_locations_model.py`

---

## 🆘 Ayuda Rápida

### ¿El backend no inicia?

```bash
# Instalar dependencias
cd backend
pip3 install -r requirements.txt

# Verificar que no haya errores
python3 -c "from app import models, schemas; print('OK')"
```

### ¿Error al migrar?

```bash
# Hacer backup primero
cp inventory.db inventory.db.backup

# Ejecutar migración con logs
python3 migrate_to_locations_model.py 2>&1 | tee migracion.log
```

### ¿Cómo pruebo los endpoints?

```bash
# Abrir en navegador
http://localhost:8000/docs

# O usar curl
curl http://localhost:8000/api/locations
```

---

## ✅ Checklist de Configuración

- [ ] Migración ejecutada exitosamente
- [ ] Backend corriendo en puerto 8000
- [ ] 3 tiendas creadas
- [ ] 1 bodega creada
- [ ] 10 perfiles de venta creados
- [ ] Productos visibles globalmente
- [ ] Primera orden de prueba creada

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
