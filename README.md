# 📦 Sistema de Inventario para Chatbots de Ventas

## 🎯 Progreso del Proyecto: **95%** ✅

Un sistema completo de gestión de inventario de celulares y accesorios diseñado para integrarse con chatbots de ventas en WhatsApp, Facebook e Instagram.

**🆕 NOVEDAD**: Ahora con soporte para backend FastAPI - elige entre almacenamiento local o base de datos compartida.

## 🏗️ Arquitectura

El sistema soporta **dos modos de backend**:

- **Modo Local** (por defecto): Datos en Spark KV (almacenamiento del navegador)
- **Modo API**: Conectado a backend FastAPI con SQLite

👉 Ver [INTEGRATION.md](./INTEGRATION.md) para guía completa de integración.

### ✅ Características Implementadas (95%)

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
- ✅ **NUEVO: Activar/desactivar productos desde UI**
- ✅ **NUEVO: Filtro para mostrar/ocultar productos inactivos**
- ✅ **NUEVO: Indicador visual para productos inactivos**

#### 🔹 Gestión de Órdenes (100%)
- ✅ Creación de órdenes con múltiples productos
- ✅ Validación de stock antes de crear orden
- ✅ Actualización automática de inventario
- ✅ Información de cliente (nombre, teléfono)
- ✅ Selección de canal (WhatsApp/Facebook/Instagram)
- ✅ Método de pago (efectivo/transferencia/tarjeta/financiamiento)
- ✅ Cálculo automático de totales
- ✅ Visualización de historial de órdenes
- ✅ Actualización de estado de órdenes

#### 🔹 Multi-Perfil (100%)
- ✅ Soporte para múltiples perfiles de negocio
- ✅ Filtrado de productos por perfil
- ✅ Filtrado de órdenes por perfil
- ✅ Selector de perfil en header
- ✅ Interfaz para crear nuevos perfiles
- ✅ Visualización de perfiles con estadísticas

#### 🔹 Persistencia de Datos (100%)
- ✅ **NUEVO: Arquitectura dual de backend (Local + API)**
- ✅ **NUEVO: Cliente HTTP para FastAPI**
- ✅ **NUEVO: Diálogo de configuración con test de conexión**
- ✅ **NUEVO: Cambio dinámico entre backends**
- ✅ Almacenamiento persistente usando spark.kv
- ✅ Datos iniciales de demostración
- ✅ Actualización atómica de stock
- ✅ Prevención de condiciones de carrera

#### 🔹 Backend FastAPI (100%) ✨
- ✅ API REST completa con FastAPI
- ✅ Base de datos SQLite con SQLAlchemy
- ✅ Schemas Pydantic para validación
- ✅ Transacciones atómicas
- ✅ CORS habilitado
- ✅ Documentación Swagger automática
- ✅ Script de inicialización de datos
- 👉 Ver `backend/README.md` para más detalles

#### 🔹 UI/UX (90%)
- ✅ Diseño profesional con Tailwind CSS
- ✅ Componentes shadcn implementados
- ✅ Tema de colores azul profesional
- ✅ Tipografía Inter
- ✅ Responsive design
- ✅ Estados de carga
- ✅ Notificaciones toast (sonner)
- ✅ Animaciones sutiles
- ⏳ Estados vacíos mejorados (parcial)

### ⏳ Características Pendientes (5%)

#### 🔸 Gestión de Perfiles Avanzada
- ⏳ Interfaz para editar perfiles existentes
- ⏳ Activar/desactivar perfiles

#### 🔸 Reportes y Analíticas
- ⏳ Dashboard con métricas principales
- ⏳ Gráficos de ventas por período
- ⏳ Productos más vendidos
- ⏳ Inventario bajo stock
- ⏳ Reporte de ingresos

#### 🔸 Funcionalidades Adicionales
- ⏳ Exportar órdenes a PDF/Excel
- ⏳ Buscar órdenes por cliente
- ⏳ Filtros avanzados de órdenes por fecha
- ⏳ Historial de cambios de stock
- ⏳ Notas en órdenes

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
- **Spark KV** - Persistencia de datos

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

## 📊 Próximos Pasos

1. ✅ ~~Implementar gestión completa de productos (agregar/editar/activar-desactivar)~~
2. ✅ ~~Agregar gestión de perfiles (crear/visualizar)~~
3. ✅ ~~Implementar backend FastAPI con integración completa~~
4. **Agregar dashboard con analíticas**
5. **Implementar reportes y exportación**
6. **Agregar búsqueda avanzada de órdenes**

---

📄 **License**: MIT License, Copyright GitHub, Inc.
