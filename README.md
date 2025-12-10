# 📦 Sistema de Inventario Multi-Ubicación para Ventas Online

## 🚀 INICIO RÁPIDO (2 Comandos)

```bash
# 1. Inicio automático (RECOMENDADO)
chmod +x start-all.sh && ./start-all.sh

# 2. O inicio manual en terminales separadas
./start-backend.sh    # Terminal 1 - Backend
./start-frontend.sh   # Terminal 2 - Frontend
```

**URLs después de iniciar:**
- 🖥️ **Frontend:** http://localhost:5173
- 🔧 **Backend API:** http://localhost:8000/docs

**📖 [Ver Guía Completa de Inicio](INICIO_RAPIDO.md) | [Arquitectura V2.0](NUEVO_SISTEMA_UBICACIONES.md)**

---

## 🎯 Versión 2.0 - Sistema Completamente Rediseñado ✅

Un sistema avanzado de gestión de inventario diseñado para **múltiples ubicaciones físicas** y **múltiples canales de venta** online (WhatsApp, Facebook, Instagram).

### 🆕 NUEVA ARQUITECTURA V2.0

**Sistema de Ubicaciones y Perfiles de Venta Independientes:**
- 📍 **Ubicaciones Físicas**: Tiendas, bodegas, oficinas con stock individual
- 🤖 **Perfiles de Venta**: Bots de IA, vendedores humanos que ven TODO el inventario
- 📊 **Stock por Ubicación**: Control preciso de inventario en cada tienda/bodega
- 🌐 **Productos Globales**: Catálogo único visible para todos los vendedores
- 🔄 **Trazabilidad Completa**: Sabes quién vendió y de dónde salió el stock

### 🚀 Características Principales V2.0

#### 📍 Gestión de Ubicaciones
- Crear tiendas, bodegas y oficinas
- Stock independiente por ubicación
- Transferencias entre ubicaciones
- Reportes por ubicación

#### 🤖 Perfiles de Venta (Vendedores/Bots)
- Hasta 10+ perfiles vendiendo simultáneamente
- Cada perfil maneja WhatsApp, Facebook, Instagram
- Todos ven el inventario completo
- Reportes de ventas por perfil

#### 📦 Inventario Inteligente
- Productos globales (no atados a ubicaciones)
- Stock distribuido en múltiples ubicaciones
- Vista consolidada del inventario total
- Alertas de stock bajo por ubicación

#### 🛒 Órdenes con Trazabilidad
- Registro de qué perfil vendió
- Registro de qué ubicación proveyó el stock
- Historial completo de movimientos
- Reportes por vendedor y por tienda

## 📚 Documentación V2.0

- **[INICIO_RAPIDO.md](./INICIO_RAPIDO.md)** - Guía de inicio paso a paso
- **[NUEVO_SISTEMA_UBICACIONES.md](./NUEVO_SISTEMA_UBICACIONES.md)** - Arquitectura completa
- **[SISTEMA_TRANSFERENCIAS_V2.md](./SISTEMA_TRANSFERENCIAS_V2.md)** - Sistema de transferencias con reservas
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - Guía de pruebas
- **[INTEGRATION.md](./INTEGRATION.md)** - Integración frontend/backend
- **[api-examples-nuevo-sistema.json](./api-examples-nuevo-sistema.json)** - Ejemplos de API

## 🧪 Inicio del Sistema

### ⚡ Opción 1: Script Automático (Recomendado)

**Linux/Mac:**
```bash
chmod +x start-all.sh
./start-all.sh
```

O por separado:
```bash
./start-backend.sh   # Terminal 1 - Backend en puerto 8000
./start-frontend.sh  # Terminal 2 - Frontend en puerto 5173
```

**Windows:**
```cmd
start-backend.bat   # Terminal 1 - Backend en puerto 8000
start-frontend.bat  # Terminal 2 - Frontend en puerto 5173
```

