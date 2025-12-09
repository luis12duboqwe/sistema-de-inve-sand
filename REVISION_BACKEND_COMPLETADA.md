# ✅ REVISIÓN BACKEND COMPLETADA - Alineación V2.0

**Fecha:** 8 de diciembre de 2025  
**Contexto:** Correcciones backend para alinear con visión de negocio único con inventario global

---

## ✅ CORRECCIONES APLICADAS EN ESTA SESIÓN

### 1. **GET /api/products** - Productos globales ✅

**Archivo:** `/backend/app/routers/products.py`

**ANTES:**
```python
def list_products(
    profile_slug: Optional[str] = Query(...),  # ❌ Filtraba por perfil
    ...
):
    if profile_slug:
        query = query.filter(Product.profile_id == profile.id)  # ❌ Segmentaba inventario
```

**AHORA:**
```python
def list_products(
    search: Optional[str] = Query(...),  # ✅ Solo búsqueda y paginación
    ...
):
    # Sin filtro por profile - TODOS los productos visibles
    query = db.query(Product).join(Stock)
```

**Impacto:**
- ✅ Todos los canales de venta ven TODO el inventario
- ✅ No más segmentación de productos por perfil
- ✅ Docstring actualizado con nota V2.0

---

### 2. **GET /api/suppliers** - Proveedores globales ✅

**Archivo:** `/backend/app/routers/suppliers.py`

**ANTES:**
```python
def list_suppliers(
    profile_id: Optional[int] = Query(...),  # ❌ Filtraba por perfil
    ...
):
    if profile_id:
        query = query.filter(Supplier.profile_id == profile_id)  # ❌ Segmentaba proveedores
```

**AHORA:**
```python
def list_suppliers(
    search: Optional[str] = Query(...),  # ✅ Solo búsqueda
    ...
):
    query = db.query(Supplier)  # ✅ Proveedores globales
```

**Impacto:**
- ✅ Proveedores visibles para todo el negocio
- ✅ Sin duplicación de proveedores por perfil
- ✅ Docstring actualizado con nota V2.0

---

### 3. **POST /api/suppliers** - Sin validación de perfil ✅

**ANTES:**
```python
def create_supplier(...):
    profile = db.query(Profile).filter(Profile.id == supplier.profile_id).first()
    if not profile:
        raise HTTPException(404)  # ❌ Requería perfil válido
```

**AHORA:**
```python
def create_supplier(...):
    # Crear proveedor directamente (sin validación de profile)
    # TODO: Migración pendiente para eliminar profile_id de tabla
    db_supplier = Supplier(
        profile_id=supplier.profile_id or 1,  # Temporal por compatibilidad
        ...
```

**Impacto:**
- ✅ No requiere validar perfil al crear proveedor
- ⚠️ profile_id=1 por defecto (temporal hasta migración)

---

### 4. **Schemas de Supplier** - profile_id opcional ✅

**Archivo:** `/backend/app/schemas.py`

**ANTES:**
```python
class SupplierCreate(SupplierBase):
    profile_id: int  # ❌ Obligatorio

class SupplierResponse(SupplierBase):
    profile_id: int  # ❌ Obligatorio
```

**AHORA:**
```python
class SupplierCreate(SupplierBase):
    profile_id: Optional[int] = None  # V2.0: Deprecated, proveedores son globales

class SupplierResponse(SupplierBase):
    profile_id: Optional[int] = None  # V2.0: Deprecated, proveedores son globales
```

**Impacto:**
- ✅ Frontend puede omitir profile_id al crear proveedores
- ✅ Compatible con datos existentes que tienen profile_id

---

## 📋 PROBLEMAS ADICIONALES IDENTIFICADOS (Para siguiente iteración)

### 🔴 CRÍTICO 1: Órdenes filtran por profile_id (V1.0) en lugar de sales_profile_id (V2.0)

**Ubicación:** `/backend/app/routers/orders.py` líneas 91, 119, 140, 174

**Problema:**
```python
def list_orders(
    profile_slug: Optional[str] = Query(...),  # ❌ V1.0
    ...
):
    query = query.filter(Order.profile_id == profile.id)  # ❌ Filtro V1.0
```

**Cómo debería ser:**
```python
def list_orders(
    sales_profile_slug: Optional[str] = Query(...),  # ✅ V2.0
    ...
):
    query = query.filter(Order.sales_profile_id == sales_profile.id)  # ✅ V2.0
```

