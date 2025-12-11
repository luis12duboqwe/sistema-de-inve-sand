# 🏪 Guía del Nuevo Sistema de Inventario Multi-Ubicación

## 📋 Índice
1. [Visión General](#visión-general)
2. [Conceptos Clave](#conceptos-clave)
3. [Flujo de Trabajo](#flujo-de-trabajo)
4. [API Endpoints](#api-endpoints)
5. [Ejemplos de Uso](#ejemplos-de-uso)
6. [Migración desde el Modelo Anterior](#migración)

---

## 🎯 Visión General

El sistema ahora separa claramente dos conceptos:

### **Ubicaciones Físicas** (Locations)
- Tienda 1, Tienda 2, Tienda 3, Bodega, etc.
- Cada ubicación tiene su propio inventario
- El stock se maneja **por producto Y ubicación**

### **Perfiles de Venta** (Sales Profiles)
- Vendedores humanos, bots de IA, sistemas automáticos
- Cada perfil puede manejar WhatsApp, Facebook, Instagram
- **Todos los perfiles ven TODO el inventario** (de todas las ubicaciones)
- Al vender, especifican de qué ubicación toman el stock

---

## 🔑 Conceptos Clave

### 1. **Location (Ubicación Física)**
```json
{
  "id": 1,
  "nombre": "Tienda Centro",
  "tipo": "tienda",  // tienda | bodega | oficina
  "direccion": "Calle Principal #123",
  "telefono": "+504 1234-5678",
  "activo": true
}
```

### 2. **SalesProfile (Perfil de Venta)**
```json
{
  "id": 1,
  "name": "Bot WhatsApp 1",
  "slug": "bot-whatsapp-1",
  "tipo": "bot_ia",  // bot_ia | vendedor_humano | sistema_automatico
  "canales": ["whatsapp", "facebook"],
  "active": true,
  "configuracion": {
    "numero_whatsapp": "+504 9999-9999",
    "horario": "24/7"
  }
}
```

### 3. **Stock por Ubicación**
```json
{
  "product_id": 100,
  "location_id": 1,
  "cantidad_disponible": 5
}
```

Un mismo producto puede tener stock en múltiples ubicaciones:
- Producto X en Tienda 1: 5 unidades
- Producto X en Tienda 2: 3 unidades
- Producto X en Bodega: 10 unidades
- **Total disponible: 18 unidades**

### 4. **Order (Orden de Venta)**
```json
{
  "id": 1,
  "sales_profile_id": 1,      // Quién vendió (bot, vendedor, etc.)
  "source_location_id": 2,     // De dónde se tomó el stock
  "customer_name": "Juan Pérez",
  "customer_phone": "+504 8888-8888",
  "canal": "whatsapp",
  "metodo_pago": "efectivo",
  "total": 5000.00,
  "items": [...]
}
```

---

## 🔄 Flujo de Trabajo

### Escenario Completo

#### 1. **Configuración Inicial**

```bash
# Crear ubicaciones físicas
POST /api/locations
{
  "nombre": "Tienda 1 - Centro",
  "tipo": "tienda",
  "direccion": "Centro Comercial Plaza",
  "activo": true
}

POST /api/locations
{
  "nombre": "Tienda 2 - Norte",
  "tipo": "tienda",
  "direccion": "Barrio El Norte",
  "activo": true
}

POST /api/locations
{
  "nombre": "Bodega Central",
  "tipo": "bodega",
  "direccion": "Zona Industrial",
  "activo": true
}
```

#### 2. **Crear Perfiles de Venta (Bots/Vendedores)**

```bash
# Bot de WhatsApp 1
POST /api/sales-profiles
{
  "name": "Bot WhatsApp Principal",
  "slug": "bot-whatsapp-1",
  "tipo": "bot_ia",
  "canales": ["whatsapp"],
  "active": true,
  "configuracion": {
    "numero": "+504 9999-0001",
    "ia_modelo": "gpt-4"
  }
}

# Bot de Facebook/Instagram
POST /api/sales-profiles
{
  "name": "Bot Redes Sociales",
  "slug": "bot-social-1",
  "tipo": "bot_ia",
  "canales": ["facebook", "instagram"],
  "active": true
}

# Vendedor Humano
POST /api/sales-profiles
{
  "name": "María González",
  "slug": "vendedor-maria",
  "tipo": "vendedor_humano",
  "canales": ["whatsapp", "facebook"],
  "active": true
}
```

#### 3. **Agregar Productos (Ahora Globales)**

```bash
POST /api/products
{
  "sku": "SAM-S24-256-BLK",
  "nombre": "Samsung Galaxy S24",
  "categoria": "celular",
  "marca": "Samsung",
  "modelo": "S24",
  "capacidad": "256GB",
  "condicion": "nuevo",
  "precio": 15000.00,
  "moneda": "HNL"
  # Ya no se requiere profile_id - el producto es global
}
```

#### 4. **Asignar Stock por Ubicación**

```bash
# Agregar 10 unidades en Tienda 1
POST /api/products/{product_id}/stock/location/{location_id}
{
  "cantidad": 10
}

# Agregar 5 unidades en Tienda 2
POST /api/products/{product_id}/stock/location/{location_id_2}
{
  "cantidad": 5
}

# Agregar 20 unidades en Bodega
POST /api/products/{product_id}/stock/location/{warehouse_id}
{
  "cantidad": 20
}
```

#### 5. **Ver Inventario Completo**

```bash
# Inventario total de un producto
GET /api/products/{product_id}/stock/total
# Respuesta: { "total": 35, "ubicaciones": [...] }

# Stock por ubicación
GET /api/locations/{location_id}/stock
```

#### 6. **Crear Orden desde un Bot**

```bash
POST /api/orders
{
  "sales_profile_id": 1,        # Bot WhatsApp 1
  "source_location_id": 1,      # Tomar stock de Tienda 1
  "customer_name": "Carlos López",
  "customer_phone": "+504 8888-8888",
  "canal": "whatsapp",
  "metodo_pago": "transferencia",
  "items": [
    {
      "product_id": 100,
      "cantidad": 2
    }
  ]
}
```

El sistema automáticamente:
- ✅ Reduce el stock en la ubicación especificada
- ✅ Registra quién vendió (sales_profile_id)
- ✅ Registra de dónde salió el stock (source_location_id)
- ✅ Crea historial de movimientos

#### 7. **Transferir Stock entre Ubicaciones**

```bash
POST /api/stock-transfers
{
  "product_id": 100,
  "from_location_id": 3,      # Bodega
  "to_location_id": 1,        # Tienda 1
  "cantidad": 5,
  "notas": "Reabastecimiento semanal"
}
```

---

## 🔌 API Endpoints

### **Locations**
```
GET    /api/locations                 # Listar ubicaciones
GET    /api/locations/{id}            # Obtener ubicación
POST   /api/locations                 # Crear ubicación
PUT    /api/locations/{id}            # Actualizar ubicación
DELETE /api/locations/{id}            # Eliminar ubicación
GET    /api/locations/{id}/stock      # Ver stock de ubicación
```

### **Sales Profiles**
```
GET    /api/sales-profiles            # Listar perfiles de venta
GET    /api/sales-profiles/{id}       # Obtener perfil
GET    /api/sales-profiles/slug/{slug}  # Obtener por slug
POST   /api/sales-profiles            # Crear perfil
PUT    /api/sales-profiles/{id}       # Actualizar perfil
DELETE /api/sales-profiles/{id}       # Eliminar perfil
GET    /api/sales-profiles/{id}/orders  # Órdenes del perfil
```

### **Products** (Modificado)
```
GET    /api/products                  # Todos los productos (globales)
POST   /api/products                  # Crear producto (sin profile_id)
GET    /api/products/{id}/stock/total # Stock total (todas ubicaciones)
GET    /api/products/{id}/stock/by-location  # Stock por cada ubicación
```

### **Orders** (Modificado)
```
POST   /api/orders
{
  "sales_profile_id": 1,      # NUEVO - requerido
  "source_location_id": 1,    # NUEVO - requerido
  ...
}
```

### **Stock Transfers** (Modificado)
```
POST   /api/stock-transfers
{
  "from_location_id": 1,      # NUEVO - ubicación origen
  "to_location_id": 2,        # NUEVO - ubicación destino
  ...
}
```

---

## 📝 Ejemplos de Uso

### Ejemplo 1: Dashboard de Inventario Global

```javascript
// Ver TODO el inventario
const response = await fetch('/api/products?activo=true');
const products = await response.json();

// Para cada producto, mostrar stock por ubicación
for (const product of products) {
  const stockRes = await fetch(`/api/products/${product.id}/stock/by-location`);
  const stock = await stockRes.json();
  
  console.log(`${product.nombre}:`);
  console.log(`  Tienda 1: ${stock.tienda1 || 0}`);
  console.log(`  Tienda 2: ${stock.tienda2 || 0}`);
  console.log(`  Bodega: ${stock.bodega || 0}`);
  console.log(`  TOTAL: ${stock.total}`);
}
```

### Ejemplo 2: Bot de WhatsApp Vendiendo

```javascript
// Bot recibe mensaje de cliente
const orden = {
  sales_profile_id: getBotSalesProfileId(),  // ID del bot
  source_location_id: await elegirMejorUbicacion(producto_id),
  customer_name: clienteNombre,
  customer_phone: clienteTelefono,
  canal: "whatsapp",
  metodo_pago: "transferencia",
  items: [
    { product_id: producto_id, cantidad: 1 }
  ]
};

const response = await fetch('/api/orders', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(orden)
});

// El stock se reduce automáticamente de la ubicación especificada
```

### Ejemplo 3: Reportes por Vendedor/Bot

```javascript
// Ver cuánto ha vendido cada perfil
const profiles = await fetch('/api/sales-profiles').then(r => r.json());

for (const profile of profiles) {
  const orders = await fetch(`/api/sales-profiles/${profile.id}/orders`).then(r => r.json());
  
  const totalVentas = orders.reduce((sum, order) => sum + order.total, 0);
  
  console.log(`${profile.name}:`);
  console.log(`  Canales: ${profile.canales.join(', ')}`);
  console.log(`  Órdenes: ${orders.length}`);
  console.log(`  Total vendido: L ${totalVentas}`);
}
```

---

## 🔄 Migración desde el Modelo Anterior

### Paso 1: Backup

```bash
# Hacer backup de la base de datos
cp inventory.db inventory.db.backup
```

### Paso 2: Ejecutar Migración

```bash
cd backend
python migrate_to_locations_model.py
```

El script migrará automáticamente:
- ✅ Profiles → Locations (cada perfil se convierte en tienda)
- ✅ Crea "Bodega Central" como ubicación adicional
- ✅ Crea "Sistema Principal" como SalesProfile por defecto
- ✅ Migra todo el stock a la nueva estructura
- ✅ Actualiza todas las órdenes existentes
- ✅ Actualiza transferencias e historial

### Paso 3: Verificar

```bash
# Ver ubicaciones creadas
curl http://localhost:8000/api/locations

# Ver perfiles de venta
curl http://localhost:8000/api/sales-profiles

# Ver productos (ahora globales)
curl http://localhost:8000/api/products
```

---

## 🎯 Ventajas del Nuevo Modelo

### ✅ Separación de Conceptos
- **Ubicaciones físicas** ≠ **Canales de venta**
- Claridad en dónde está el inventario vs quién lo vende

### ✅ Escalabilidad
- Agregar 10+ bots de IA sin duplicar inventario
- Cada bot ve TODO el inventario disponible
- Flexibilidad para elegir de dónde tomar stock

### ✅ Trazabilidad Completa
- Sabes quién vendió (sales_profile_id)
- Sabes de dónde salió el stock (source_location_id)
- Historial detallado por ubicación

### ✅ Multi-Canal Real
- Un perfil maneja WhatsApp, Facebook, Instagram
- Múltiples perfiles pueden vender el mismo producto
- No hay duplicación de datos

### ✅ Gestión Inteligente
- Transferencias entre ubicaciones físicas
- Stock consolidado vs stock por ubicación
- Reportes por vendedor y por tienda

---

## 🚀 Roadmap Futuro

### Funcionalidades Planeadas

1. **Asignación Automática de Stock**
   - El sistema elige automáticamente la mejor ubicación
   - Basado en: cercanía, disponibilidad, costo de envío

2. **Sincronización con n8n**
   - Bots de WhatsApp consultan inventario en tiempo real
   - Crean órdenes automáticamente
   - Notificaciones cuando stock está bajo

3. **Dashboard Avanzado**
   - Vista consolidada de todas las ubicaciones
   - Alertas de stock bajo por ubicación
   - Métricas de ventas por perfil/canal

4. **Multi-Moneda por Ubicación**
   - Tienda en Honduras: HNL
   - Tienda en USA: USD
   - Conversión automática

---

## 📞 Soporte

Si tienes preguntas sobre el nuevo modelo:

1. Revisa los endpoints en: `http://localhost:8000/docs`
2. Consulta ejemplos de migración en: `migrate_to_locations_model.py`
3. Prueba los endpoints con el archivo de ejemplos API

---

**Versión:** 2.0.0  
**Última actualización:** Diciembre 2025
