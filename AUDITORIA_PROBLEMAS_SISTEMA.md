# 🔍 AUDITORÍA COMPLETA DEL SISTEMA - PROBLEMAS CRÍTICOS Y MEJORAS

**Fecha**: 8 de Diciembre, 2025  
**Sistema**: Inventario Multi-Ubicación V2.0  
**Estado**: En transición V1.0 → V2.0 (INCOMPLETA)

---

## 🚨 PROBLEMAS CRÍTICOS (Bloquean funcionalidad V2.0)

### 1. **INCONSISTENCIA TOTAL EN GESTIÓN DE STOCK POR UBICACIÓN**

**Problema**: El sistema V2.0 está diseñado para manejar stock por ubicación física, pero la implementación es incompleta y contradictoria.

#### Evidencias:

**Backend - Modelo de Stock (V2.0)**:
```python
class Stock(Base):
    product_id = Column(Integer, ForeignKey("products.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))  # ✅ Campo existe
    cantidad_disponible = Column(Integer)
    # Constraint: Un producto solo puede tener UN registro por ubicación
    Index('idx_stock_product_location', 'product_id', 'location_id', unique=True)
```

**Backend - init_db.py (V1.0 OBSOLETO)**:
```python
# ❌ PROBLEMA: Stock creado SIN location_id
stock = Stock(
    product_id=product.id,
    cantidad_disponible=stock_qty  # ← NO asigna location_id
)
```

**Backend - Orders Router (INCONSISTENTE)**:
```python
# Línea 318-332: Maneja AMBOS casos sin claridad
if order.source_location_id:
    # V2.0: Busca en ubicación específica
    stock = Stock.filter(location_id == order.source_location_id)
else:
    # V1 Legacy: Busca stock SIN ubicación (¿?)
    stock = Stock.filter(location_id.is_(None))
```

**Frontend - Products Router**:
```python
# ❌ PROBLEMA: NO filtra por ubicación al listar productos
query = db.query(Product).join(Stock)  # ← JOIN sin condición de ubicación
# Resultado: Muestra stock TOTAL sin desglose por tienda
```

#### Impacto en el Negocio:

1. **Imposible saber stock por tienda**: Un producto puede tener 10 unidades totales, pero ¿cuántas en Tienda 1 vs Bodega?
2. **Ventas incorrectas**: Al crear una orden, el sistema NO verifica si hay stock en la ubicación seleccionada de forma confiable
3. **Datos corruptos**: Stock con `location_id = NULL` mezclado con stock V2.0
4. **Transferencias inútiles**: No se puede transferir stock entre ubicaciones si no está asignado correctamente

---

### 2. **PRODUCT.PROFILE_ID OBSOLETO PERO OBLIGATORIO**

**Problema**: El campo `profile_id` en `Product` está marcado como "temporal" pero es `nullable=True` en el modelo y **obligatorio** en los schemas.

#### Evidencias:

**Backend - models.py**:
```python
class Product(Base):
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)  # ✅ Permite NULL
    # Comentario: "Temporal - será eliminado"
```

**Backend - schemas.py**:
```python
class ProductBase(BaseModel):
    profile_id: int  # ❌ OBLIGATORIO (no Optional)
```

**Backend - products.py router**:
```python
@router.post("")
def create_product(product: ProductCreate, db: Session):
    # ❌ Valida que profile_id exista SIEMPRE
    profile = db.query(Profile).filter(Profile.id == product.profile_id).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")
```

#### Impacto en el Negocio:

1. **Contradicción conceptual**: V2.0 dice "productos globales" pero requieren un perfil (segmento de negocio)
2. **Frontend confundido**: `NewProductDialog` necesita seleccionar un "perfil" que conceptualmente no debería existir
3. **Migración imposible**: No se puede eliminar `Profile` sin romper toda la creación de productos
4. **Arquitectura inconsistente**: `SalesProfile` (bots/vendedores) vs `Profile` (¿negocio?)

---

### 3. **TRANSFERENCIAS DE STOCK ENTRE PERFILES EN VEZ DE UBICACIONES**

**Problema**: El sistema V2.0 de transferencias usa `from_profile_id` y `to_profile_id` en lugar de `from_location_id` y `to_location_id`.

#### Evidencias:

**Backend - models.py**:
```python
class StockTransfer(Base):
    from_location_id = Column(Integer, ForeignKey("locations.id"))  # ✅ Existe
    to_location_id = Column(Integer, ForeignKey("locations.id"))    # ✅ Existe
    # PERO TAMBIÉN:
    from_profile_id = Column(Integer, ForeignKey("profiles.id"))    # ❌ Legacy
    to_profile_id = Column(Integer, ForeignKey("profiles.id"))      # ❌ Legacy
```

