# Transferencias de Stock Entre Perfiles

## Descripción

El sistema ahora permite transferir stock de productos entre diferentes perfiles de manera sencilla y rastreable. Esta funcionalidad es útil para:

- Redistribuir inventario entre sucursales o perfiles
- Balancear stock entre diferentes unidades de negocio
- Mantener un historial completo de movimientos de inventario
- Crear productos automáticamente en perfiles de destino cuando sea necesario

## Características Principales

### 1. **Transferencia Automática de Stock**
   - Reduce el stock en el perfil de origen
   - Aumenta el stock en el perfil de destino
   - Si el producto no existe en el destino, se crea automáticamente con las mismas características

### 2. **Validaciones Integradas**
   - Verifica que haya stock suficiente antes de transferir
   - Valida que los perfiles de origen y destino existan
   - Previene transferencias al mismo perfil
   - Confirma que el producto pertenece al perfil de origen

### 3. **Trazabilidad Completa**
   - Registra cada transferencia con fecha y hora
   - Almacena información del usuario que realizó la transferencia
   - Permite agregar notas explicativas
   - Mantiene historial completo de movimientos

## Uso en la Interfaz

### Transferir Stock

1. **Navega a la pestaña de Productos**
2. **Selecciona un perfil** (no puede ser "Todos los perfiles")
3. **Localiza el producto** que deseas transferir
4. **Haz clic en el botón de transferencia** (ícono de flechas ↔)
5. **Completa el formulario:**
   - **Perfil Destino**: Selecciona a qué perfil transferir
   - **Cantidad**: Especifica cuántas unidades transferir (máximo: stock disponible)
   - **Notas** (opcional): Agrega observaciones sobre la transferencia

6. **Confirma la transferencia**

### Información Mostrada

El diálogo de transferencia muestra:
- Nombre y SKU del producto
- Stock actual disponible
- Perfil de origen (actual)
- Perfiles de destino disponibles
- Límite de cantidad a transferir

## API Endpoints

### Crear una Transferencia

```http
POST /api/stock-transfers
Content-Type: application/json

{
  "product_id": 1,
  "from_profile_slug": "softmobile",
  "to_profile_slug": "hardmobile",
  "cantidad": 5,
  "notas": "Rebalanceo de inventario",
  "created_by": "Admin"
}
```

**Respuesta exitosa (201):**
```json
{
  "id": 1,
  "product_id": 1,
  "from_profile_id": 1,
  "to_profile_id": 2,
  "cantidad": 5,
  "notas": "Rebalanceo de inventario",
  "created_at": "2025-12-06T10:30:00Z",
  "created_by": "Admin",
  "product_nombre": "Samsung Galaxy S24",
  "product_sku": "SM-S24-256-NEGRO",
  "from_profile_name": "Softmobile",
  "to_profile_name": "Hardmobile"
}
```

### Listar Transferencias

```http
GET /api/stock-transfers?profile_slug=softmobile&page=1&per_page=50
```

**Parámetros de consulta:**
- `profile_slug` (opcional): Filtra transferencias donde el perfil sea origen o destino
- `product_id` (opcional): Filtra transferencias de un producto específico
- `page`: Número de página (default: 1)
- `per_page`: Resultados por página (default: 50, max: 100)

**Respuesta:**
```json
{
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "from_profile_id": 1,
      "to_profile_id": 2,
      "cantidad": 5,
      "notas": "Rebalanceo de inventario",
      "created_at": "2025-12-06T10:30:00Z",
      "created_by": "Admin",
      "product_nombre": "Samsung Galaxy S24",
      "product_sku": "SM-S24-256-NEGRO",
      "from_profile_name": "Softmobile",
      "to_profile_name": "Hardmobile"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50,
  "total_pages": 1
}
```

### Obtener Detalles de una Transferencia

```http
GET /api/stock-transfers/{transfer_id}
```

## Modelo de Base de Datos

### Tabla: `stock_transfers`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer | ID único de la transferencia |
| `product_id` | Integer | ID del producto transferido |
| `from_profile_id` | Integer | ID del perfil de origen |
| `to_profile_id` | Integer | ID del perfil de destino |
| `cantidad` | Integer | Cantidad transferida |
| `notas` | Text | Notas opcionales sobre la transferencia |
| `created_at` | DateTime | Fecha y hora de la transferencia |
| `created_by` | String | Usuario que realizó la transferencia |

**Índices:**
- `idx_transfer_product`: Índice en `product_id`
- `idx_transfer_from_profile`: Índice en `from_profile_id`
- `idx_transfer_to_profile`: Índice en `to_profile_id`
- `idx_transfer_created`: Índice en `created_at`

## Instalación y Migración

### 1. Ejecutar la Migración de Base de Datos

Desde el directorio `backend`:

```bash
python3 migrate_stock_transfers.py
```

Esto creará la tabla `stock_transfers` en la base de datos.

### 2. Verificar la Instalación

El script de migración mostrará:
```
Aplicando migración: Agregar tabla stock_transfers...
✓ Tabla stock_transfers creada exitosamente

✓ Migración completada con éxito
Ahora puedes transferir stock entre perfiles usando el endpoint /api/stock-transfers
```

### 3. Reiniciar el Backend

```bash
cd backend
./start.sh
```

O en Windows:
```bash
cd backend
start.bat
```

## Flujo de Transferencia

```
1. Usuario selecciona producto del Perfil A
2. Usuario hace clic en botón de transferencia
3. Usuario selecciona Perfil B como destino
4. Usuario especifica cantidad (validado contra stock disponible)
5. Sistema valida:
   - Stock suficiente en Perfil A
   - Perfiles válidos y diferentes
   - Producto pertenece a Perfil A
6. Sistema ejecuta:
   - Reduce stock en Perfil A
   - Verifica si producto existe en Perfil B
   - Si no existe, crea producto en Perfil B
   - Aumenta stock en Perfil B
   - Registra transferencia en historial
7. Usuario recibe confirmación
8. Stock se actualiza en ambos perfiles
```

## Creación Automática de Productos

Cuando se transfiere stock a un perfil donde el producto no existe:

1. **Se crea automáticamente** un nuevo producto en el perfil destino
2. **Se copian todas las características** del producto original:
   - SKU (mismo que el original)
   - Nombre
   - Categoría
   - Marca, modelo, capacidad
   - Condición
   - Precio y moneda
   - Garantía
   - Estado activo

3. **Se inicializa el stock** con la cantidad transferida
4. **El producto queda listo** para uso inmediato en el perfil destino

## Casos de Uso

### 1. Rebalanceo de Inventario
Cuando una sucursal tiene exceso y otra tiene déficit del mismo producto.

### 2. Traslado Entre Ubicaciones
Mover inventario físicamente entre diferentes ubicaciones o almacenes.

### 3. Consolidación de Stock
Centralizar inventario de varios perfiles en uno solo.

### 4. Distribución Inicial
Distribuir productos nuevos desde un perfil central a varios perfiles de venta.

## Notas Importantes

- ⚠️ **Las transferencias son permanentes** y modifican el stock inmediatamente
- ✅ **Se mantiene un historial completo** de todas las transferencias
- 🔒 **Las validaciones previenen** transferencias inválidas
- 📊 **Trazabilidad total** para auditoría y reportes
- 🔄 **Sincronización automática** entre perfiles cuando se usa la API

## Próximas Mejoras

- [ ] Reportes de transferencias por período
- [ ] Aprobación de transferencias para cantidades grandes
- [ ] Notificaciones automáticas de transferencias
- [ ] Reversión de transferencias (con validaciones)
- [ ] Exportar historial de transferencias a CSV/Excel
