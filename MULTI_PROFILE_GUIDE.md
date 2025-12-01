# Guía de Configuración de Múltiples Perfiles

## Descripción General

El sistema de inventario soporta múltiples perfiles de negocio, permitiéndote gestionar diferentes tiendas, marcas o líneas de productos desde una sola interfaz. Cada perfil tiene su propio catálogo de productos, órdenes, y configuraciones personalizadas.

## ¿Qué es un Perfil?

Un perfil representa un negocio o marca independiente dentro del sistema. Cada perfil incluye:

- **Catálogo de productos independiente**: Los productos de un perfil no se mezclan con otros
- **Órdenes separadas**: Cada perfil tiene su propio historial de órdenes
- **Configuración personalizada**: Moneda, impuestos, umbrales de stock, etc.
- **Estado activo/inactivo**: Puedes desactivar perfiles temporalmente

## Crear un Nuevo Perfil

### Paso 1: Acceder a la Pestaña de Perfiles
1. Abre el sistema de inventario
2. Haz clic en la pestaña **"Perfiles"** en la navegación principal
3. Haz clic en el botón **"Nuevo Perfil"**

### Paso 2: Completar la Información del Perfil
El formulario de creación requiere dos campos:

#### Nombre del Perfil
- **Ejemplo**: "TechStore Honduras", "Celulares Premium", "Accesorios Móviles"
- **Propósito**: Este es el nombre visible en toda la interfaz
- **Características**: Puede contener espacios, mayúsculas, acentos y caracteres especiales

#### Slug
- **Ejemplo**: "techstore-honduras", "celulares-premium", "accesorios-moviles"
- **Propósito**: Identificador único usado internamente y en API
- **Reglas**:
  - Solo letras minúsculas (a-z)
  - Solo números (0-9)
  - Solo guiones (-) para separar palabras
  - Mínimo 2 caracteres
  - **NO se puede modificar después de crear el perfil**
- **Generación automática**: Al escribir el nombre, el slug se genera automáticamente
- **Validación visual**: Un ícono de verificación verde aparece cuando el slug es válido

### Paso 3: Confirmar Creación
1. Verifica que el nombre y slug sean correctos
2. Haz clic en **"Crear Perfil"**
3. El nuevo perfil aparecerá en la lista de perfiles

## Configurar un Perfil

Después de crear un perfil, puedes personalizar su configuración:

### Abrir Configuración
1. En la pestaña de Perfiles, encuentra la tarjeta del perfil
2. Haz clic en el botón **"Configuración"**
3. Se abrirá el diálogo de configuración con tres pestañas

### Pestaña General

#### Moneda
- **Opciones**: HNL (Lempira), USD (Dólar), MXN (Peso Mexicano), EUR (Euro)
- **Uso**: Define la moneda para mostrar precios

#### Formato de Precio
- **Estándar**: 1234.56
- **Coma**: 1.234,56
- **Espacio**: 1 234.56

#### Tasa de Impuesto
- **Rango**: 0% - 100%
- **Formato**: Decimal (ej: 15.5 para 15.5%)
- **Uso**: Porcentaje de impuesto aplicable a las ventas

#### Calcular Impuesto Automáticamente
- **Activado**: El sistema agrega impuesto a los precios en órdenes
- **Desactivado**: Los precios se muestran sin modificación

#### Umbral de Stock Bajo
- **Valor**: Número entero (ej: 5)
- **Uso**: Productos con stock igual o menor a este valor mostrarán alerta de stock bajo

#### Método de Pago Predeterminado
- **Opciones**: Efectivo, Transferencia, Tarjeta, Financiamiento
- **Uso**: Se preselecciona al crear nuevas órdenes

#### Canal Predeterminado
- **Opciones**: WhatsApp, Facebook, Instagram
- **Uso**: Se preselecciona al crear nuevas órdenes

### Pestaña Notificaciones

#### Habilitar Notificaciones
- **Activado**: Recibirás alertas de stock bajo y nuevas órdenes
- **Desactivado**: No se mostrarán notificaciones

### Pestaña Negocio

#### Dirección del Negocio
- **Opcional**
- **Ejemplo**: "Calle Principal #123, Tegucigalpa"
- **Uso**: Para referencia en órdenes o reportes

#### Teléfono del Negocio
- **Opcional**
- **Ejemplo**: "+504 1234-5678"
- **Uso**: Información de contacto del negocio

#### Correo del Negocio
- **Opcional**
- **Ejemplo**: "ventas@techstore.com"
- **Uso**: Información de contacto del negocio

## Editar un Perfil

### Opciones Editables
1. En la tarjeta del perfil, haz clic en **"Editar"**
2. Puedes modificar:
   - **Nombre del perfil**: Cambiarlo en cualquier momento
   - **Estado**: Activar o desactivar el perfil
3. **NO puedes modificar**: El slug (identificador único)

### Activar/Desactivar Perfil
- **Perfil Activo**: Aparece en los filtros y puede recibir productos/órdenes
- **Perfil Inactivo**: Se oculta de los filtros, pero conserva todos sus datos

## Gestionar Productos por Perfil

### Crear Producto en un Perfil
1. Ve a la pestaña **"Productos"**
2. Haz clic en **"Nuevo Producto"**
3. **Importante**: Selecciona el perfil al que pertenecerá el producto
4. Completa la información del producto
5. El producto solo será visible cuando filtres por ese perfil