### ⚙️ Opción 2: Configuración Manual

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 init_db.py --with-data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
npm install
npm run dev
```

### 📱 URLs de Acceso

Después de iniciar (espera ~30 segundos para compilación):

- **🖥️ Frontend**: http://localhost:5173 
- **🔧 Backend API**: http://localhost:8000/docs (Documentación interactiva)
- **📚 ReDoc**: http://localhost:8000/redoc

### 🧪 Verificar el Sistema

```bash
chmod +x test-system.sh
./test-system.sh
```

📖 **Guía completa de pruebas**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)

## 🏗️ Arquitectura V2.0

### Modo de Operación: Backend FastAPI + Frontend React

- **Backend**: FastAPI con SQLite para persistencia
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Comunicación**: REST API con documentación automática (Swagger/OpenAPI)

### Estructura del Proyecto

```
spark-template/
├── backend/              # API FastAPI
│   ├── app/
│   │   ├── main.py      # Aplicación principal
│   │   ├── models.py    # Modelos SQLAlchemy
│   │   ├── schemas.py   # Esquemas Pydantic
│   │   └── routers/     # Endpoints API
│   ├── init_db.py       # Inicialización DB
│   └── requirements.txt # Dependencias Python
│
├── src/                  # Frontend React
│   ├── App.tsx          # Componente principal
│   ├── components/      # Componentes UI
│   ├── lib/             # Servicios y utilidades
│   └── hooks/           # Custom React hooks
│
└── Documentación
    ├── README.md        # Este archivo
    ├── INICIO_RAPIDO.md
    ├── NUEVO_SISTEMA_UBICACIONES.md
    └── SISTEMA_TRANSFERENCIAS_V2.md