**Backend - stock_transfers.py router**:
```python
class StockTransferCreate(BaseModel):
    from_profile_slug: str  # ❌ USA PERFILES, NO UBICACIONES
    to_profile_slug: str
    # NO tiene from_location_id / to_location_id
```

**Endpoint POST /api/stock-transfers**:
```python
# Busca perfiles antiguos (V1)
from_profile = db.query(Profile).filter(slug == transfer.from_profile_slug)
to_profile = db.query(Profile).filter(slug == transfer.to_profile_slug)
# ❌ NO usa Location en absoluto
```

#### Impacto en el Negocio:

1. **Transferencias no funcionales**: No se puede transferir de "Tienda 1" a "Bodega Central"
2. **Confusión total**: ¿Transferir entre perfiles (Softmobile → TechStore) o entre tiendas?
3. **Endpoint V2.0 inexistente**: No hay forma de hacer transferencias físicas reales
4. **Frontend desactualizado**: `StockByLocationDialog` probablemente roto

---

### 4. **FRONTEND NO IMPLEMENTA STOCK POR UBICACIÓN**

**Problema**: El frontend sigue usando la lógica V1.0 de stock global por producto.

#### Evidencias:

**Frontend - inventoryService.ts (Local Mode)**:
```typescript
async createOrder(request: CreateOrderRequest) {
    // ❌ Valida stock total, NO por ubicación
    const stockEntry = stock.find(s => s.product_id === item.product_id)
    if (stockEntry.cantidad_disponible < item.cantidad) {
        throw new Error("Insufficient stock")
    }
    // NO verifica source_location_id
}
```

**Frontend - apiClient.ts**:
```typescript
async fetchProducts() {
    // ❌ NO pasa location_id como filtro
    const response = await fetch('/products?per_page=100')
    // Retorna stock_disponible total, no desglosado
}
```

**Frontend - types.ts**:
```typescript
export interface Product {
    stock_disponible?: number  // ❌ Campo único, no array
    stock_items?: StockByLocation[]  // ✅ Existe pero NO se usa
}
```

#### Impacto en el Negocio:

1. **Modo local roto**: No soporta V2.0 en absoluto
2. **Validaciones incorrectas**: Permite vender stock que no existe en la ubicación seleccionada
3. **UI engañosa**: Muestra stock total sin indicar distribución por tienda
4. **Desconexión backend-frontend**: El backend soporta (parcialmente) V2.0, el frontend no

---

## ⚠️ PROBLEMAS GRAVES (Afectan consistencia y confiabilidad)

### 5. **DOBLE GESTIÓN DE IMEIS INCONSISTENTE**

**Problema**: Los productos tienen TRES formas de almacenar IMEIs.

#### Evidencias:

**Backend - models.py**:
```python
class Product(Base):
    # NO tiene campo imei directo (eliminado)
    imeis = relationship("ProductIMEI")  # ✅ Tabla separada

class ProductIMEI(Base):
    product_id = Column(Integer)
    location_id = Column(Integer)  # ✅ IMEI asociado a ubicación
    imei = Column(String, unique=True)
    vendido = Column(Boolean)
```

**Backend - schemas.py**:
```python
class ProductBase(BaseModel):
    imei: Optional[str] = None  # ❌ Campo DEPRECATED pero permitido
    imeis: Optional[List[str]] = None  # ✅ Correcto
```

**Frontend - types.ts**:
```typescript
export interface Product {
    imei?: string  // ❌ DEPRECATED según comentario
    imeis?: string[]  // ✅ Correcto
}
```

**Backend - products.py**:
```python
# Al crear producto:
product_data.pop("imei", None)  # ❌ Elimina pero acepta en schema
if imeis:
    for imei_value in imeis:
        db_imei = ProductIMEI(product_id=db_product.id, imei=imei_value)
        # ❌ NO asigna location_id al crear
```

#### Impacto en el Negocio:

1. **IMEIs sin ubicación**: No se sabe en qué tienda está físicamente cada celular
2. **Validación duplicada**: Acepta `imei` en input pero lo ignora
3. **Frontend desincronizado**: Puede enviar `imei` único o `imeis` array
4. **Reclamos imposibles**: Si un celular tiene garantía, ¿dónde está físicamente?

---

### 6. **SALES_PROFILE VS PROFILE: CONFUSIÓN ARQUITECTÓNICA**

**Problema**: El sistema mantiene DOS conceptos de "perfil" que se solapan.

