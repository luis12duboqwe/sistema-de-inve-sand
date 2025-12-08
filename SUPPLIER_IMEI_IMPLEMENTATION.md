# Implementación: Gestión de Proveedores e IMEI

## ✅ Características Implementadas

Se ha implementado exitosamente la funcionalidad de **gestión de proveedores** y **registro de IMEI** para productos.

## 🎯 Componentes Implementados

### Backend (Python/FastAPI)

1. **Nuevo Modelo Supplier** (`backend/app/models.py`)
   - Tabla `suppliers` con campos:
     - nombre, contacto, telefono, email
     - direccion, notas, activo
     - profile_id (relación con perfil)
     - created_at, updated_at
   - Relación con Profile y Product

2. **Modelo Product Actualizado** (`backend/app/models.py`)
   - Nuevo campo `supplier_id` (clave foránea a suppliers)
   - Nuevo campo `imei` (único, para celulares)
   - Índices optimizados

3. **Schemas de Supplier** (`backend/app/schemas.py`)
   - `SupplierBase`, `SupplierCreate`, `SupplierUpdate`, `SupplierResponse`
   - Validaciones integradas

4. **Schemas de Product Actualizados** (`backend/app/schemas.py`)
   - `ProductBase`, `ProductCreate`, `ProductUpdate`, `ProductResponse`
   - Incluyen `supplier_id` e `imei`

5. **Router de Suppliers** (`backend/app/routers/suppliers.py`)
   - `POST /api/suppliers` - Crear proveedor
   - `GET /api/suppliers` - Listar proveedores (con filtros)
   - `GET /api/suppliers/{id}` - Obtener detalles
   - `PUT /api/suppliers/{id}` - Actualizar proveedor
   - `DELETE /api/suppliers/{id}` - Eliminar proveedor

6. **Script de Migración** (`backend/migrate_supplier_imei.py`)
   - Crea tabla suppliers
   - Agrega columnas supplier_id e imei a products

### Frontend (React/TypeScript)

1. **Tipos Actualizados** (`src/lib/types.ts`)
   - Interface `Supplier` completa
   - `Product` actualizado con `supplier_id` e `imei`

2. **Componente ManageSuppliersDialog** (`src/components/ManageSuppliersDialog.tsx`)
   - Gestión completa de proveedores
   - Listado, creación, edición y eliminación
   - Formulario completo con validaciones

3. **NewProductDialog Actualizado** (`src/components/NewProductDialog.tsx`)
   - Campo de selección de proveedor (opcional)
   - Campo de IMEI (opcional, solo para celulares)
   - Carga automática de proveedores del perfil
   - Información contextual para ambos campos

## 📋 Casos de Uso

### 1. Gestionar Proveedores

**Desde la interfaz:**
1. Ir a configuración o gestión de proveedores
2. Crear nuevo proveedor con:
   - Nombre (requerido)
   - Persona de contacto
   - Teléfono y email
   - Dirección
   - Notas adicionales
3. Editar o eliminar proveedores existentes

**Desde la API:**
```bash
POST /api/suppliers
{
  "profile_id": 1,
  "nombre": "Distribuidora TechHN",
  "contacto": "Juan Pérez",
  "telefono": "+504 2222-3333",
  "email": "ventas@techn.com",
  "direccion": "Tegucigalpa, Honduras",
  "notas": "Proveedor principal de Samsung",
  "activo": true
}
```

### 2. Agregar Producto con Proveedor e IMEI

**Al crear un producto:**
1. Completar datos normales del producto
2. Seleccionar proveedor del dropdown
3. Si es celular, ingresar IMEI (15 dígitos)
4. El sistema guarda la relación

**Ejemplo con API:**
```bash
POST /api/products
{
  "profile_id": 1,
  "supplier_id": 5,
  "sku": "SAM-S24-256-NEG",
  "nombre": "Samsung Galaxy S24 256GB Negro",
  "categoria": "celular",
  "marca": "Samsung",
  "modelo": "Galaxy S24",
  "capacidad": "256GB",
  "condicion": "nuevo",
  "precio": 18500.00,
  "moneda": "HNL",
  "garantia_meses": 12,
  "imei": "123456789012345",
  "stock_inicial": 5
}
```

### 3. Organizar Reclamos y Devoluciones

**Beneficios:**
- Identificar rápidamente el proveedor de un producto
- Contactar al proveedor para devoluciones
- Rastrear productos por IMEI único
- Organizar reclamos de garantía
- Análisis de productos por proveedor

## 🔍 Filtros y Búsquedas Disponibles

### Proveedores
```bash
GET /api/suppliers?profile_id=1&include_inactive=false&search=Tech&page=1&per_page=50
```

**Parámetros:**
- `profile_id` - Filtrar por perfil
- `include_inactive` - Incluir proveedores inactivos
- `search` - Buscar por nombre
- `page`, `per_page` - Paginación

### Productos por Proveedor
Los productos ahora incluyen `supplier_id`, permitiendo:
- Filtrar productos de un proveedor específico
- Generar reportes por proveedor
- Identificar productos sin proveedor asignado

## 📊 Estructura de Base de Datos