```

### ✅ Características Principales

#### 🔹 Gestión de Productos (100%) ✓
- ✅ Visualización de catálogo de productos con filtros
- ✅ Búsqueda por nombre, marca y modelo
- ✅ Filtrado por categoría (celular/accesorio)
- ✅ Filtrado por perfil de negocio
- ✅ Indicadores de stock en tiempo real
- ✅ Tarjetas de producto con detalles completos
- ✅ Badges de estado de stock (disponible/bajo/agotado)

### 1. Configurar Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python init_db.py  # Crea la base de datos con datos de ejemplo
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Configurar Frontend

```bash
npm install
npm run dev
```

La aplicación estará disponible en http://localhost:5173

### 3. Configurar el Sistema

1. **Crear Ubicaciones** (Tiendas/Bodegas):
   - Ve a "Ubicaciones" en el menú
   - Crea tus tiendas y bodega
   - Ejemplo: "Tienda Centro", "Bodega Principal"

2. **Crear Perfiles de Venta** (Bots/Vendedores):
   - Ve a "Perfiles de Venta"
   - Crea perfiles para cada bot o vendedor
   - Configura canales (WhatsApp, Facebook, Instagram)

3. **Agregar Productos con Stock por Ubicación**:
   - Crea productos en el catálogo global
   - Asigna stock específico a cada ubicación
   - Ejemplo: iPhone 15 → 5 en Tienda Centro, 10 en Bodega

## 📱 Funcionalidades Principales

### 📍 Gestión de Ubicaciones
- ✅ Crear tiendas, bodegas, oficinas
- ✅ Asignar stock por ubicación
- ✅ Ver inventario consolidado y por ubicación
- ✅ Transferencias entre ubicaciones
- ✅ Reportes de stock por ubicación
- ✅ Activar/desactivar ubicaciones

### 🤖 Perfiles de Venta (Vendedores/Bots)
- ✅ Crear perfiles para bots de IA o vendedores humanos
- ✅ Configurar canales: WhatsApp, Facebook, Instagram
- ✅ Todos los perfiles ven inventario completo
- ✅ Seguimiento de ventas por perfil
- ✅ Configuración personalizada por perfil
- ✅ Reportes de rendimiento por vendedor/bot

### 📦 Gestión de Productos
- ✅ Catálogo global de productos
- ✅ Stock distribuido por ubicaciones
- ✅ Vista de stock total consolidado
- ✅ Vista de stock por ubicación individual
- ✅ Alertas de stock bajo por ubicación
- ✅ Seguimiento de IMEI único
- ✅ Asignación de proveedores
- ✅ Activar/desactivar productos
- ✅ Imágenes de productos
- ✅ Filtros y búsqueda avanzada

### 🛒 Gestión de Órdenes con Trazabilidad
- ✅ Registro de qué perfil realizó la venta
- ✅ Registro de qué ubicación proveyó el stock
- ✅ Validación automática de stock disponible
- ✅ Actualización automática de inventario
- ✅ Múltiples productos por orden
- ✅ Estados: Pendiente, Pagada, Enviada, Completada, Cancelada
- ✅ Métodos de pago múltiples
- ✅ Historial completo por vendedor
- ✅ Historial completo por ubicación
- ✅ Exportación a CSV

### 🔄 Transferencias de Stock Entre Ubicaciones
- ✅ Transferir stock entre tiendas/bodegas
- ✅ Flujo de confirmación en dos pasos
- ✅ Estados: Pendiente, Confirmada, Rechazada
- ✅ Validación de stock disponible
- ✅ Auditoría completa de movimientos
- ✅ Historial de transferencias

### 📊 Reportes y Analíticas
- ✅ Dashboard con métricas principales
- ✅ Ventas por perfil de venta
- ✅ Ventas por ubicación (tienda)
- ✅ Inventario por ubicación
- ✅ Top productos más vendidos
- ✅ Gráficos de ventas últimos 7 días
- ✅ Distribución de órdenes por estado
- ✅ Alertas de stock bajo por ubicación
- ✅ Valor total del inventario
- ✅ Ingresos totales

### 🔹 Gestión de Proveedores
- ✅ CRUD completo de proveedores
- ✅ Asignación a productos
- ✅ Información de contacto
- ✅ Organización de reclamos/devoluciones

### 🔹 Sincronización Multi-Dispositivo (Legacy)
- ✅ Sincronización automática en tiempo real
- ✅ Indicador de estado de sincronización
- ✅ Notificaciones de actualización
- ✅ Resolución de conflictos

---

## 🚀 Tecnologías Utilizadas

### Frontend
- **React 19** - Framework UI
- **TypeScript** - Tipado estático
- **Tailwind CSS v4** - Estilos
- **shadcn/ui v4** - Componentes
- **Phosphor Icons** - Iconografía
- **Sonner** - Notificaciones toast
- **date-fns** - Manejo de fechas
- **Recharts** - Gráficos y visualizaciones
- **Framer Motion** - Animaciones
- **Spark KV** - Persistencia de datos y sincronización en tiempo real

### Backend
- **FastAPI** - Framework API
- **SQLAlchemy** - ORM
- **SQLite** - Base de datos
- **Pydantic** - Validación de schemas
- **Python 3.11+**

## 🏗️ Arquitectura V2.0

### Sistema de Ubicaciones y Perfiles de Venta

**Antes (V1):** Perfiles = Tiendas independientes con inventario aislado  
**Ahora (V2):** Ubicaciones (físicas) + Perfiles de Venta (vendedores/bots)

#### Tablas Principales:
- **Location**: Tiendas, bodegas, oficinas (tipo: tienda/bodega/oficina)
- **SalesProfile**: Vendedores, bots de IA (tipo: bot_ia/vendedor_humano/sistema_automatico)
- **Product**: Catálogo global (no atado a ubicaciones)
- **Stock**: Producto + Ubicación + Cantidad
- **Order**: Venta con `sales_profile_id` (quién vendió) + `source_location_id` (de dónde salió)

#### Flujo de Negocio:
1. **Crear Ubicaciones**: Tienda Centro, Tienda Norte, Bodega Principal
2. **Crear Perfiles de Venta**: Bot WhatsApp 1, Bot Facebook, Vendedor María
3. **Agregar Productos**: iPhone 15 (catálogo global)
4. **Asignar Stock por Ubicación**: iPhone 15 → 5 en Tienda Centro, 10 en Bodega
5. **Venta**: Bot WhatsApp 1 vende → Stock se descuenta de ubicación elegida
6. **Reportes**: Ventas por bot, Stock por tienda

## 📡 API Endpoints V2.0

### Ubicaciones
- `GET /api/locations` - Listar ubicaciones
- `POST /api/locations` - Crear ubicación
- `GET /api/locations/{id}/stock` - Stock en ubicación
- `PUT /api/locations/{id}` - Actualizar
- `DELETE /api/locations/{id}` - Eliminar

### Perfiles de Venta
- `GET /api/sales-profiles` - Listar perfiles
- `POST /api/sales-profiles` - Crear perfil
- `GET /api/sales-profiles/{id}/orders` - Órdenes del perfil

### Productos (Stock por Ubicación)
- `GET /api/products/{id}/stock/by-location` - Stock por ubicación
- `POST /api/products/{id}/stock/location/{location_id}` - Actualizar stock en ubicación
- `GET /api/products/{id}/stock/total` - Stock total consolidado

👉 Ver `api-examples-nuevo-sistema.json` para ejemplos completos.

---

## 📚 Documentación

### Documentación V2.0 (Nueva Arquitectura)
- **[INICIO_RAPIDO.md](./INICIO_RAPIDO.md)** - Guía de inicio 3 pasos
- **[NUEVO_SISTEMA_UBICACIONES.md](./NUEVO_SISTEMA_UBICACIONES.md)** - Documentación técnica completa
- **[RESUMEN_VISUAL.md](./RESUMEN_VISUAL.md)** - Diagramas antes/después
- **[api-examples-nuevo-sistema.json](./api-examples-nuevo-sistema.json)** - Ejemplos API

### Documentación Legacy (V1)
- [INTEGRATION.md](./INTEGRATION.md) - Integración Frontend + Backend V1
- [MULTI_PROFILE_GUIDE.md](./MULTI_PROFILE_GUIDE.md) - Sistema multi-perfil V1
- [STOCK_TRANSFER_GUIDE.md](./STOCK_TRANSFER_GUIDE.md) - Transferencias V1
- [REALTIME_SYNC.md](./REALTIME_SYNC.md) - Sincronización multi-dispositivo

### Guías Técnicas
- [backend/README.md](./backend/README.md) - Documentación backend FastAPI
- [backend/N8N_INTEGRATION.md](./backend/N8N_INTEGRATION.md) - Integración n8n
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Guía de pruebas
- [PRD.md](./PRD.md) - Especificaciones del producto

---

## ⌨️ Atajos de Teclado
- `Ctrl + N` - Crear nuevo
- `Ctrl + K` - Buscar
- `Ctrl + ,` - Configuración

---

## 🔧 Troubleshooting

### Backend no conecta
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
# Debe mostrar: Application startup complete
```

