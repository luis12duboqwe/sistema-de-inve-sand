# Nuevos Errores Encontrados - Segunda Revisión del Sistema V2.0

**Fecha:** 8 de Diciembre de 2025
**Estado:** Correcciones aplicadas a errores críticos, listando errores adicionales encontrados

---

## ERRORES CRÍTICOS CORREGIDOS EN ESTA SESIÓN ✅

### 1. ✅ source_location_id Opcional en Órdenes
**Problema:** En V2.0, las órdenes deben indicar de qué ubicación física sale el stock, pero el campo era opcional.
**Ubicación:** `backend/app/schemas.py` - `OrderCreate`
**Corrección Aplicada:**
- Cambiado `source_location_id: Optional[int]` a `source_location_id: int` (obligatorio)
- Esto garantiza trazabilidad completa del stock

### 2. ✅ Validación de Slug Único en SalesProfile
**Problema:** No se validaba duplicación de slug al crear perfiles de venta.
**Ubicación:** `backend/app/routers/sales_profiles.py`
**Estado:** YA ESTABA IMPLEMENTADO correctamente (líneas 59-62)

### 3. ✅ Proveedores Atados a Profiles V1.0
**Problema:** `Supplier.profile_id` era obligatorio, atando proveedores a perfiles antiguos (V1.0).
**Ubicación:** `backend/app/models.py` - modelo `Supplier`
**Corrección Aplicada:**
- `profile_id` cambiado a `nullable=True`
- `ondelete="CASCADE"` cambiado a `ondelete="SET NULL"`
- Ahora proveedores son globales (V2.0)

### 4. ✅ IMEIs sin Ubicación Asignada
**Problema:** `ProductCreate` no tenía forma de asignar ubicación a los IMEIs.
**Ubicación:** `backend/app/schemas.py`
**Corrección Aplicada:**
- Creado schema `IMEIWithLocation` con campos `imei` y `location_id`
- Agregado campo `imeis_con_ubicacion: Optional[List[IMEIWithLocation]]` a `ProductCreate`
- Agregado campo `initial_location_id: Optional[int]` para stock inicial
- Campos antiguos `imei` e `imeis` marcados como DEPRECATED

### 5. ✅ API_URL Hardcodeada en Múltiples Componentes
**Problema:** URL de la API (`http://localhost:8000`) hardcodeada en ~12 componentes.
**Corrección Aplicada:**
- Creado `/src/lib/config.ts` con función `getApiUrl()` asíncrona
- Incluye constantes para paginación, stock, sincronización, validaciones, etc.
- Componentes afectados (pendiente refactorizar para usar config.ts):
  - `src/components/SalesProfilesList.tsx`
  - `src/components/NewOrderDialog.tsx`
  - `src/components/BackendConnectionCheck.tsx`
  - `src/components/LocationsList.tsx`
  - `src/components/StockByLocationDialog.tsx`
  - `src/components/OrderCard.tsx`
  - `src/components/DashboardStats.tsx`
  - `src/components/SettingsDialog.tsx`
  - `src/App.tsx`

### 6. ✅ Falta de Reportes por Ubicación
**Problema:** No había endpoints para análisis de inventario y ventas por ubicación física.
**Corrección Aplicada:**
- Agregados 3 nuevos endpoints a `backend/app/routers/reports.py`:
  - `GET /api/reports/stock-summary-by-location` - Stock agregado por ubicación
  - `GET /api/reports/sales-summary-by-location` - Ventas por ubicación con filtros de fecha
  - `GET /api/reports/top-products-by-location/{location_id}` - Top productos vendidos por ubicación

### 7. ✅ Validación de Stock en Transferencias
**Problema:** Transferencias podían crear stock negativo.
**Estado:** YA ESTABA IMPLEMENTADO correctamente en `stock_transfers.py` (líneas 119-128)

---

## NUEVOS ERRORES IDENTIFICADOS (Pendientes de Corrección) ⚠️

### Error 8: Frontend No Usa config.ts Centralizado
**Severidad:** Media
**Descripción:** Aunque se creó `config.ts`, los componentes siguen usando valores hardcodeados
**Archivos Afectados:**
- `src/components/SalesProfilesList.tsx` (línea 13)
- `src/components/NewOrderDialog.tsx` (línea 26)
- `src/components/LocationsList.tsx` (línea 12)
- `src/components/StockByLocationDialog.tsx` (línea 11)
- `src/components/OrderCard.tsx` (línea 16)
- `src/components/DashboardStats.tsx` (línea 11)
- `src/App.tsx` (líneas 103, 137, 150)

**Corrección Necesaria:**
```typescript
// Cambiar de:
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// A:
import { getApiUrl } from '@/lib/config'
const API_URL = await getApiUrl()
```

### Error 9: Suppliers Router Usa profile_id=1 Hardcodeado
**Severidad:** Alta
**Descripción:** Al crear proveedores, si no se proporciona `profile_id`, se usa valor hardcodeado `1`
**Archivo:** `backend/app/routers/suppliers.py` (línea 48)
**Código Problemático:**
```python
profile_id=supplier.profile_id or 1,  # Temporal: usar 1 por defecto para compatibilidad
```