**Justificación desde tu visión:**
- Un bot WhatsApp debe ver SOLO SUS ventas (las que él hizo)
- No debe ver ventas de otros bots o vendedores
- Pero el filtro debe ser por `sales_profile_id` (quién vendió), no por `profile_id` (legacy)

**Impacto:**
- 🔴 **ALTO:** Las órdenes no se filtran correctamente por canal de venta
- 🔴 Los reportes por vendedor/bot no funcionan en V2.0

---

### 🟠 IMPORTANTE 2: Customers filtran por profile_id (V1.0)

**Ubicación:** `/backend/app/routers/customers.py` líneas 16, 34-41, 87, 105-112, 138, 156-163

**Problema:**
Similar al de órdenes, los endpoints de customers filtran por `profile_slug` (V1.0) en lugar de `sales_profile_slug` (V2.0).

**Solución:**
Cambiar todos los filtros de `Order.profile_id == profile.id` a `Order.sales_profile_id == sales_profile.id`

**Impacto:**
- 🟠 **MEDIO:** Estadísticas de clientes no se agrupan correctamente por canal de venta

---

### 🟡 MEJORABLE 3: Migración de base de datos pendiente

**Tablas afectadas:**
1. `suppliers` - Columna `profile_id` debería ser `nullable=True` o eliminarse
2. `products` - Columna `profile_id` ya está marcada como temporal en comentario
3. `orders` - Debe depender de `sales_profile_id`, no de `profile_id`

**Migración necesaria:**
```sql
-- 1. Hacer profile_id nullable en suppliers
ALTER TABLE suppliers ALTER COLUMN profile_id DROP NOT NULL;

-- 2. Actualizar suppliers existentes a NULL
UPDATE suppliers SET profile_id = NULL;

-- 3. Eventualmente eliminar columna
-- ALTER TABLE suppliers DROP COLUMN profile_id;

-- 4. Hacer profile_id nullable en products
ALTER TABLE products ALTER COLUMN profile_id DROP NOT NULL;

-- 5. Actualizar products existentes a NULL
UPDATE products SET profile_id = NULL;
```

**Impacto:**
- 🟡 **BAJO por ahora:** Todo funciona con valores por defecto
- 🟡 Necesario para limpieza completa del modelo V1.0

---

### 🟢 OBSERVACIÓN 4: Índices de base de datos obsoletos

**Ubicación:** `/backend/app/models.py`

```python
class Supplier(Base):
    ...
    __table_args__ = (
        Index('idx_supplier_profile_active', 'profile_id', 'activo'),  # ❌ Índice V1.0
    )
```

**Problema:** Hay un índice compuesto sobre `profile_id` + `activo` que ya no se usará.

**Solución futura:**
```python
__table_args__ = (
    Index('idx_supplier_active', 'activo'),  # ✅ Solo activo
)
```

---

## 📊 ESTADO ACTUAL DEL BACKEND

### ✅ ENDPOINTS V2.0 COMPLETOS

| Endpoint | Estado | Notas |
|----------|--------|-------|
| GET /api/products | ✅ V2.0 | Productos globales |
| POST /api/products | ✅ V2.0 | Acepta profile_id opcional (legacy) |
| GET /api/suppliers | ✅ V2.0 | Proveedores globales |
| POST /api/suppliers | ✅ V2.0 | profile_id opcional |
| GET /api/locations | ✅ V2.0 | CRUD completo ubicaciones |
| GET /api/sales-profiles | ✅ V2.0 | CRUD completo canales venta |
| GET /api/products/{id}/stock/by-location | ✅ V2.0 | Stock por ubicación |
| POST /api/stock/transfer | ✅ V2.0 | Transferencias entre ubicaciones |

### ⚠️ ENDPOINTS REQUIEREN ACTUALIZACIÓN

| Endpoint | Problema | Prioridad |
|----------|----------|-----------|
| GET /api/orders | Filtra por profile_id V1.0 | 🔴 CRÍTICO |
| GET /api/orders/stats | Filtra por profile_id V1.0 | 🔴 CRÍTICO |
| GET /api/customers | Filtra por profile_id V1.0 | 🟠 IMPORTANTE |
| GET /api/customers/top | Filtra por profile_id V1.0 | 🟠 IMPORTANTE |
| GET /api/customers/{phone}/history | Filtra por profile_id V1.0 | 🟠 IMPORTANTE |

---

## 🎯 PRÓXIMOS PASOS RECOMENDADOS

