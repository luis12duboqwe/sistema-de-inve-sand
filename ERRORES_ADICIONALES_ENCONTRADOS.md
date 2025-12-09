# 🔍 ERRORES ADICIONALES ENCONTRADOS DURANTE CORRECCIONES

**Fecha**: 8 de Diciembre, 2025  
**Durante**: Corrección de Problemas Críticos V2.0

---

## 🚨 ERRORES CRÍTICOS ADICIONALES

### 16. **FALTA ENDPOINT PARA OBTENER STOCK POR UBICACIÓN DE UN PRODUCTO**

**Problema**: No existe un endpoint dedicado para consultar el desglose de stock de un producto específico por ubicación.

**Evidencia**:
```typescript
// Frontend - NewOrderDialog.tsx línea 135
const response = await fetch(`${API_URL}/products/${item.product_id}/stock/by-location`)
// ❌ Este endpoint NO EXISTÍA
```

**Impacto en el Negocio**:
- El frontend no puede validar stock antes de crear órdenes
- No se puede mostrar dónde está disponible cada producto
- Vendedores no saben de qué tienda pueden vender

**✅ CORREGIDO**: Agregado endpoint `GET /api/products/{product_id}/stock/by-location`

---

### 17. **PAGINACIÓN INCONSISTENTE EN RESPONSE**

**Problema**: Algunos endpoints retornan `total_pages` y otros no.

**Evidencia**:
```python
# stock_transfers.py - usa total_pages
return PaginatedResponse(
    total_pages=total_pages  # ✅ Correcto
)

# Pero PaginatedResponse schema define:
class PaginatedResponse(BaseModel, Generic[T]):
    pages: int  # ❌ Debería ser "pages" no "total_pages"
```

**Impacto**: Frontend no puede paginar correctamente si el campo cambia de nombre.

**✅ CORREGIDO**: Estandarizado a usar `pages` en todos los endpoints.

---

### 18. **NO SE REGISTRA EN STOCK_HISTORY AL CREAR ÓRDENES**

**Problema**: Al crear una orden y descontar stock, NO se crea una entrada en `StockHistory`.

**Evidencia**:
```python
# backend/app/routers/orders.py línea 394-397
# Descuenta stock pero NO registra en historial
item_data["stock"].cantidad_disponible = stock_nuevo
# ❌ Falta:
# StockHistory.create(tipo_cambio='venta', ...)
```

**Impacto en el Negocio**:
1. **Auditoría incompleta**: No se puede rastrear todas las ventas en el historial
2. **Trazabilidad rota**: ¿Quién vendió qué y cuándo?
3. **Reconciliación imposible**: No se puede reconstruir inventario histórico

**Solución requerida**:
```python
# Después de descontar stock en órdenes:
history_entry = StockHistory(
    product_id=product.id,
    location_id=order.source_location_id,
    tipo_cambio='venta',
    cantidad=-item.cantidad,  # Negativo = salida
    stock_anterior=stock_anterior,
    stock_nuevo=stock_nuevo,
    referencia_id=db_order.id,
    referencia_tipo='order',
    notas=f"Venta a {order.customer_name}",
    usuario=sales_profile.name if sales_profile else None
)
db.add(history_entry)
```

---

### 19. **FALTA VALIDACIÓN: LOCATION_ID NO PUEDE SER NULL EN STOCK V2.0**

**Problema**: El modelo permite `location_id` nullable pero en V2.0 DEBE ser obligatorio.

**Evidencia**:
```python
# backend/app/models.py - Stock
location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
# ✅ nullable=False CORRECTO

# PERO en orders.py línea 332:
stock = db.query(Stock).filter(
    Stock.location_id.is_(None)  # ❌ Busca stock SIN ubicación (legacy V1)
)
```

**Impacto**: El sistema acepta y busca stock sin ubicación, contradiciendo V2.0.

**Solución**: Eliminar el código legacy que busca `location_id.is_(None)` y forzar que TODAS las órdenes especifiquen `source_location_id`.

---

### 20. **PRODUCTS.PROFILE_ID PUEDE SER NULL PERO TIENE FOREIGN KEY**

**Problema**: El campo está marcado como `nullable=True` pero tiene relación con Profile que puede ser eliminado.

**Evidencia**:
```python
# models.py
class Product(Base):
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True)
    # ⚠️ Si Profile se elimina, CASCADE elimina productos
```

**Impacto en el Negocio**:
1. Si se elimina un Profile legacy, se pierden TODOS los productos asociados
2. Contradice "productos globales" de V2.0
3. Pérdida masiva de datos accidental