#### Evidencias:

**Documentación NUEVO_SISTEMA_UBICACIONES.md**:
```markdown
- Profile = DEPRECATED (negocio: Softmobile, TechStore)
- SalesProfile = Actual (bot_ia, vendedor_humano)
```

**Backend - models.py**:
```python
class Profile(Base):
    # "Mantener por compatibilidad (alias temporal)"
    products = relationship("Product")  # ❌ Productos SIGUEN atados a Profile
    
class SalesProfile(Base):
    # "Perfil de venta (vendedor, bot de IA)"
    orders = relationship("Order")  # ✅ Órdenes usan SalesProfile
```

**Backend - orders.py**:
```python
# Acepta AMBOS:
if order.sales_profile_slug:
    sales_profile = db.query(SalesProfile).filter(...)
else:
    profile = db.query(Profile).filter(...)  # ❌ Legacy fallback
```

**Frontend - App.tsx**:
```typescript
const [profiles, setProfiles] = useKV<Profile[]>('inventory-profiles', [])
// ❌ SIGUE usando Profile antiguo, NO SalesProfile
```

#### Impacto en el Negocio:

1. **Migración bloqueada**: No se puede eliminar `Profile` sin reescribir todo
2. **APIs duplicadas**: `/profiles` vs `/sales-profiles` con propósitos difusos
3. **Frontend en V1**: Usa `profiles` legacy en lugar de `sales_profiles`
4. **Órdenes híbridas**: Algunas con `profile_id`, otras con `sales_profile_id`

---

### 7. **VALIDACIÓN DE STOCK EN ÓRDENES NO ATÓMICA**

**Problema**: La creación de órdenes NO usa transacciones de forma consistente, puede haber race conditions.

#### Evidencias:

**Backend - orders.py línea 323-355**:
```python
# Validación FUERA de transacción explícita
for item in order.items:
    stock = db.query(Stock).filter(...)
    if stock.cantidad_disponible < item.cantidad:
        raise HTTPException(400, "Stock insuficiente")

# Descuento EN BUCLE (no atómico)
for item_data in order_items_data:
    item_data["stock"].cantidad_disponible -= item_data["cantidad"]

db.commit()  # ← Una sola commit, PERO sin isolation level explícito
```

**Problema potencial**:
- Request 1 valida stock: 5 unidades ✅
- Request 2 valida stock: 5 unidades ✅ (simultáneo)
- Request 1 descuenta: stock = 2 ✅
- Request 2 descuenta: stock = -3 ❌ (STOCK NEGATIVO)

#### Impacto en el Negocio:

1. **Sobreventa posible**: Dos bots vendiendo al mismo tiempo pueden agotar stock
2. **Stock negativo**: No hay constraint `CHECK cantidad_disponible >= 0`
3. **Pérdida de dinero**: Se vende lo que no existe físicamente

---

### 8. **PROVEEDORES ATADOS A PROFILE OBSOLETO**

**Problema**: Los proveedores (`Supplier`) están vinculados a `Profile` en lugar de ser globales.

#### Evidencias:

**Backend - models.py**:
```python
class Supplier(Base):
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    # ❌ Un proveedor solo puede pertenecer a UN negocio
```

**Backend - schemas.py**:
```python
class SupplierCreate(BaseModel):
    profile_id: Optional[int] = None  # V2.0: Deprecated, proveedores son globales
```

**Contradicción**:
- Schema dice "Deprecated"
- Modelo lo requiere (`nullable=False`)

#### Impacto en el Negocio:

1. **Proveedores duplicados**: "Samsung Guatemala" debe crearse en cada Profile
2. **Reclamos fragmentados**: Garantías no centralizadas
3. **Reportes imposibles**: No se puede ver "todos los productos de Samsung"

---

## 📊 PROBLEMAS DE LÓGICA DE NEGOCIO

### 9. **STOCK_HISTORY SIN CONTEXT ADECUADO**

**Problema**: El historial de stock registra cambios pero sin contexto completo.

#### Evidencias:

**Backend - models.py**:
```python
class StockHistory(Base):
    location_id = Column(Integer, nullable=True)  # ✅ Opcional
    referencia_id = Column(Integer, nullable=True)  # ID de orden/transferencia
    referencia_tipo = Column(String, nullable=True)  # 'order', 'transfer'
    usuario = Column(String, nullable=True)  # ❌ String libre, no FK a User
```

**Backend - NO HAY TRIGGERS**:
- No se registra automáticamente en el historial al crear órdenes
- No se registra en transferencias de stock
- Depende de que cada router lo haga manualmente