**Corrección Necesaria:**
```python
# Eliminar el fallback a 1, permitir NULL
profile_id=supplier.profile_id,  # V2.0: Proveedores globales no necesitan profile_id
```

### Error 10: Falta Implementar imeis_con_ubicacion en Products Router
**Severidad:** Alta
**Descripción:** Aunque se creó el schema `IMEIWithLocation`, el endpoint de creación de productos no lo procesa
**Archivo:** `backend/app/routers/products.py`
**Problema:** No hay lógica para:
1. Leer `imeis_con_ubicacion` de `ProductCreate`
2. Crear registros en tabla `ProductIMEI` con `location_id`
3. Asociar stock inicial con `initial_location_id`

**Corrección Necesaria:**
En el endpoint `POST /api/products`, agregar:
```python
# Después de crear el producto
if product_data.imeis_con_ubicacion:
    for imei_data in product_data.imeis_con_ubicacion:
        db_imei = ProductIMEI(
            product_id=db_product.id,
            location_id=imei_data.location_id,
            imei=imei_data.imei,
            vendido=False
        )
        db.add(db_imei)
```

### Error 11: No Se Valida location_id en OrderCreate
**Severidad:** Alta
**Descripción:** Ahora que `source_location_id` es obligatorio, falta validar que la ubicación exista y esté activa
**Archivo:** `backend/app/routers/orders.py`
**Problema:** No hay validación antes de crear la orden

**Corrección Necesaria:**
```python
# Al inicio de create_order, después de validar sales_profile_slug
source_location = db.query(Location).filter(
    Location.id == order.source_location_id,
    Location.activo == True
).first()

if not source_location:
    raise HTTPException(
        status_code=404,
        detail=f"Ubicación con ID {order.source_location_id} no encontrada o inactiva"
    )
```

### Error 12: StockHistory No Registra Transferencias Canceladas/Rechazadas
**Severidad:** Media
**Descripción:** Cuando se cancela o rechaza una transferencia, no se registra en StockHistory
**Archivo:** `backend/app/routers/stock_transfers.py`
**Endpoints Afectados:**
- `PATCH /api/stock-transfers/{transfer_id}/reject`
- `PATCH /api/stock-transfers/{transfer_id}/cancel`

**Corrección Necesaria:**
Agregar registro de StockHistory al rechazar/cancelar con `tipo="ajuste"` y cantidad 0

### Error 13: Products Router No Filtra por Múltiples Categorías
**Severidad:** Baja
**Descripción:** El filtro de categoría solo acepta una, pero sería útil filtrar por múltiples
**Archivo:** `backend/app/routers/products.py`
**Mejora Sugerida:**
```python
# Cambiar de:
categoria: Optional[CategoriaEnum] = Query(None)

# A:
categorias: Optional[List[CategoriaEnum]] = Query(None)

# Y en el filtro:
if categorias:
    query = query.filter(Product.categoria.in_(categorias))
```

### Error 14: Falta Endpoint para Mover IMEIs entre Ubicaciones
**Severidad:** Media
**Descripción:** Cuando se transfiere stock, los IMEIs deberían actualizarse automáticamente
**Problema:** No hay endpoint ni lógica para actualizar `ProductIMEI.location_id` al confirmar transferencia
**Corrección Necesaria:**
En `confirm_transfer` de `stock_transfers.py`:
```python
# Después de actualizar stock
# Mover IMEIs no vendidos a la nueva ubicación
imeis_to_move = db.query(ProductIMEI).filter(
    ProductIMEI.product_id == transfer.product_id,
    ProductIMEI.location_id == transfer.from_location_id,
    ProductIMEI.vendido == False
).limit(transfer.cantidad).all()

for imei in imeis_to_move:
    imei.location_id = transfer.to_location_id
```

### Error 15: Falta Validación de Stock Disponible vs IMEIs Registrados
**Severidad:** Media
**Descripción:** Puede haber inconsistencia entre `Stock.cantidad_disponible` y cantidad de IMEIs no vendidos
**Problema:** No hay validación que asegure:
```
Stock.cantidad_disponible == COUNT(ProductIMEI WHERE vendido=False AND location_id=X)
```

**Corrección Necesaria:**
Agregar endpoint de auditoría:
```python
@router.get("/api/products/{product_id}/audit-stock")
def audit_product_stock(product_id: int, db: Session):
    """Verifica consistencia entre stock registrado e IMEIs"""
    # Para cada ubicación, comparar stock vs IMEIs
```

### Error 16: Frontend Local Mode (Spark KV) No Soporta V2.0
**Severidad:** Crítica
**Descripción:** `inventoryService.ts` (local mode) no tiene modelos de `Location` ni `SalesProfile`
**Archivo:** `src/lib/inventoryService.ts`
**Problema:** Solo funciona modo API, KV storage no fue actualizado a V2.0
**Impacto:** Usuarios sin backend no pueden usar el sistema