### Iteración 1 (CRÍTICO - 2-3 horas)
1. ✅ **Orders Router:** Cambiar filtros de `profile_slug` → `sales_profile_slug`
2. ✅ **Orders Router:** Actualizar queries de `profile_id` → `sales_profile_id`
3. ✅ **Testing:** Verificar que filtros por canal de venta funcionan

### Iteración 2 (IMPORTANTE - 1-2 horas)
4. ✅ **Customers Router:** Cambiar filtros de `profile_slug` → `sales_profile_slug`
5. ✅ **Customers Router:** Actualizar queries a V2.0
6. ✅ **Testing:** Verificar estadísticas de clientes por canal

### Iteración 3 (MEJORABLE - 2-3 horas)
7. ✅ **Migración DB:** Hacer `profile_id` nullable en `suppliers` y `products`
8. ✅ **Migración DB:** Actualizar datos existentes
9. ✅ **Models:** Eliminar índices obsoletos
10. ✅ **Limpieza:** Eventualmente eliminar columnas `profile_id`

---

## 📝 RESUMEN DE CAMBIOS APLICADOS

### Archivos modificados en esta sesión:

1. **`/backend/app/routers/products.py`**
   - ❌ Eliminado parámetro `profile_slug`
   - ❌ Eliminado filtro por `profile_id`
   - ✅ Docstring actualizado con nota V2.0
   - Líneas afectadas: 58-87

2. **`/backend/app/routers/suppliers.py`**
   - ❌ Eliminado parámetro `profile_id` de `list_suppliers`
   - ❌ Eliminado filtro por `profile_id`
   - ❌ Eliminada validación de profile en `create_supplier`
   - ✅ profile_id con valor por defecto temporal (1)
   - ✅ Docstrings actualizados con notas V2.0
   - Líneas afectadas: 29-50, 68-91

3. **`/backend/app/schemas.py`**
   - ✅ `SupplierCreate.profile_id` → `Optional[int] = None`
   - ✅ `SupplierResponse.profile_id` → `Optional[int] = None`
   - Líneas afectadas: 189-191, 204-206

### Compatibilidad:
- ✅ **Backend:** Compatible hacia atrás (acepta profile_id pero no lo requiere)
- ✅ **Frontend:** Ya actualizado en sesión anterior
- ⚠️ **Datos existentes:** Funcionan pero tienen profile_id deprecated

---

## 🔍 VALIDACIÓN RECOMENDADA

### Testing manual sugerido:

```bash
# 1. Listar productos sin filtro (debe mostrar TODOS)
curl http://localhost:8000/api/products

# 2. Listar proveedores (debe mostrar TODOS)
curl http://localhost:8000/api/suppliers

# 3. Crear proveedor sin profile_id
curl -X POST http://localhost:8000/api/suppliers \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Proveedor Global", "activo": true}'

# 4. Verificar que frontend carga productos y suppliers correctamente
# (Abrir navegador y crear orden nueva)
```

### Puntos a verificar:
- [ ] Productos se listan sin filtro por perfil
- [ ] Suppliers se listan sin filtro por perfil
- [ ] NewOrderDialog muestra TODOS los productos
- [ ] NewProductDialog carga TODOS los suppliers
- [ ] No hay errores de validación al crear supplier sin profile_id

---

## 💡 LECCIONES APRENDIDAS

### Arquitectura V1.0 vs V2.0

**V1.0 (Multi-tenant):**
- Cada "Profile" = negocio independiente
- Productos, suppliers, órdenes segmentados por profile_id
- Cada profile tiene su propio inventario aislado

**V2.0 (Single business, multi-location, multi-channel):**
- **Location** = ubicación física (tienda, bodega)
- **SalesProfile** = canal de venta (bot, vendedor)
- **Productos** = globales, visibles para todos
- **Stock** = por ubicación física
- **Órdenes** = registran quién vendió (sales_profile_id) y de dónde salió el stock (source_location_id)
- **Suppliers** = globales del negocio

### Patrones de migración V1.0 → V2.0

1. **Hacer opcionales antes de eliminar:** `profile_id: Optional[int] = None`
2. **Valores por defecto temporales:** `profile_id or 1`
3. **Documentar deprecation:** Comentarios "V2.0: Deprecated"
4. **Actualizar docstrings:** Explicar nueva arquitectura
5. **Testing incremental:** Verificar cada cambio individualmente

---

**Estado:** Backend parcialmente migrado a V2.0. Productos y Suppliers completamente globales. Órdenes y Customers pendientes de actualización a sales_profile_id.