#### Impacto en el Negocio:

1. **Auditoría incompleta**: No se registran TODOS los movimientos
2. **Trazabilidad rota**: ¿Quién movió 50 unidades ayer?
3. **Reportes inexactos**: No se puede reconstruir inventario histórico

---

### 10. **FRONTEND NO SINCRONIZA LOCATIONS Y SALES_PROFILES**

**Problema**: El frontend usa KV local pero no sincroniza entidades V2.0.

#### Evidencias:

**Frontend - inventoryService.ts**:
```typescript
const STORAGE_KEYS = {
  PROFILES: 'inventory-profiles',  // ✅ Profile V1
  PRODUCTS: 'inventory-products',
  ORDERS: 'inventory-orders'
  // ❌ NO HAY: LOCATIONS, SALES_PROFILES
}
```

**Frontend - App.tsx**:
```typescript
const [profiles, setProfiles] = useKV<Profile[]>('inventory-profiles', [])
// ❌ NO EXISTE:
// const [locations, setLocations] = useKV<Location[]>(...)
// const [salesProfiles, setSalesProfiles] = useKV<SalesProfile[]>(...)
```

#### Impacto en el Negocio:

1. **Modo local no funciona**: Solo API mode soporta V2.0
2. **Datos perdidos al cambiar**: Locations/SalesProfiles no persisten en KV
3. **Testing imposible**: No se puede probar sin backend

---

### 11. **FILTROS DE PRODUCTOS IGNORAN UBICACIÓN**

**Problema**: Al listar productos, no se puede filtrar por ubicación o ver stock desglosado.

#### Evidencias:

**Backend - products.py**:
```python
@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products(
    search: Optional[str] = None,
    include_inactive: bool = False
    # ❌ NO HAY: location_id parameter
):
    query = db.query(Product).join(Stock)
    # ❌ NO filtra por Stock.location_id
```

**Frontend - ProductCard.tsx**:
```tsx
// Muestra:
<Badge>Stock: {product.stock_disponible}</Badge>
// ❌ NO muestra desglose:
// Tienda 1: 5, Tienda 2: 3, Bodega: 10
```

#### Impacto en el Negocio:

1. **Vendedores ciegos**: No saben si un producto está en su tienda
2. **Promesas falsas**: Venden algo que está en otra ciudad
3. **UX pobre**: Clientes frustrados al cambiar de ubicación

---

### 12. **REPORTES Y ANALÍTICA EN V1.0**

**Problema**: Todos los reportes ignoran la dimensión de ubicación.

#### Evidencias:

**Backend - reports.py** (NO revisado en detalle, pero basado en estructura):
```python
# Probablemente:
@router.get("/sales-by-profile")
# ❌ NO HAY: /sales-by-location
```

**Frontend - ReportsDialog.tsx**:
```typescript
// Muestra:
// - Revenue total
// - Top products
// ❌ NO muestra:
// - Revenue por tienda
// - Productos más vendidos por ubicación
```

#### Impacto en el Negocio:

1. **Decisiones ciegas**: No se sabe qué tienda es más rentable
2. **Inventario desbalanceado**: No se reabastece según demanda local
3. **KPIs inútiles**: Métricas globales sin contexto geográfico

---

## 🔧 PROBLEMAS DE ARQUITECTURA

### 13. **MIGRACIÓN V1→V2 INCOMPLETA**

**Problema**: El script de migración existe pero no se ejecuta automáticamente.

#### Evidencias:

**Backend - migrate_to_locations_model.py**:
```python
# Script MANUAL que convierte:
# - Profile → Location (tiendas)
# - Stock → Stock con location_id
```

**Backend - init_db.py**:
```python
# ❌ NO ejecuta migración automáticamente
# ❌ Crea stock SIN location_id (V1.0)
```

**Guías**:
- `INICIO_RAPIDO.md` dice "Ejecuta migrate_to_locations_model.py"
- Pero `test-system.sh` NO lo ejecuta
- `start-backend.sh` NO lo verifica

#### Impacto en el Negocio:

1. **Bases de datos inconsistentes**: Desarrolladores olvidan migrar
2. **Testing con datos V1**: Pruebas no reflejan realidad V2.0
3. **Producción en riesgo**: Deploy puede fallar si no hay migración

---

### 14. **DUAL MODE ROTO PARA V2.0**

**Problema**: El patrón "dual mode" (KV local vs API) solo funciona para V1.0.

#### Evidencias:

