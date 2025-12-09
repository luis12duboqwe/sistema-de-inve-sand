# 🔍 PROBLEMAS ADICIONALES ENCONTRADOS - Para Siguiente Iteración

**Revisión desde perspectiva del dueño del negocio**  
**Fecha:** 8 de diciembre de 2025

---

## 🎯 CONTEXTO

Durante la corrección de `NewOrderDialog` y `NewProductDialog`, se identificaron **6 problemas adicionales** que no están alineados con tu visión de negocio:

**Tu visión:**
- ✅ **1 negocio** (no múltiples unidades de negocio separadas)
- ✅ **4 ubicaciones físicas:** Bodega Central + Tienda 1, 2, 3
- ✅ **10+ canales de venta:** Bots, vendedores humanos, sistema
- ✅ **Inventario global:** Todos ven los mismos productos
- ✅ **Stock por ubicación:** Cada producto tiene stock en cada tienda/bodega

---

## 🔴 PROBLEMA 1: Backend filtra productos por "perfil" (CRÍTICO)

### ¿Qué pasa ahora?
Cuando el frontend pide productos al backend, **puede filtrarlos por `profile_slug`**:

```python
# backend/app/routers/products.py línea 95-100
if profile_slug:
    query = query.filter(Product.profile_id == profile.id)
```

**Ejemplo del problema:**
- Bot WhatsApp pide productos con `?profile_slug=bot-whatsapp`
- Backend solo devuelve productos que "pertenecen" a ese perfil
- El bot NO VE productos que debería poder vender

### ¿Cómo debería ser?
**TODOS los productos deberían ser visibles para TODOS los canales de venta**, sin importar quién esté vendiendo.

### Impacto:
- 🔴 **ALTO:** Si algún componente pasa `profile_slug`, el inventario se segmenta incorrectamente
- 🔴 Los canales de venta no ven todos los productos disponibles

### Corrección necesaria:
```python
# Eliminar este bloque completamente:
if profile_slug:
    profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
    if not profile:
        raise HTTPException(status_code=404)
    query = query.filter(Product.profile_id == profile.id)  # ❌ ELIMINAR
```

---

## 🟠 PROBLEMA 2: Stock inicial sin distribución por ubicación (IMPORTANTE)

### ¿Qué pasa ahora?
Al crear un producto nuevo, hay un campo **"Stock Inicial"** que es un número único:

```tsx
<Input 
  label="Stock Inicial"
  value={stockInicial}  // Ejemplo: "10"
  onChange={setStockInicial}
/>
```

**El problema:** 
- Creas producto con stock inicial = 10
- ¿Dónde están esos 10 productos? ¿En Bodega? ¿En Tienda 1? ¿Distribuidos?

### ¿Cómo debería ser?
Después de crear el producto, debería haber un paso para distribuir el stock:

```
Producto: iPhone 15 Pro Max
Stock inicial total: 10 unidades

Distribución:
- Bodega Central: 5 unidades
- Tienda 1: 2 unidades  
- Tienda 2: 2 unidades
- Tienda 3: 1 unidad
Total: 10 ✅
```

### Impacto:
- 🟠 **MEDIO:** El stock se crea pero no sabes dónde está físicamente
- 🟠 Probablemente va a una ubicación por defecto (la primera del sistema)

### Corrección necesaria:
**Opción A:** Diálogo después de crear producto
**Opción B:** Sección inline en formulario de creación

---

## 🟠 PROBLEMA 3: Proveedores tienen "dueño" (profile_id) (IMPORTANTE)

### ¿Qué pasa ahora?
En la base de datos, tabla `suppliers` tiene columna `profile_id`:

```sql
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER,  -- ❌ Proveedor "pertenece" a un perfil
    nombre VARCHAR,
    ...
)
```

**El problema:**
- Proveedor "TechDistribuidora" está asociado a "Perfil Tienda 1"
- Cuando Tienda 2 quiere comprar del mismo proveedor, no lo ve

### ¿Cómo debería ser?
Los **proveedores son globales del negocio**. Si tienes un proveedor que te vende celulares, ese proveedor debería estar disponible para registrar compras a cualquier ubicación.

### Impacto:
- 🟠 **MEDIO:** Proveedores duplicados por cada "perfil"
- 🟠 No puedes tener vista consolidada de compras por proveedor

### Corrección necesaria:
1. **Migración:** Eliminar `profile_id` de `suppliers`
2. **Backend:** Actualizar queries de suppliers
3. **Frontend:** Ya está corregido ✅ (carga global)

---

## 🟡 PROBLEMA 4: Moneda hardcoded (MEJORABLE)

### ¿Qué pasa ahora?
La moneda está fija en el código:

```tsx
const currency = 'HNL'  // Hardcoded
```