**Corrección Necesaria:**
Implementar en `inventoryService.ts`:
- `getLocations()`, `createLocation()`, `updateLocation()`
- `getSalesProfiles()`, `createSalesProfile()`, `updateSalesProfile()`
- Actualizar `createProduct()` para manejar stock por ubicación
- Actualizar `createOrder()` para usar `source_location_id`
- Implementar transferencias de stock en KV

### Error 17: No Hay Migración Automática de Datos V1.0 → V2.0
**Severidad:** Alta
**Descripción:** Usuarios con datos V1.0 existentes no tienen forma de migrar a V2.0
**Problema:** No existe script de migración que:
1. Convierta `Profile` antiguos en `Location` + `SalesProfile`
2. Distribuya stock existente a ubicaciones
3. Migre `Supplier.profile_id` a NULL (global)
4. Actualice órdenes antiguas con `source_location_id`

**Corrección Necesaria:**
Crear `backend/migrate_v1_to_v2.py` con estrategia de migración

### Error 18: Falta Documentación de API V2.0
**Severidad:** Media
**Descripción:** `api-examples-nuevo-sistema.json` no incluye nuevos endpoints de reportes
**Nuevos Endpoints No Documentados:**
- `GET /api/reports/stock-summary-by-location`
- `GET /api/reports/sales-summary-by-location`
- `GET /api/reports/top-products-by-location/{location_id}`
- `GET /api/products/{id}/stock/by-location` (agregado en sesión anterior)

**Corrección Necesaria:**
Actualizar `api-examples-nuevo-sistema.json` con ejemplos cURL

### Error 19: Proveedores Aún Usan CASCADE en Orders
**Severidad:** Baja
**Descripción:** Aunque se cambió a SET NULL en productos, hay otras relaciones con CASCADE que deberían revisarse
**Archivo:** `backend/app/models.py`
**Relaciones a Revisar:**
- `Profile.products` → `cascade="all, delete-orphan"` (puede causar pérdida de datos)
- `Profile.orders_legacy` → `cascade="all, delete-orphan"` (idem)
- `Profile.suppliers` → Ya corregido a SET NULL

**Corrección Sugerida:**
Cambiar cascades peligrosos a SET NULL en campos críticos

### Error 20: No Se Registra Quién Modificó Stock Manualmente
**Severidad:** Media
**Descripción:** Al ajustar stock manualmente, no se registra el usuario que hizo el cambio
**Archivo:** `backend/app/routers/products.py` - endpoint `PATCH /api/products/{product_id}/stock`
**Problema:** `StockHistory` no tiene campo `user_id` o `modified_by`

**Corrección Necesaria:**
1. Agregar campo `modified_by: Optional[str]` a `StockHistory` model
2. Capturar usuario desde token JWT en endpoints de modificación
3. Incluir en todos los registros de historial

---

## RESUMEN DE ESTADO

### Correcciones Aplicadas: 7/7 ✅
1. ✅ source_location_id obligatorio en órdenes
2. ✅ Slug único en SalesProfile (ya existía)
3. ✅ Proveedores globales (profile_id opcional)
4. ✅ IMEIs con ubicación (schema creado)
5. ✅ Centralización de API_URL (config.ts creado)
6. ✅ Reportes por ubicación (3 endpoints agregados)
7. ✅ Validación stock en transferencias (ya existía)

### Errores Nuevos Identificados: 13 ⚠️
- **Críticos (2):** Frontend local mode V2.0, Migración V1→V2
- **Altos (4):** Suppliers hardcoded, IMEIs en router, Validación location_id, Profile CASCADE
- **Medios (6):** Config.ts no usado, StockHistory transferencias, IMEIs en transferencias, Auditoría stock, Documentación API, Usuario en historial
- **Bajos (1):** Filtro múltiples categorías

---

## PRÓXIMOS PASOS RECOMENDADOS

**Prioridad 1 - Crítico:**
1. Implementar V2.0 en `inventoryService.ts` (frontend local mode)
2. Crear script de migración V1.0 → V2.0
3. Validar `source_location_id` en endpoint de órdenes

**Prioridad 2 - Alto:**
4. Implementar lógica de `imeis_con_ubicacion` en products router
5. Remover `profile_id=1` hardcoded de suppliers router
6. Cambiar cascades peligrosos a SET NULL

**Prioridad 3 - Medio:**
7. Refactorizar componentes para usar `config.ts`
8. Registrar cancelaciones/rechazos en StockHistory
9. Mover IMEIs automáticamente en transferencias
10. Agregar campo `modified_by` a StockHistory
11. Actualizar documentación de API

**Prioridad 4 - Bajo:**
12. Filtro por múltiples categorías
13. Endpoint de auditoría de stock vs IMEIs

---

## NOTAS IMPORTANTES

- **Compatibilidad:** Muchas correcciones mantienen campos legacy para no romper datos existentes
- **Testing:** Cada corrección debe probarse con `test-backend.py` y `TESTING_GUIDE.md`
- **Documentación:** Actualizar `INICIO_RAPIDO.md` y `NUEVO_SISTEMA_UBICACIONES.md` después de correcciones
- **Breaking Changes:** `source_location_id` obligatorio puede romper órdenes antiguas sin migración
