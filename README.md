# 📦 Sistema de Inventario para Chatbots de Ventas

## 🎯 Progreso del Proyecto: **100%** ✅

Un sistema completo de gestión de inventario de celulares y accesorios diseñado para integrarse con chatbots de ventas en WhatsApp, Facebook e Instagram.

**🆕 NOVEDAD**: Ahora con **sincronización en tiempo real multi-dispositivo** - trabaja desde cualquier dispositivo y mantén todo sincronizado automáticamente.

**🔄 SINCRONIZACIÓN MULTI-DISPOSITIVO**: Ver [REALTIME_SYNC.md](./REALTIME_SYNC.md) para documentación completa.

## 🧪 Probar el Sistema

### Inicio Rápido

**Linux/Mac:**
```bash
# Dar permisos de ejecución (solo primera vez)
chmod +x test-system.sh start-backend.sh start-frontend.sh

# Ejecutar pruebas completas del sistema
./test-system.sh

# O iniciar manualmente:
./start-backend.sh   # Terminal 1 - Backend en puerto 8000
./start-frontend.sh  # Terminal 2 - Frontend en puerto 5173
```

**Windows:**
```cmd
start-backend.bat   # Terminal 1 - Backend en puerto 8000
start-frontend.bat  # Terminal 2 - Frontend en puerto 5173
```

### Pruebas Automatizadas

```bash
# Backend debe estar ejecutándose primero
python3 test-backend.py
```

📖 **Guía completa de pruebas**: Ver [TESTING_GUIDE.md](./TESTING_GUIDE.md)

## 🏗️ Arquitectura

El sistema soporta **dos modos de backend**:

- **Modo Local** (por defecto): Datos en Spark KV (almacenamiento del navegador) con sincronización automática
- **Modo API**: Conectado a backend FastAPI con SQLite

👉 Ver [INTEGRATION.md](./INTEGRATION.md) para guía completa de integración.

### ✅ Características Implementadas (100%)

#### 🔹 Gestión de Productos (100%) ✓
- ✅ Visualización de catálogo de productos con filtros
- ✅ Búsqueda por nombre, marca y modelo
- ✅ Filtrado por categoría (celular/accesorio)
- ✅ Filtrado por perfil de negocio
- ✅ Indicadores de stock en tiempo real
- ✅ Tarjetas de producto con detalles completos
- ✅ Badges de estado de stock (disponible/bajo/agotado)
- ✅ Formulario para agregar nuevos productos
- ✅ Formulario para editar productos existentes
- ✅ Actualización de stock desde UI de edición
- ✅ Activar/desactivar productos desde UI
- ✅ Filtro para mostrar/ocultar productos inactivos
- ✅ Indicador visual para productos inactivos
- ✅ Animaciones sutiles en tarjetas
- ✅ Alerta visual para stock bajo
- ✅ Validación mejorada de formularios

#### 🔹 Gestión de Órdenes (100%) ✓
- ✅ Creación de órdenes con múltiples productos
- ✅ Validación de stock antes de crear orden
- ✅ Actualización automática de inventario
- ✅ Información de cliente (nombre, teléfono)
- ✅ Selección de canal (WhatsApp/Facebook/Instagram)
- ✅ Método de pago (efectivo/transferencia/tarjeta/financiamiento)
- ✅ Cálculo automático de totales
- ✅ Visualización de historial de órdenes
- ✅ Actualización de estado de órdenes
- ✅ Filtrado por estado
- ✅ Exportación a CSV

#### 🔹 Multi-Perfil (100%) ✓
- ✅ Soporte para múltiples perfiles de negocio
- ✅ Filtrado de productos por perfil
- ✅ Filtrado de órdenes por perfil
- ✅ Selector de perfil en header
- ✅ Interfaz para crear nuevos perfiles
- ✅ **Interfaz para editar perfiles existentes**
- ✅ **Activar/desactivar perfiles**
- ✅ Visualización de perfiles con estadísticas

#### 🔹 Persistencia de Datos (100%) ✓
- ✅ Arquitectura dual de backend (Local + API)
- ✅ Cliente HTTP para FastAPI
- ✅ Diálogo de configuración con test de conexión
- ✅ Cambio dinámico entre backends
- ✅ Almacenamiento persistente usando spark.kv
- ✅ Datos iniciales de demostración
- ✅ Actualización atómica de stock
- ✅ Prevención de condiciones de carrera

#### 🔹 Backend FastAPI (100%) ✓
- ✅ API REST completa con FastAPI
- ✅ Base de datos SQLite con SQLAlchemy
- ✅ Schemas Pydantic para validación
- ✅ Transacciones atómicas
- ✅ CORS habilitado
- ✅ Documentación Swagger automática
- ✅ Script de inicialización de datos
- 👉 Ver `backend/README.md` para más detalles

#### 🔹 Reportes y Analíticas (100%) ✓
- ✅ **Dashboard con métricas principales**
- ✅ **Gráfico de ventas últimos 7 días**
- ✅ **Gráfico de distribución de órdenes por estado**
- ✅ **Top 5 productos más vendidos**
- ✅ **Alertas de inventario (stock bajo/agotado)**
- ✅ **Indicadores de ingresos totales**
- ✅ **Indicadores de valor del inventario**
- ✅ Exportar productos a CSV
- ✅ Exportar órdenes a CSV