**Frontend - inventoryServiceFactory.ts**:
```typescript
export interface IInventoryService {
    createOrder(request: CreateOrderRequest): Promise<OrderWithItems>
    // ✅ Firma genérica
    
    // ❌ NO HAY:
    // listLocations(): Promise<Location[]>
    // listSalesProfiles(): Promise<SalesProfile[]>
    // getStockByLocation(productId, locationId): Promise<number>
}
```

**Frontend - inventoryService.ts** (local):
```typescript
// ❌ NO implementa nada de V2.0
```

#### Impacto en el Negocio:

1. **Local mode obsoleto**: Solo sirve para demos V1.0
2. **Desarrollo bloqueado**: No se puede trabajar offline en V2.0
3. **Arquitectura quebrada**: Promesa de "dual mode" es falsa

---

### 15. **PAGINACIÓN INCONSISTENTE**

**Problema**: Algunos endpoints soportan paginación, otros no.

#### Evidencias:

**Backend - locations.py**:
```python
@router.get("", response_model=List[LocationResponse])
# ❌ NO usa PaginatedResponse
```

**Backend - products.py**:
```python
@router.get("", response_model=PaginatedResponse[ProductResponse])
# ✅ Sí usa paginación
```

**Frontend - apiClient.ts**:
```typescript
async fetchProducts() {
    const response = await this.request<{ items: ProductWithStock[]; total: number }>
    return response.items  // ✅ Maneja paginación
}

async listLocations() {
    // ❌ Probablemente espera array directo
}
```

#### Impacto en el Negocio:

1. **Performance variable**: Algunos endpoints escalan, otros no
2. **Frontend frágil**: Código diferente para cada recurso
3. **UX inconsistente**: Algunas listas tienen paginación, otras no

---

## 📝 RECOMENDACIONES PRIORITARIAS

### CRÍTICAS (Hacer AHORA):

1. **✅ UNIFICAR GESTIÓN DE STOCK POR UBICACIÓN**
   - Eliminar stock con `location_id = NULL`
   - Crear migración obligatoria en `init_db.py`
   - Actualizar frontend para mostrar stock por tienda

2. **✅ ELIMINAR PRODUCT.PROFILE_ID**
   - Hacer `profile_id` truly opcional
   - Actualizar schemas para no requerirlo
   - Productos son globales, punto.

3. **✅ ARREGLAR TRANSFERENCIAS DE STOCK**
   - Usar `from_location_id`/`to_location_id` exclusivamente
   - Eliminar `from_profile_id`/`to_profile_id` de schemas
   - Crear endpoint correcto en frontend

4. **✅ IMPLEMENTAR V2.0 EN FRONTEND LOCAL MODE**
   - Agregar `locations` y `salesProfiles` a KV storage
   - Actualizar `inventoryService.ts` con lógica de ubicaciones
   - Sincronizar `inventoryServiceFactory` interface

### IMPORTANTES (Hacer PRONTO):

5. **Agregar constraint de stock no negativo**
6. **Hacer proveedores globales (eliminar profile_id)**
7. **Auto-registrar en StockHistory con triggers o eventos**
8. **Estandarizar paginación en todos los endpoints**

### MEJORAS (Hacer DESPUÉS):

9. Reportes por ubicación
10. Dashboard con KPIs por tienda
11. Alertas de stock bajo por ubicación
12. Transferencias automáticas entre tiendas

---

## 🎯 PLAN DE ACCIÓN SUGERIDO

### Fase 1: Estabilizar V2.0 Core (1 semana)
- [ ] Problema 1: Stock por ubicación obligatorio
- [ ] Problema 2: Product.profile_id opcional
- [ ] Problema 3: Transferencias con ubicaciones
- [ ] Problema 7: Transacciones atómicas + constraint

### Fase 2: Frontend V2.0 (1 semana)
- [ ] Problema 4: Implementar stock por ubicación en local mode
- [ ] Problema 10: Sincronizar Locations/SalesProfiles en KV
- [ ] Problema 11: Filtros y UI por ubicación
- [ ] Problema 14: Dual mode completo

### Fase 3: Limpieza y Optimización (1 semana)
- [ ] Problema 6: Deprecar Profile completamente
- [ ] Problema 8: Proveedores globales
- [ ] Problema 9: StockHistory automático
- [ ] Problema 15: Paginación consistente

### Fase 4: Reportes y Analítica (1 semana)
- [ ] Problema 12: Reportes por ubicación
- [ ] Dashboard multi-tienda
- [ ] KPIs por canal de venta
- [ ] Optimización de inventario por tienda

---

**TOTAL ESTIMADO**: 4 semanas para sistema V2.0 completamente funcional y consistente.

