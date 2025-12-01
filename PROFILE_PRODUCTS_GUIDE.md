# Guía: Productos Específicos por Perfil y Órdenes por Perfil

## ✅ Sistema Implementado

El sistema de inventario ya cuenta con todas las funcionalidades necesarias para:
- Agregar productos específicos a cada perfil
- Crear órdenes asociadas a perfiles específicos
- Filtrar productos y órdenes por perfil
- Gestionar múltiples negocios de forma independiente

## 🎯 Características Implementadas

### 1. Productos por Perfil

Cada producto está asociado a un perfil específico mediante el campo `profile_id`:

```typescript
interface Product {
  id: number
  profile_id: number  // ← Asociación con el perfil
  sku: string
  nombre: string
  categoria: 'celular' | 'accesorio'
  marca: string
  modelo: string
  // ... otros campos
}
```

**Cómo funciona:**
- Al crear un producto, debes seleccionar el perfil al que pertenece
- Los productos solo aparecen cuando filtras por su perfil
- Cada perfil tiene su propio catálogo de productos independiente

### 2. Órdenes por Perfil

Cada orden está asociada a un perfil específico mediante el campo `profile_id`:

```typescript
interface Order {
  id: number
  profile_id: number  // ← Asociación con el perfil
  customer_name: string
  customer_phone: string
  canal: 'whatsapp' | 'facebook' | 'instagram'
  // ... otros campos
}
```

**Cómo funciona:**
- Al crear una orden, primero seleccionas el perfil
- Solo puedes agregar productos del mismo perfil a la orden
- Las órdenes se filtran por perfil automáticamente

## 📋 Flujo de Trabajo

### Paso 1: Crear Perfiles

1. Ve a la pestaña **Perfiles**
2. Haz clic en **+ Nuevo Perfil**
3. Ingresa:
   - **Nombre**: Nombre del negocio (ej: "Softmobile", "TechStore")
   - **Slug**: Identificador único (ej: "softmobile", "techstore")
4. Haz clic en **Crear Perfil**

**Ejemplo:**
```
Perfil 1:
  Nombre: Softmobile
  Slug: softmobile

Perfil 2:
  Nombre: TechStore Honduras
  Slug: techstore-hn
```

### Paso 2: Agregar Productos al Perfil

1. Ve a la pestaña **Productos**
2. Haz clic en **Nuevo Producto**
3. **IMPORTANTE**: Selecciona el perfil en el primer campo
4. Completa la información del producto:
   - Perfil: Selecciona "Softmobile" (u otro perfil)
   - SKU: Código único del producto
   - Nombre: Nombre descriptivo
   - Categoría: Celular o Accesorio
   - Marca, Modelo, Capacidad
   - Precio y Garantía
   - Stock Inicial
5. Haz clic en **Agregar Producto**

**Ejemplo para Perfil "Softmobile":**
```
Producto 1:
  Perfil: Softmobile
  SKU: IPH15-128-BLK
  Nombre: iPhone 15 128GB Negro
  Categoría: celular
  Marca: Apple
  Modelo: iPhone 15
  Capacidad: 128GB
  Condición: nuevo
  Precio: 22000 HNL
  Garantía: 12 meses
  Stock: 10 unidades

Producto 2:
  Perfil: Softmobile
  SKU: SAM-S24-256-WHT
  Nombre: Samsung Galaxy S24 256GB Blanco
  Categoría: celular
  Marca: Samsung
  Modelo: Galaxy S24
  Capacidad: 256GB
  Condición: nuevo
  Precio: 18500 HNL
  Garantía: 12 meses
  Stock: 5 unidades
```

### Paso 3: Crear Órdenes por Perfil

1. Ve a la pestaña **Órdenes**
2. Haz clic en **+ Nueva Orden**
3. **Selecciona el Perfil** (este define qué productos puedes agregar)
4. Ingresa datos del cliente:
   - Nombre del Cliente
   - Teléfono (formato: +504 9999-9999)
5. Selecciona Canal (WhatsApp, Facebook, Instagram)
6. Selecciona Método de Pago
7. **Agrega Productos**:
   - Solo verás productos del perfil seleccionado
   - Selecciona el producto
   - Define la cantidad (valida contra stock disponible)
   - Puedes agregar múltiples productos con el botón **+ Agregar Producto**
8. Verifica el Total
9. Haz clic en **Crear Orden**

**Ejemplo de Orden para Perfil "Softmobile":**
```
Orden:
  Perfil: Softmobile
  Cliente: Juan Pérez
  Teléfono: +504 9876-5432
  Canal: WhatsApp
  Método de Pago: Transferencia
  
  Productos:
    - iPhone 15 128GB Negro × 1 = 22,000 HNL
    - Funda Silicona iPhone 15 × 2 = 300 HNL
  
  Total: 22,300 HNL
```

### Paso 4: Filtrar por Perfil

En las pestañas **Productos** y **Órdenes**:
1. Usa el selector de **Perfil** en la barra de filtros
2. Selecciona "Todos los perfiles" para ver todo
3. Selecciona un perfil específico para ver solo sus datos