**Solución**:
```python
profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
# ✅ SET NULL: Si se elimina Profile, productos quedan sin perfil (globales)
```

---

### 21. **FRONTEND: API_URL HARDCODEADO EN MÚLTIPLES COMPONENTES**

**Problema**: Cada componente define su propia constante API_URL en lugar de usar configuración central.

**Evidencia**:
```typescript
// NewOrderDialog.tsx línea 26
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// LocationsList.tsx línea 13
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// SalesProfilesList.tsx línea XX
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// ❌ Repetido en ~15 componentes
```

**Impacto**:
1. Difícil de mantener
2. Riesgo de inconsistencias
3. No respeta `settings_api_url` del sistema

**Solución**: Crear `src/lib/config.ts`:
```typescript
export const getApiUrl = async () => {
  const kv = getKV()
  return await kv.get<string>('settings_api_url') || 
         import.meta.env.VITE_API_URL || 
         'http://localhost:8000/api'
}
```

---

### 22. **FALTA VALIDACIÓN DE UNICIDAD DE SLUG EN SALES_PROFILE**

**Problema**: El modelo tiene `slug` único, pero el endpoint POST no valida antes de insertar.

**Evidencia**:
```python
# models.py
class SalesProfile(Base):
    slug = Column(String, unique=True, nullable=False, index=True)

# ❌ Pero en sales_profiles.py no hay validación:
@router.post("")
def create_sales_profile(profile: SalesProfileCreate, db: Session):
    # NO verifica si slug ya existe
    db_profile = SalesProfile(**profile.dict())
    db.add(db_profile)
    db.commit()  # ← Puede fallar con IntegrityError
```

**Impacto**: Error 500 en lugar de 400 con mensaje claro.

**Solución**:
```python
# Antes de crear:
existing = db.query(SalesProfile).filter(SalesProfile.slug == profile.slug).first()
if existing:
    raise HTTPException(400, f"El slug '{profile.slug}' ya está en uso")
```

---

### 23. **SUPPLIER.PROFILE_ID NULLABLE=FALSE PERO SCHEMA DICE OPCIONAL**

**Problema**: Contradicción entre modelo y schema de suppliers.

**Evidencia**:
```python
# models.py
class Supplier(Base):
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    # ❌ Requiere profile_id

# schemas.py
class SupplierCreate(BaseModel):
    profile_id: Optional[int] = None  # V2.0: Deprecated, proveedores son globales
    # ✅ Dice que es opcional
```

**Impacto**: Endpoint falla al crear supplier sin profile_id.

**Solución**: Cambiar modelo a `nullable=True` y agregar migración para proveedores globales.

---

### 24. **ORDERS SIN SOURCE_LOCATION_ID OBLIGATORIO EN V2.0**

**Problema**: El campo `source_location_id` es opcional pero en V2.0 debería ser obligatorio.

**Evidencia**:
```python
# models.py - Order
source_location_id = Column(Integer, nullable=True)  # ⚠️ Opcional

# orders.py permite crear sin ubicación
if order.source_location_id:
    # Valida ubicación
else:
    # Busca stock legacy ← NO DEBERÍA PERMITIRSE EN V2.0
```

**Impacto en el Negocio**:
- Órdenes sin trazabilidad de ubicación
- Reportes por tienda incompletos
- No se sabe de dónde salió el stock vendido

**Solución**: Hacer obligatorio para V2.0:
```python
# En OrderCreate schema:
source_location_id: int  # Obligatorio, no Optional
```

---

### 25. **IMEIS SIN LOCATION_ID AL CREARLOS**

**Problema**: Al crear IMEIs desde productos, no se asigna la ubicación física.

**Evidencia**:
```python
# products.py línea 182
db_imei = ProductIMEI(
    product_id=db_product.id,
    imei=imei_value.strip(),
    vendido=False
    # ❌ NO asigna location_id
)
```

**Impacto en el Negocio**:
1. No se sabe dónde está físicamente cada celular
2. Imposible hacer inventario por tienda de IMEIs
3. Reclamos de garantía sin ubicación

**Solución**: Requerir `location_id` al crear productos con IMEIs:
```python
class ProductCreate(BaseModel):
    # ...
    imeis: Optional[List[dict]] = None  # [{"imei": "123", "location_id": 1}]
```

---

### 26. **FALTA ENDPOINT: LISTADO DE PRODUCTOS CON FILTRO POR LOCATION_ID**

**Problema**: No se puede filtrar productos por ubicación donde tienen stock.

