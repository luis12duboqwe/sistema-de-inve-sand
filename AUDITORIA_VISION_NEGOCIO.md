# 🔍 AUDITORÍA COMPLETA - PROBLEMAS DETECTADOS

**Fecha:** 8 de diciembre de 2025  
**Perspectiva:** Dueño del negocio revisando si el sistema cumple su visión

---

## 🔴 PROBLEMA #1: NewProductDialog Pide "Perfil" ❌

### Ubicación
`src/components/NewProductDialog.tsx` - Línea 307-322

### Código Problemático
```tsx
<div className="space-y-2">
  <Label htmlFor="profile">Perfil *</Label>
  <Select value={profileId.toString()} onValueChange={(v) => setProfileId(parseInt(v))}>
    <SelectTrigger id="profile">
      <SelectValue placeholder="Seleccionar perfil" />
    </SelectTrigger>
    <SelectContent>
      {profiles.map(profile => (
        <SelectItem key={profile.id} value={profile.id.toString()}>
          {profile.name}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>
```

### ❌ Por Qué Está Mal
**Como dueño del negocio:**
- Tengo UN solo negocio
- Los productos son GLOBALES
- ¿Por qué me piden elegir un "perfil" al crear un producto?
- **NO tiene sentido** - confunde con "Canales de Venta"

### ✅ Solución
Eliminar el selector de "Perfil" completamente:
1. Los productos NO pertenecen a un "perfil de negocio"
2. Los productos son del inventario global
3. Stock se gestiona por UBICACIÓN, no por perfil

---

## 🔴 PROBLEMA #2: NewOrderDialog - Selector V1.0 ❌

### Ubicación
`src/components/NewOrderDialog.tsx` - Línea 42

### Código Problemático
```tsx
const [profileSlug, setProfileSlug] = useState('')  // ❌ V1.0 legacy
const [salesProfileSlug, setSalesProfileSlug] = useState('') // ✅ V2.0
```

### ❌ Por Qué Está Mal
**Como dueño del negocio:**
- Hay DOS variables para "perfil" en el mismo componente
- `profileSlug` es V1.0 (perfil de negocio) - **NO lo necesito**
- `salesProfileSlug` es V2.0 (canal de venta) - **SÍ lo necesito**
- Esto causa confusión en el código

### Revisando Más...
```tsx
const availableProducts = products.filter(p => 
  !profileSlug || profiles.find(pr => pr.slug === profileSlug)?.id === p.profile_id
)
```

**¡Problema!** Está filtrando productos por `profileSlug` (V1.0)
- En mi visión, **NO debería filtrar productos**
- Todos los productos están disponibles para todos los canales de venta

### ✅ Solución
1. Eliminar `profileSlug` completamente
2. Eliminar filtro de productos por profile
3. Mostrar TODOS los productos disponibles
4. Solo usar `salesProfileSlug` y `sourceLocationId`

---

## 🔴 PROBLEMA #3: Toggle "useV2" en NewOrderDialog ❌

### Ubicación
`src/components/NewOrderDialog.tsx` - Línea 56

### Código Problemático
```tsx
const [useV2, setUseV2] = useState(true) // Toggle para usar V2.0
```

### ❌ Por Qué Está Mal
**Como dueño del negocio:**
- ¿Por qué hay un "toggle" entre V1.0 y V2.0?
- Yo **SOLO quiero V2.0**
- No necesito compatibilidad con V1.0
- Este toggle confunde y permite crear órdenes mal

### ✅ Solución
1. Eliminar el toggle `useV2`
2. **SIEMPRE** usar V2.0
3. Los campos V2.0 (`salesProfileSlug`, `sourceLocationId`) deben ser **obligatorios**
4. No mostrar opción de "modo legacy"

---

## 🔴 PROBLEMA #4: Proveedores por "Perfil" ❌

### Ubicación
`src/components/NewProductDialog.tsx` - Línea 113-130

### Código Problemático
```tsx
useEffect(() => {
  const loadSuppliers = async () => {
    if (profileId && open) {
      try {
        const response = await apiClient.request('/suppliers', {
          params: { profile_id: profileId, include_inactive: false }
        })
        // ...
      }
    }
  }
  loadSuppliers()
}, [profileId, open])
```

### ❌ Por Qué Está Mal
**Como dueño del negocio:**
- Los proveedores deberían ser GLOBALES
- No pertenecen a un "perfil de negocio"
- Compro inventario para TODO el negocio, no para perfiles separados

### ✅ Solución
1. Proveedores globales (sin profile_id)
2. Un solo catálogo de proveedores
3. Productos pueden tener proveedor asignado (trazabilidad)

---

## 🔴 PROBLEMA #5: Stock Inicial en NewProductDialog ❌

### Ubicación
`src/components/NewProductDialog.tsx`

### ❌ Por Qué Está Mal
**Como dueño del negocio:**
- Al crear un producto, me pide "Stock Inicial" (un número)
- Pero en V2.0, el stock debería ser **POR UBICACIÓN**
- ¿En cuál ubicación estoy poniendo ese stock inicial?

### Ejemplo del Problema
```
Creo producto: iPhone 15 Pro
Stock Inicial: 10 unidades
¿Dónde están esas 10 unidades?
  - ¿En la bodega?
  - ¿En Tienda Centro?
  - ¿Distribuidas?
```