**Antes estaba así:**
```tsx
const currency = selectedProfile?.settings?.currency || 'HNL'
```

### ¿Cómo debería ser?
Debería haber una **configuración global del sistema**:

```tsx
// Configuración del negocio
{
  "currency": "HNL",
  "timezone": "America/Tegucigalpa", 
  "tax_rate": 0.15,
  "business_name": "Mi Tienda de Celulares"
}
```

### Impacto:
- 🟡 **BAJO:** Funciona bien si solo operas en Honduras
- 🟡 Si quieres cambiar moneda, tienes que modificar código

### Corrección necesaria:
- Crear tabla `system_config` o archivo de configuración
- Hook `useSystemConfig()` en frontend

---

## 🟡 PROBLEMA 5: Campos legacy profile_id en creación (MEJORABLE)

### ¿Qué pasa ahora?
Al crear productos y órdenes, todavía se envía `profile_id` al backend:

```tsx
// NewProductDialog
profile_id: profiles[0]?.id || 1  // "Usa el primer perfil"

// NewOrderDialog  
profile_slug: profiles[0]?.slug || ''  // "Usa el primer slug"
```

**El problema:** Es código de compatibilidad que no debería existir en V2.0.

### ¿Cómo debería ser?
- Productos sin `profile_id` (son globales)
- Órdenes sin `profile_slug` (solo `sales_profile_slug` que es el canal de venta)

### Impacto:
- 🟡 **BAJO:** Funciona, pero es "deuda técnica"
- 🟡 Confunde al leer el código (¿por qué productos tienen perfil?)

### Corrección necesaria:
1. Backend: Hacer `profile_id` opcional en productos
2. Backend: Deprecar `profile_slug` en órdenes
3. Eventualmente: Eliminar columnas de la base de datos

---

## 🟢 PROBLEMA 6: Tabla Profile (V1.0) todavía existe (OBSERVACIÓN)

### ¿Qué pasa ahora?
La tabla `profiles` (de V1.0) todavía existe en la base de datos, aunque ya no se usa en el frontend.

**V1.0 (antes):** `profiles` = unidades de negocio separadas  
**V2.0 (ahora):** `locations` = ubicaciones físicas, `sales_profiles` = canales de venta

### ¿Cómo debería ser?
Eventualmente eliminar completamente:
- ✅ Tabla `profiles`
- ✅ Columnas `products.profile_id`
- ✅ Columnas `suppliers.profile_id`
- ✅ Props `profiles: Profile[]` del frontend

### Impacto:
- 🟢 **NINGUNO por ahora:** Todo funciona
- 🟢 Es limpieza técnica para el futuro

---

## 📊 RESUMEN VISUAL

```
PRIORIDADES PARA SIGUIENTE ITERACIÓN:

🔴 CRÍTICO (hacer primero):
└─ 1. Backend filtro de productos por profile_slug
   └─ Tiempo: 30 min
   └─ Impacto: ALTO - Afecta visibilidad de inventario

🟠 IMPORTANTE (hacer después):
├─ 2. Stock inicial sin distribución
│  └─ Tiempo: 2-3 horas  
│  └─ Impacto: MEDIO - UX mejorada
└─ 3. Proveedores con profile_id
   └─ Tiempo: 1-2 horas (incluye migración)
   └─ Impacto: MEDIO - Gestión de proveedores

🟡 MEJORABLE (cuando haya tiempo):
├─ 4. Moneda hardcoded → Config global
├─ 5. Campos legacy profile_id
└─ 6. Limpieza tabla Profile V1.0
```

---

## ✅ LO QUE YA SE CORRIGIÓ HOY

1. ✅ `NewOrderDialog` - Eliminado código V1.0, solo V2.0
2. ✅ `NewProductDialog` - Productos globales sin perfil
3. ✅ Filtro de productos eliminado en frontend
4. ✅ Suppliers cargados globalmente en frontend
5. ✅ UI limpia sin selectores de "perfil" innecesarios

---

## 🎯 RECOMENDACIÓN

**Para la siguiente sesión, empezar con:**

### 1️⃣ Corregir backend GET /products (15-30 min)
```python
# Eliminar filtro por profile_slug
# Hacer que todos los productos sean visibles globalmente
```

### 2️⃣ Testing completo (30 min)
```bash
# Crear producto
# Crear orden desde diferentes canales
# Verificar que todos ven el mismo inventario
```

### 3️⃣ Migración de suppliers (1-2 horas)
```python
# Eliminar profile_id de tabla suppliers
# Hacer proveedores globales
```

**Total tiempo estimado:** 2-3 horas para resolver todos los problemas críticos/importantes.

---

**¿Alguna pregunta sobre estos problemas antes de continuar?**