### Tabla: suppliers

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer | ID único del proveedor |
| profile_id | Integer | ID del perfil (FK) |
| nombre | String | Nombre del proveedor * |
| contacto | String | Persona de contacto |
| telefono | String | Teléfono de contacto |
| email | String | Email del proveedor |
| direccion | Text | Dirección completa |
| notas | Text | Observaciones adicionales |
| activo | Boolean | Estado del proveedor |
| created_at | DateTime | Fecha de creación |
| updated_at | DateTime | Última actualización |

**Índices:**
- `idx_supplier_profile_active` en (profile_id, activo)

### Tabla: products (Campos Nuevos)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| supplier_id | Integer | ID del proveedor (FK, nullable) |
| imei | String | IMEI del dispositivo (único, nullable) |

**Índices:**
- `idx_product_supplier` en supplier_id
- `idx_product_imei` en imei (único)

## 🚀 Pasos de Instalación

### 1. Ejecutar Migración

```bash
cd backend
python3 migrate_supplier_imei.py
```

**Salida esperada:**
```
Aplicando migraciones para Supplier e IMEI...
  - Creando tabla suppliers...
  ✓ Tabla suppliers creada
  - Agregando columna supplier_id a products...
  ✓ Columna supplier_id agregada
  - Agregando columna imei a products...
  ✓ Columna imei agregada

✓ Migraciones completadas con éxito
```

### 2. Reiniciar Backend

```bash
cd backend
./start.sh  # Linux/Mac
# o
start.bat   # Windows
```

### 3. Usar en la Interfaz

La funcionalidad estará disponible automáticamente:
- Selección de proveedor al crear productos
- Campo IMEI para celulares
- Gestión de proveedores desde el diálogo dedicado

## 💡 Mejores Prácticas

### Proveedores
- ✅ Mantener información de contacto actualizada
- ✅ Agregar notas sobre términos de garantía
- ✅ Desactivar proveedores en lugar de eliminarlos (historial)
- ✅ Usar nombres descriptivos y únicos

### IMEI
- ✅ Verificar IMEI antes de registrar (debe tener 15 dígitos)
- ✅ No duplicar IMEI entre productos
- ✅ Registrar IMEI especialmente para productos de alto valor
- ✅ Usar IMEI para rastreo en caso de garantía o devolución

### Organización de Reclamos
1. Filtrar productos por proveedor
2. Identificar producto por IMEI
3. Contactar proveedor usando datos guardados
4. Agregar notas al proveedor sobre el reclamo

## 📈 Beneficios del Sistema

### Para Reclamos y Devoluciones
- ✅ Identificación rápida del proveedor
- ✅ Datos de contacto siempre disponibles
- ✅ Rastreo único por IMEI
- ✅ Historial de productos por proveedor

### Para Gestión de Inventario
- ✅ Análisis de productos por proveedor
- ✅ Evaluación de calidad de proveedores
- ✅ Organización de garantías
- ✅ Trazabilidad completa de dispositivos

### Para Seguridad
- ✅ IMEI único previene duplicados
- ✅ Rastreo de dispositivos específicos
- ✅ Verificación de autenticidad
- ✅ Control antifraude

## 🔄 Relaciones del Sistema

```
Profile (Perfil)
  ├─> Suppliers (Proveedores)
  └─> Products (Productos)
        └─> Supplier (Proveedor) [opcional]

Supplier
  ├─> Profile (Perfil dueño)
  └─> Products (Productos suministrados)

Product
  ├─> Profile (Perfil)
  ├─> Supplier (Proveedor) [opcional]
  └─> IMEI (Identificador único) [opcional]
```

## 📝 Ejemplos de Uso Completo

### Escenario: Crear Proveedor y Producto

```bash
# 1. Crear proveedor
POST /api/suppliers
{
  "profile_id": 1,
  "nombre": "TechStore Global",
  "contacto": "María González",
  "telefono": "+504 9876-5432",
  "email": "maria@techstore.com",
  "activo": true
}

# Respuesta: { "id": 10, ... }

# 2. Crear producto con ese proveedor
POST /api/products
{
  "profile_id": 1,
  "supplier_id": 10,
  "sku": "APP-IP15PRO-512-TIT",
  "nombre": "iPhone 15 Pro 512GB Titanio",
  "categoria": "celular",
  "marca": "Apple",
  "modelo": "iPhone 15 Pro",
  "capacidad": "512GB",
  "condicion": "nuevo",
  "precio": 32000.00,
  "imei": "359872061234567",
  "garantia_meses": 12,
  "stock_inicial": 2
}
```

### Escenario: Buscar Producto por IMEI para Reclamo

```bash
# Buscar producto con IMEI específico
GET /api/products?search=359872061234567

# Respuesta incluye supplier_id
# Luego obtener datos del proveedor
GET /api/suppliers/10

# Contactar al proveedor usando la información obtenida
```

## ✨ Estado: LISTO PARA USAR

La funcionalidad está completamente implementada y lista para producción. Solo requiere ejecutar la migración de base de datos.

## 📞 Soporte

Para gestionar reclamos con esta funcionalidad:
1. Buscar producto (por SKU, nombre o IMEI)
2. Ver proveedor asignado
3. Acceder a datos de contacto del proveedor
4. Procesar reclamo con la información completa