**Evidencia**:
```python
# products.py
@router.get("")
def list_products(
    search: Optional[str] = None,
    # ❌ NO HAY: location_id: Optional[int] = None
```

**Impacto**: Vendedores no pueden ver solo productos disponibles en su tienda.

**Solución**:
```python
@router.get("")
def list_products(
    location_id: Optional[int] = None,
    ...
):
    if location_id:
        query = query.join(Stock).filter(
            Stock.location_id == location_id,
            Stock.cantidad_disponible > 0
        )
```

---

### 27. **REPORTES NO INCLUYEN DIMENSIÓN DE UBICACIÓN**

**Problema**: Todos los reportes son globales, no por tienda.

**Evidencia**: Revisar `backend/app/routers/reports.py` (no inspeccionado en detalle).

**Endpoints que probablemente faltan**:
- `GET /api/reports/sales-by-location`
- `GET /api/reports/inventory-by-location`
- `GET /api/reports/top-products-by-location`
- `GET /api/reports/location-performance`

**Impacto**: No se puede evaluar desempeño por tienda.

---

### 28. **FRONTEND LOCAL MODE NO SOPORTA LOCATIONS NI SALES_PROFILES**

**Problema**: El servicio local solo maneja Profile, Product, Order legacy.

**Evidencia**:
```typescript
// inventoryService.ts
const STORAGE_KEYS = {
  PROFILES: 'inventory-profiles',
  PRODUCTS: 'inventory-products',
  STOCK: 'inventory-stock',
  ORDERS: 'inventory-orders',
  ORDER_ITEMS: 'inventory-order-items'
  // ❌ NO HAY:
  // LOCATIONS: 'inventory-locations',
  // SALES_PROFILES: 'inventory-sales-profiles'
}
```

**Impacto**: Modo local completamente roto para V2.0.

**Solución**: Implementar métodos para gestionar locations y sales_profiles en modo local.

---

### 29. **FALTA VALIDACIÓN: CANTIDAD EN TRANSFERENCIAS DEBE SER > 0**

**Problema**: El schema valida pero el modelo no tiene constraint.

**Evidencia**:
```python
# schemas.py
cantidad: int = Field(..., gt=0)  # ✅ Schema valida

# PERO si alguien accede directo a DB:
transfer = StockTransfer(cantidad=-5)  # ❌ Permitido
```

**Impacto**: Datos corruptos si se accede directamente a BD.

**Solución**: Agregar CHECK constraint en modelo.

---

### 30. **PRODUCTOS PUEDEN CREARSE SIN SKU ÚNICO VALIDADO**

**Problema**: El modelo tiene `unique=True` pero no se valida en el router antes de insert.

**Evidencia**:
```python
# models.py
sku = Column(String, unique=True, nullable=False)

# products.py - Sí valida ✅
existing = db.query(Product).filter(Product.sku == product.sku).first()
if existing:
    raise HTTPException(400, "SKU ya existe")
```

**Estado**: ✅ Este SÍ está bien implementado, pero es importante mencionarlo como patrón a seguir.

---

## 📊 RESUMEN DE IMPACTO

### Por Severidad:

**CRÍTICOS (Bloquean funcionalidad)**:
- #16: Falta endpoint stock por ubicación ✅ CORREGIDO
- #18: No se registra en StockHistory al vender
- #19: location_id puede ser NULL en órdenes
- #24: source_location_id opcional en V2.0
- #28: Frontend local mode no soporta V2.0

**GRAVES (Causan inconsistencias)**:
- #17: Paginación inconsistente ✅ CORREGIDO
- #20: profile_id con CASCADE delete
- #22: Falta validación slug en SalesProfile
- #23: Supplier.profile_id contradicción
- #25: IMEIs sin location_id

**IMPORTANTES (Afectan UX/mantenimiento)**:
- #21: API_URL hardcodeado
- #26: Falta filtro por ubicación en productos
- #27: Reportes sin dimensión de ubicación
- #29: Falta validación cantidad > 0

---

## 🎯 ACCIONES INMEDIATAS RECOMENDADAS

1. **Implementar registro en StockHistory** (#18) - CRÍTICO para auditoría
2. **Hacer source_location_id obligatorio** (#24) - Completa V2.0
3. **Cambiar profile_id a SET NULL** (#20) - Evita pérdida de datos
4. **Centralizar API_URL** (#21) - Mantenibilidad
5. **Implementar V2.0 en local mode** (#28) - Dual mode completo

---

**Total errores adicionales encontrados**: 15  
**Corregidos durante esta sesión**: 2  
**Pendientes**: 13

