# Problemas V1.0 Adicionales Encontrados

## Fecha: 8 de diciembre 2025

---

## ❌ PROBLEMA 1: LowStockAlert - Filtra productos por profile_id

**Archivo**: `/src/components/LowStockAlert.tsx` línea 30

**Código V1.0 (INCORRECTO)**:
```tsx
const lowStockProducts = products.filter(
  p => p.profile_id === profile.id && p.activo && p.stock_disponible <= threshold
)
```

**Problema**:
- Filtra productos por `profile_id` (concepto V1.0 multi-tenant)
- En tu negocio: TODOS los productos son globales
- Resultado: No muestra alertas de stock correctamente

**Solución V2.0**:
```tsx
// Opción A: Mostrar TODOS los productos con stock bajo (global)
const lowStockProducts = products.filter(
  p => p.activo && p.stock_disponible <= threshold
)

// Opción B (MEJOR): Consultar stock POR UBICACIÓN
const lowStockByLocation = await service.getStockAlerts(location.id, threshold)
```

**Impacto**: MEDIO  
**Decisión necesaria**: ¿Alertas globales o por ubicación física?

---

## ❌ PROBLEMA 2: NotificationCenter - Busca profile_id en productos

**Archivo**: `/src/components/NotificationCenter.tsx` línea 78

**Código V1.0 (INCORRECTO)**:
```tsx
products.forEach(product => {
  const profile = profiles.find(p => p.id === product.profile_id)
  if (!profile || !profile.active) return
  // ... genera notificaciones
})
```

**Problema**:
- Intenta encontrar el "profile" dueño de cada producto
- En V2.0: productos NO tienen dueño, son globales
- Resultado: No genera notificaciones correctamente

**Solución V2.0**:
```tsx
// V2.0: Products are global - check stock across all locations
products.forEach(product => {
  // Get stock for this product across all locations
  const globalStock = product.stock_disponible
  const threshold = 10 // Global threshold or get from settings
  
  if (globalStock <= threshold) {
    // Generate low stock notification
  }
})
```

**Impacto**: ALTO  
**Acción**: Corregir lógica de notificaciones para V2.0

---

## ❌ PROBLEMA 3: PendingTransfersDialog - Usa to_profile_id

**Archivo**: `/src/components/PendingTransfersDialog.tsx` línea 55

**Código V1.0 (INCORRECTO)**:
```tsx
const pending = data.items.filter(
  (t: StockTransfer) => t.estado === 'pendiente' && t.to_profile_id === profile.id
)
```

**Problema**:
- Filtra transfers por `to_profile_id` (transferencias entre profiles)
- En V2.0: transfers son entre UBICACIONES FÍSICAS (`to_location_id`)
- Componente completo usa concepto V1.0

**Solución V2.0**:
```tsx
// OPCIÓN A: Reescribir para usar locations
const pending = data.items.filter(
  (t: StockTransfer) => t.estado === 'pendiente' && t.to_location_id === location.id
)

// OPCIÓN B: Comentar componente completo - usar StockByLocationDialog
```

**Impacto**: MEDIO  
**Recomendación**: Comentar componente (duplica funcionalidad de StockByLocationDialog)

---

## 📊 RESUMEN DE PROBLEMAS

### Total Encontrados: 3 adicionales

| # | Componente | Tipo | Impacto | Estado |
|---|------------|------|---------|--------|
| 1 | LowStockAlert | Filtro profile_id | MEDIO | Pendiente |
| 2 | NotificationCenter | profile_id lookup | ALTO | Pendiente |
| 3 | PendingTransfersDialog | to_profile_id | MEDIO | Pendiente |

### Problemas Previos Corregidos: 5
- ✅ TransferStockDialog
- ✅ NotificationCenter (partial - optimization)
- ✅ use-optimization-alerts
- ✅ use-optimization-insights
- ✅ LowStockReportDialog (interim)

---

## 🎯 PLAN DE CORRECCIÓN

### Prioridad ALTA (hacer ahora):
1. **NotificationCenter** - Corregir generación de notificaciones
   - Eliminar búsqueda de profile por product.profile_id
   - Usar stock global o por location

### Prioridad MEDIA (próxima iteración):
2. **LowStockAlert** - Refactor para usar locations
   - Cambiar de filtro por profile a consulta por location
   - Integrar con API `/api/stock?location_id=X`

3. **PendingTransfersDialog** - Comentar o refactor
   - Opción 1: Comentar (usar StockByLocationDialog)
   - Opción 2: Refactor completo para V2.0 locations

---

## 🔍 BÚSQUEDA ADICIONAL NECESARIA

Debo revisar:
- ✅ Hooks (`use-*.ts`) - COMPLETADO
- ✅ Componentes principales (`*.tsx`) - EN PROGRESO
- ⏳ Servicios (`/lib/api.ts`) - Pendiente
- ⏳ Tipos (`/lib/types.ts`) - Verificar interfaces
- ⏳ Utilidades (`/lib/*.ts`) - Revisar helpers

---

*Generado automáticamente - Auditoría V2.0*
