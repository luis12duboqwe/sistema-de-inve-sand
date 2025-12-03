# 📦 Sistema de Inventario para Chatbots de Ventas

## 🎯 Progreso del Proyecto: **100%** ✅

Un sistema completo de gestión de inventario de celulares y accesorios diseñado para integrarse con chatbots de ventas en WhatsApp, Facebook e Instagram.

**🆕 NOVEDAD**: Ahora con soporte para backend FastAPI - elige entre almacenamiento local o base de datos compartida.

## 🏗️ Arquitectura

El sistema soporta **dos modos de backend**:

- **Modo Local** (por defecto): Datos en Spark KV (almacenamiento del navegador)
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

El sistema está 100% completo y listo para producción. Posibles mejoras futuras:

1. **Reportes Avanzados**
   - Exportación a PDF
   - Gráficos de tendencias mensuales/anuales
   - Reportes de rentabilidad por producto

2. **Búsqueda Avanzada**
   - Buscar órdenes por cliente
   - Filtros de fecha en órdenes
   - Historial de cambios de stock

3. **Funcionalidades Extras**
   - Notas en órdenes
   - Gestión de proveedores
   - Alertas por email/WhatsApp
   - Multi-moneda

---

📄 **License**: MIT License, Copyright GitHub, Inc.