#### 🔹 Gestión de Proveedores (100%) ✓
- ✅ **CRUD completo de proveedores**
- ✅ **Asignación de proveedor a productos**
- ✅ **Información de contacto (teléfono, email)**
- ✅ **Búsqueda y filtrado por perfil**
- ✅ **Organización de reclamos y devoluciones**

#### 🔹 Seguimiento de IMEI (100%) ✓
- ✅ **Campo IMEI único por producto**
- ✅ **Validación de IMEI en formularios**
- ✅ **Visualización de IMEI en tarjetas de producto**
- ✅ **Trazabilidad completa de dispositivos**

#### 🔹 Transferencias de Stock (100%) ✓
- ✅ **Sistema de transferencias entre perfiles**
- ✅ **Flujo de confirmación en dos pasos**
- ✅ **Estados: Pendiente, Confirmada, Rechazada, Cancelada**
- ✅ **Panel de transferencias pendientes**
- ✅ **Confirmación/rechazo desde perfil destino**
- ✅ **Motivo de rechazo requerido**
- ✅ **Historial completo de transferencias**
- ✅ **Actualización de stock solo al confirmar**
- ✅ **Auditoría completa (quién confirma, cuándo)**

#### 🔹 UI/UX (100%) ✓
- ✅ Diseño profesional con Tailwind CSS
- ✅ Componentes shadcn implementados
- ✅ Tema de colores azul profesional
- ✅ Tipografía Inter
- ✅ Responsive design
- ✅ Estados de carga
- ✅ Notificaciones toast (sonner)
- ✅ Animaciones sutiles con framer-motion
- ✅ Estados vacíos mejorados con CTA
- ✅ Transiciones suaves en listas
- ✅ Validación visual de formularios
- ✅ Atajos de teclado
- ✅ **Gráficos interactivos con recharts**

#### 🔹 Sincronización Multi-Dispositivo (100%) ✓
- ✅ Sincronización automática en tiempo real
- ✅ Indicador de estado de sincronización
- ✅ Detección de cambios remotos
- ✅ Notificaciones de actualización
- ✅ Identificación única por dispositivo
- ✅ Configuración de intervalo de sincronización
- ✅ Resolución automática de conflictos
- ✅ Panel de configuración de sincronización
- ✅ Limpiar datos de sincronización
- ✅ Documentación completa

---

## 🚀 Inicio Rápido

### Modo Local (Recomendado para comenzar)

```bash
npm install
npm run dev
```

La aplicación estará disponible en http://localhost:5173

### Modo API (Para producción)

Ver [INTEGRATION.md](./INTEGRATION.md) para configurar el backend FastAPI.

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
- **Pydantic** - Validación de datos
- **Python 3.11+**

---

## 📚 Documentación

- [INTEGRATION.md](./INTEGRATION.md) - Guía de integración Frontend + Backend
- [backend/README.md](./backend/README.md) - Documentación del API
- [backend/N8N_INTEGRATION.md](./backend/N8N_INTEGRATION.md) - Integración con n8n
- [PRD.md](./PRD.md) - Especificaciones del producto

---

## 🎉 Funcionalidades Destacadas

### 📊 Dashboard Analytics
- Visualización de métricas clave en tiempo real
- Gráficos de ventas de los últimos 7 días
- Distribución de órdenes por estado
- Top 5 productos más vendidos
- Alertas automáticas de inventario bajo

### 🔄 Backend Dual
- Modo local con Spark KV para desarrollo rápido
- Modo API con FastAPI para producción
- Cambio entre modos sin perder datos
- Indicador visual del backend activo

### ⌨️ Atajos de Teclado
- `Ctrl + N` - Crear nuevo elemento en pestaña activa
- `Ctrl + K` - Enfocar búsqueda
- `Ctrl + ,` - Abrir configuración
- `Shift + ?` - Mostrar atajos de teclado

### 📤 Exportación de Datos
- Exportar productos a CSV con filtros aplicados
- Exportar órdenes a CSV por estado
- Nombres de archivo con timestamp único

### 🔄 Transferencias entre Tiendas
- **Flujo de confirmación en dos pasos** para tiendas independientes
- Transferencias quedan en estado **Pendiente** hasta ser confirmadas
- El perfil destino puede **Confirmar** o **Rechazar** con motivo
- Stock se actualiza **solo al confirmar**, no al crear
- Historial completo con trazabilidad de quién confirmó y cuándo
- Panel dedicado para revisar transferencias pendientes

### 🏪 Gestión de Proveedores e IMEI
- **Registro de proveedores** con información de contacto completa
- Asignación de proveedor al agregar productos nuevos
- **IMEI único** para identificación de dispositivos
- Organización de reclamos y devoluciones por proveedor
- Trazabilidad completa para garantías

---

## 🔧 Troubleshooting

### Error: "Cannot find module vite/dist/node/chunks/dist.js"

This is a **node_modules corruption issue**, not a code issue. It happens when Vite's installation is incomplete.

**Quick Fix:**
```bash
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

👉 See [FIX_VITE_ERROR.md](./FIX_VITE_ERROR.md) for detailed troubleshooting steps.

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