## 🔍 Validaciones Implementadas

### Creación de Productos
- ✅ Perfil es obligatorio
- ✅ SKU, nombre, marca, modelo son obligatorios
- ✅ Precio debe ser mayor a 0
- ✅ Stock inicial debe ser número entero

### Creación de Órdenes
- ✅ Perfil es obligatorio
- ✅ Nombre del cliente es obligatorio
- ✅ Teléfono se valida (formato hondureño)
- ✅ Debe tener al menos un producto
- ✅ Cantidad no puede exceder el stock disponible
- ✅ Solo puedes agregar productos del perfil seleccionado

### Filtrado
- ✅ Los productos se filtran automáticamente por perfil
- ✅ Las órdenes se filtran automáticamente por perfil
- ✅ El cambio de perfil actualiza la lista de productos disponibles

## 🎨 Características Visuales

### Tarjetas de Perfil
- Muestra nombre del perfil
- Indica si está activo/inactivo
- Contador de productos activos
- Contador de órdenes totales
- Botones para editar y configurar

### Filtros de Perfil
- Selector desplegable en productos
- Selector desplegable en órdenes
- Opción "Todos los perfiles" para vista general

### Indicadores
- Badge en el header muestra modo de conexión (Local/API)
- Stock badges con colores según disponibilidad:
  - 🔴 Rojo: Stock < 5
  - 🟡 Amarillo: Stock < 20
  - 🟢 Verde: Stock ≥ 20

## 💾 Persistencia de Datos

### Modo Local (por defecto)
- Datos se guardan en `spark.kv` (almacenamiento del navegador)
- Los productos y órdenes persisten entre sesiones
- Cada perfil mantiene su catálogo independiente

### Modo API
1. Ve a **Configuración** (ícono de engranaje)
2. Activa "Usar API Backend"
3. Configura la URL del backend (ej: http://localhost:8000/api)
4. Los datos se sincronizan con el backend FastAPI

## 🚀 Datos de Ejemplo Iniciales

El sistema viene pre-cargado con:
- **1 Perfil**: Softmobile
- **6 Productos**: 
  - 3 celulares (iPhone 13, Galaxy S23, Redmi Note 12)
  - 2 accesorios (Funda, Cargador)
  - 1 iPhone 14 Pro reacondicionado
- Todos asociados al perfil "Softmobile"

## 📊 Dashboard de Estadísticas

En la pestaña Productos verás:
- Total de productos activos
- Total de órdenes
- Valor total del inventario
- Alertas de stock bajo/agotado

Las estadísticas respetan el filtro de perfil seleccionado.

## 🔧 Configuración por Perfil

Cada perfil puede tener configuraciones independientes:
1. Haz clic en el botón de configuración (engranaje) en una tarjeta de perfil
2. Configura:
   - Moneda (HNL por defecto)
   - Tasa de impuesto
   - Umbral de stock bajo
   - Método de pago predeterminado
   - Canal predeterminado
   - Información del negocio (dirección, teléfono, email)

## ⌨️ Atajos de Teclado

- `Ctrl + N`: Crear nuevo elemento (producto/orden/perfil según pestaña activa)
- `Ctrl + K`: Enfocar búsqueda
- `Ctrl + ,`: Abrir configuración
- `Shift + ?`: Mostrar atajos de teclado

## 🎯 Casos de Uso

### Caso 1: Múltiples Tiendas
```
Perfil: Tienda Centro
  - Productos: 50 celulares
  - Órdenes: Clientes del centro de la ciudad

Perfil: Tienda Mall
  - Productos: 30 celulares premium
  - Órdenes: Clientes del mall
```

### Caso 2: Marcas Separadas
```
Perfil: Apple Store
  - Productos: Solo iPhones, iPads, AirPods
  - Órdenes: Ventas de productos Apple

Perfil: Samsung Store
  - Productos: Solo Galaxy, Buds, Watch
  - Órdenes: Ventas de productos Samsung
```

### Caso 3: Nuevos vs Usados
```
Perfil: Nuevos Premium
  - Productos: Celulares nuevos de alta gama
  - Órdenes: Clientes premium

Perfil: Reacondicionados
  - Productos: Celulares reacondicionados
  - Órdenes: Clientes value
```

## ✨ Próximas Mejoras Sugeridas

1. **Transferencia de productos entre perfiles**
2. **Reportes por perfil** (ventas, ingresos, productos más vendidos)
3. **Configuración de permisos** por perfil
4. **Plantillas de productos** para copiar entre perfiles
5. **Importación masiva** de productos con perfil asignado

## 📞 Soporte

Si tienes dudas sobre cómo usar el sistema de perfiles:
1. Consulta la guía de setup: `MULTI_PROFILE_GUIDE.md`
2. Revisa los datos de ejemplo en: `src/lib/initialData.ts`
3. Verifica la documentación técnica en: `PRD.md`

---

**Sistema listo para usar** ✅ - Todos los componentes funcionan correctamente con productos específicos por perfil y órdenes por perfil.