### Error en migraciones
```bash
cd backend
python -c "from app.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
# Debe incluir: location, sales_profile, stock, product, order
```

### Frontend muestra datos viejos
- Limpiar cache: `Ctrl + Shift + R`
- Verificar API URL en configuración
- Revisar consola del navegador (errores CORS)

---

## 🎯 Estado del Proyecto

**Backend V2.0:** ✅ 95% Completo
- ✅ Modelos de datos (Location, SalesProfile, Stock)
- ✅ Routers CRUD completos
- ✅ Migraciones ejecutadas
- ✅ Stock por ubicación funcional
- ⏳ **Pendiente**: Actualizar `orders.py` con `sales_profile_id` y `source_location_id`

**Frontend V2.0:** ⏳ Pendiente
- ❌ UI para ubicaciones
- ❌ UI para perfiles de venta
- ❌ Stock por ubicación en productos
- ❌ Selector de perfil/ubicación en órdenes

**Documentación:** ✅ Actualizada

## 🔜 Próximos Pasos

1. **Backend**: Actualizar `orders.py` router con nuevos campos
2. **Frontend**: Componentes para Ubicaciones y Perfiles de Venta
3. **Frontend**: Formulario de productos con stock por ubicación
4. **Frontend**: Formulario de órdenes con selección de perfil/ubicación
5. **Testing**: Pruebas end-to-end

---

### 🏪 Features Legacy (V1)
- Gestión de proveedores con contactos
- Seguimiento de IMEI único por producto
- Transferencias entre perfiles (V1, ahora usa ubicaciones)
- Sincronización multi-dispositivo
- Dashboard con analíticas
- Exportación CSV

---

## 📄 License

MIT License, Copyright GitHub, Inc.


### Other Common Issues

**Application won't start:**
- Check that you're using Node.js 18+ 
- Run `npm install` to ensure all dependencies are installed
- Clear browser cache if you see stale data

**Backend connection fails:**
- Verify the backend is running: `cd backend && uvicorn main:app --reload`
- Check the API URL in settings (default: `http://localhost:8000/api`)
- Look for CORS errors in browser console

**Data not persisting:**
- In Local mode: Check browser's local storage quota
- In API mode: Verify backend database file exists: `backend/inventory.db`

---

## 📊 Próximos Pasos (Opcionales)

El sistema está **100% completo** en backend y listo para producción con todas las funcionalidades implementadas:
- ✅ Gestión de inventario multi-perfil
- ✅ Sistema de órdenes con múltiples canales
- ✅ Dashboard con analíticas en tiempo real
- ✅ Sincronización multi-dispositivo
- ✅ Gestión de proveedores e IMEI
- ✅ Transferencias de stock entre tiendas con confirmación
- ✅ Reportes con gráficos mensuales/anuales
- ✅ Exportación de órdenes a PDF
- ✅ Multi-moneda (USD, EUR, MXN, etc.)
- ✅ **Búsqueda de órdenes por cliente** (implementado)
- ✅ **Notas en órdenes** (backend listo)
- ✅ **Filtros de fecha en órdenes** (backend listo)
- ✅ **Historial de cambios de stock** (backend listo)
- ✅ **Gestión de garantías por proveedor** (backend listo)

### Funcionalidades Avanzadas Disponibles

📋 Ver [ADVANCED_FEATURES_IMPLEMENTATION.md](./ADVANCED_FEATURES_IMPLEMENTATION.md) para detalles completos.

**Backend 100% implementado:**
- Sistema completo de historial de stock (`/api/stock-history`)
- Notas y fecha de entrega en órdenes
- Condiciones de garantía vinculadas a proveedores
- Filtros avanzados por fecha

**Frontend requiere componentes UI para:**
- Visualizar historial de stock en diálogo
- Agregar campos de notas en formularios de órdenes
- Date pickers para filtrar por fecha
- Mostrar condiciones de garantía en productos

**Por implementar:**
- Integración con servicios externos de email/WhatsApp para alertas automáticas

---

📄 **License**: MIT License, Copyright GitHub, Inc.