### ✅ Solución Correcta
Al crear un producto nuevo:

**Opción A (Recomendada):**
```
1. Crear producto SIN stock
2. Después, ir a "Stock por Ubicación"
3. Asignar stock a cada ubicación
```

**Opción B (Más compleja pero mejor UX):**
```
Al crear producto, mostrar:
┌─────────────────────────────┐
│ Distribuir Stock Inicial    │
├─────────────────────────────┤
│ Bodega Principal:    [10]   │
│ Tienda Centro:       [5]    │
│ Tienda Mall:         [3]    │
│ Tienda Aeropuerto:   [2]    │
│                             │
│ Total: 20 unidades          │
└─────────────────────────────┘
```

---

## 🟡 PROBLEMA #6: Moneda por "Perfil" ⚠️

### Ubicación
`src/components/NewProductDialog.tsx` - Línea 109-110

### Código Cuestionable
```tsx
const selectedProfile = profiles.find(p => p.id === profileId)
const currency = selectedProfile?.settings?.currency || 'HNL'
```

### ⚠️ Por Qué Podría Ser Problema
**Como dueño del negocio:**
- ¿Debería tener múltiples monedas?
- Probablemente NO - mi negocio opera en Honduras (HNL)
- Si vendo en dólares, es una conversión, no un "perfil diferente"

### ✅ Solución
1. Moneda global: HNL (o configuración del negocio)
2. Si necesitas multi-moneda, que sea en Configuración Global
3. No por "perfil de negocio"

---

## 🔴 PROBLEMA #7: Filtro de Productos por Profile en App.tsx

### Ya Corregido Pero Revisar Backend

Eliminamos el selector de UI, pero el backend todavía:
- Tiene `profile_id` en tabla `products`
- Los queries pueden estar filtrando por profile_id

### ✅ Verificar
```python
# backend/app/routers/products.py
# ¿Los endpoints filtran por profile_id?
# Deberían devolver TODOS los productos (globales)
```

---

## 🎯 RESUMEN DE PROBLEMAS

### CRÍTICOS (Arreglar YA):
1. ❌ **NewProductDialog:** Eliminar selector de "Perfil"
2. ❌ **NewOrderDialog:** Eliminar `profileSlug` y filtro V1.0
3. ❌ **NewOrderDialog:** Eliminar toggle useV2 (siempre V2.0)
4. ❌ **NewProductDialog:** Stock inicial → Stock por ubicación

### IMPORTANTES (Arreglar Pronto):
5. ⚠️ **Proveedores:** Hacer globales (no por profile)
6. ⚠️ **Moneda:** Configuración global vs por perfil

### VERIFICAR (Backend):
7. 🔍 Queries de productos no deben filtrar por profile_id
8. 🔍 Proveedores no deberían tener profile_id obligatorio

---

## 🎯 VISIÓN CORRECTA DEL SISTEMA

```
┌─────────────────────────────────────────────────┐
│            MI NEGOCIO ÚNICO                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  CONFIGURACIÓN GLOBAL                           │
│  ├─ Moneda: HNL                                 │
│  ├─ Nombre del negocio                          │
│  └─ Datos fiscales                              │
│                                                 │
│  PROVEEDORES (Globales)                         │
│  ├─ Proveedor A                                 │
│  ├─ Proveedor B                                 │
│  └─ Proveedor C                                 │
│                                                 │
│  PRODUCTOS (Globales)                           │
│  ├─ iPhone 15 Pro (stock por ubicación)        │
│  ├─ Samsung S24 (stock por ubicación)          │
│  └─ Funda (stock por ubicación)                │
│                                                 │
│  UBICACIONES FÍSICAS                            │
│  ├─ Bodega Principal                            │
│  ├─ Tienda Centro                               │
│  ├─ Tienda Mall                                 │
│  └─ Tienda Aeropuerto                           │
│                                                 │
│  CANALES DE VENTA                               │
│  ├─ Bot WhatsApp 1 → ve TODO                   │
│  ├─ Bot Facebook 1 → ve TODO                   │
│  ├─ Vendedor Juan → ve TODO                    │
│  └─ Sistema Auto → ve TODO                     │
│                                                 │
│  ÓRDENES                                        │
│  Cada orden:                                    │
│    ✅ Canal que vendió (sales_profile_id)      │
│    ✅ Ubicación de origen (source_location_id) │
│    ✅ Cliente                                   │
│    ✅ Productos vendidos                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Concepto clave:** NO hay "múltiples perfiles de negocio", hay UN negocio con múltiples canales de venta

---

## 📝 LISTA DE TAREAS

### Alta Prioridad:
- [ ] Eliminar selector "Perfil" de NewProductDialog
- [ ] Cambiar stock inicial → distribución por ubicación
- [ ] Limpiar NewOrderDialog de código V1.0
- [ ] Hacer obligatorios campos V2.0 en órdenes
- [ ] Eliminar toggle useV2

### Media Prioridad:
- [ ] Proveedores globales (backend + frontend)
- [ ] Revisar queries de productos (no filtrar por profile)
- [ ] Configuración global de moneda

### Baja Prioridad:
- [ ] Migración de datos legacy
- [ ] Eliminar tabla profiles (después de migración)

---

¿Procedo a implementar las correcciones de ALTA PRIORIDAD?