### Filtrar Productos por Perfil
1. En la pestaña de Productos, usa el selector de perfiles
2. Selecciona **"Todos los perfiles"** para ver todo el inventario
3. Selecciona un perfil específico para ver solo sus productos

## Gestionar Órdenes por Perfil

### Crear Orden en un Perfil
1. Ve a la pestaña **"Órdenes"**
2. Haz clic en **"Nueva Orden"**
3. Selecciona el perfil en el primer campo del formulario
4. Solo los productos de ese perfil estarán disponibles para agregar a la orden

### Filtrar Órdenes por Perfil
1. En la pestaña de Órdenes, usa el selector de perfiles
2. Selecciona un perfil para ver solo sus órdenes
3. Selecciona **"Todos los perfiles"** para ver todas las órdenes

## Casos de Uso Comunes

### Escenario 1: Múltiples Tiendas Físicas
**Situación**: Tienes 3 tiendas en diferentes ciudades

**Configuración**:
- Crea un perfil por tienda: "Tienda Tegucigalpa", "Tienda San Pedro Sula", "Tienda La Ceiba"
- Cada perfil tiene su propio inventario
- Gestiona las órdenes de cada tienda por separado

### Escenario 2: Diferentes Líneas de Producto
**Situación**: Vendes celulares nuevos y celulares reacondicionados como negocios separados

**Configuración**:
- Perfil "Celulares Nuevos": Productos nuevos, garantía completa
- Perfil "Celulares Reacondicionados": Productos reacondicionados, diferentes precios

### Escenario 3: Negocios para Diferentes Clientes
**Situación**: Tienes un negocio B2C (consumidores) y B2B (mayorista)

**Configuración**:
- Perfil "Retail": Precios al por menor, productos individuales
- Perfil "Mayorista": Precios al por mayor, ventas en volumen

### Escenario 4: Marcas Diferentes
**Situación**: Representas múltiples marcas o franquicias

**Configuración**:
- Un perfil por marca
- Configuraciones personalizadas por marca (moneda, impuestos)
- Inventarios completamente separados

## Exportar Datos por Perfil

### Exportar Productos
1. Filtra por el perfil deseado
2. Haz clic en el botón de exportar (icono de descarga)
3. Se descargará un CSV con solo los productos de ese perfil

### Exportar Órdenes
1. Filtra por el perfil deseado
2. Haz clic en el botón de exportar
3. Se descargará un CSV con solo las órdenes de ese perfil

## Mejores Prácticas

### Nomenclatura de Perfiles
- **Usa nombres descriptivos**: "TechStore Zona Norte" es mejor que "Tienda 1"
- **Mantén consistencia**: Si usas ubicación, úsala para todos los perfiles
- **Slugs significativos**: "techstore-zona-norte" es mejor que "perfil1"

### Organización
- **No crees demasiados perfiles**: Solo crea perfiles cuando realmente necesites separación
- **Desactiva en lugar de eliminar**: Si un perfil ya no se usa, desactívalo en lugar de borrarlo
- **Documenta configuraciones**: Mantén notas de por qué configuraste cada perfil de cierta manera

### Configuración Inicial
- **Configura completamente antes de agregar productos**: Es más fácil configurar moneda e impuestos antes
- **Prueba con productos de ejemplo**: Crea algunos productos de prueba para verificar la configuración
- **Revisa las notificaciones**: Asegúrate de que las alertas estén configuradas correctamente

## Preguntas Frecuentes

### ¿Puedo mover un producto de un perfil a otro?
No directamente. Deberías crear un nuevo producto en el perfil destino y desactivar el original.

### ¿Puedo tener el mismo producto en múltiples perfiles?
Sí, pero serán productos independientes con inventarios separados. Crea el producto en cada perfil.

### ¿Qué pasa con los datos si desactivo un perfil?
Todos los datos (productos, órdenes, configuración) se conservan. Solo se oculta de los filtros.

### ¿Puedo eliminar un perfil?
Actualmente no hay función de eliminación. Desactiva el perfil si ya no lo necesitas.

### ¿El slug puede contener mayúsculas?
No. El sistema convierte automáticamente a minúsculas y elimina caracteres no permitidos.

### ¿Cuántos perfiles puedo crear?
No hay límite técnico, pero para mejor rendimiento y organización, se recomienda menos de 20 perfiles activos.

## Solución de Problemas

### No puedo crear un nuevo perfil
- **Verifica el slug**: Debe tener al menos 2 caracteres y solo minúsculas, números y guiones
- **Slug duplicado**: Ese slug ya existe, usa uno diferente
- **Campos vacíos**: Asegúrate de completar nombre y slug

### No veo productos en un perfil
- **Verifica el filtro**: Asegúrate de tener el perfil correcto seleccionado
- **Productos inactivos**: Marca "Mostrar productos inactivos" si están desactivados
- **Perfil equivocado**: Los productos pueden estar en otro perfil

### Las órdenes no muestran productos correctos
- **Perfil de la orden**: Verifica que el perfil de la orden sea el correcto
- **Stock del perfil**: Solo productos del mismo perfil están disponibles

## Soporte y Ayuda

Si necesitas ayuda adicional:
1. Revisa esta guía completa
2. Verifica la configuración del perfil
3. Consulta el PRD.md para detalles técnicos
4. Contacta al administrador del sistema
