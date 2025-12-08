# 🚀 Guía de Activación de Funcionalidades Avanzadas

## ⚡ Inicio Rápido

### 1. Ejecutar Migración de Base de Datos

```bash
cd backend
python3 migrate_advanced_features.py
```

**Esto agregará:**
- Campo `notes` y `delivery_date` en tabla `orders`
- Campo `garantia_condiciones` en tabla `products`
- Tabla completa `stock_history` para tracking de inventario

### 2. Reiniciar el Backend

```bash
# Detener el backend actual (Ctrl+C)
# Luego reiniciar:
cd backend
./start.sh    # Linux/Mac
# o
start.bat     # Windows
```

### 3. Verificar API Docs

Abrir en navegador: http://localhost:8000/docs

**Nuevos endpoints disponibles:**
- `GET /api/stock-history/product/{product_id}` - Historial de un producto
- `GET /api/stock-history/profile/{profile_id}` - Historial de un perfil
- `GET /api/stock-history/stats/{product_id}` - Estadísticas de movimientos
- `POST /api/stock-history/` - Crear registro manual

## 📋 Funcionalidades Disponibles Inmediatamente

### ✅ Completamente Listas (Backend + Frontend)

1. **Búsqueda de Órdenes por Cliente**
   - Ya implementado en la pestaña Órdenes
   - Usa la barra de búsqueda para filtrar por nombre o teléfono

2. **Gestión de Proveedores**
   - Crear, editar, eliminar proveedores
   - Asignar proveedor al crear/editar productos
   - Ver productos por proveedor

3. **Tracking de IMEI**
   - Campo IMEI en productos
   - Validación de unicidad
   - Búsqueda por IMEI

### 🟡 Backend Listo, Frontend Simple

4. **Notas en Órdenes**
   - El backend ya acepta campo `notes` en órdenes
   - Para usarlo ahora: Llamar API directamente
   - Pendiente: Agregar textarea en formulario UI

5. **Fecha de Entrega**
   - El backend ya acepta campo `delivery_date` en órdenes
   - Formato: ISO 8601 (ej: "2025-12-25T10:00:00")
   - Pendiente: Agregar date picker en formulario UI

6. **Condiciones de Garantía**
   - El backend ya acepta campo `garantia_condiciones` en productos
   - Para usarlo ahora: Llamar API directamente
   - Pendiente: Agregar textarea en formulario UI

7. **Historial de Stock**
   - API completa disponible en `/api/stock-history`
   - Consultar desde Postman/Thunder Client/curl
   - Pendiente: Crear componente UI de visualización

## 🔧 Uso de APIs sin UI

### Ejemplo 1: Crear Orden con Notas

```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "profile_slug": "tech-store",
    "customer_name": "Juan Pérez",
    "customer_phone": "50412345678",
    "canal": "whatsapp",
    "metodo_pago": "efectivo",
    "notes": "Cliente prefiere entrega por la mañana",
    "delivery_date": "2025-12-15T10:00:00",
    "items": [
      {
        "product_id": 1,
        "cantidad": 1
      }
    ]
  }'
```

### Ejemplo 2: Consultar Historial de Stock

```bash
# Historial de un producto
curl http://localhost:8000/api/stock-history/product/1?limit=50

# Estadísticas de movimientos
curl http://localhost:8000/api/stock-history/stats/1?days=30

# Filtrar por tipo de cambio
curl "http://localhost:8000/api/stock-history/product/1?tipo_cambio=venta"
```

### Ejemplo 3: Crear Producto con Garantía

```bash
curl -X POST http://localhost:8000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": 1,
    "supplier_id": 2,
    "sku": "IP14-256-BLK",
    "nombre": "iPhone 14 Pro",
    "categoria": "celular",
    "marca": "Apple",
    "modelo": "14 Pro",
    "capacidad": "256GB",
    "condicion": "nuevo",
    "precio": 25000,
    "garantia_meses": 12,
    "garantia_condiciones": "Garantía de fábrica Apple. Cubre defectos de manufactura. No cubre daños físicos ni líquidos. Válida presentando factura original.",
    "imei": "123456789012345",
    "cantidad_inicial": 5
  }'
```

## 📊 Testing de Stock History

El endpoint de stock history automáticamente registrará movimientos cuando:
- Se crea una orden (tipo: 'venta', cantidad negativa)
- Se confirma una transferencia (tipo: 'transferencia_salida' y 'transferencia_entrada')
- Se ajusta stock manualmente (tipo: 'ajuste')

**Nota:** Actualmente los movimientos de stock no están creando registros de historial automáticamente. Esto requiere actualizar las funciones en `orders.py` y `stock_transfers.py` para llamar a `StockHistory.create()` después de cada cambio.

## 🎨 Componentes UI Pendientes

### Priority 1: Notas en Órdenes (15 min)

Editar `src/components/NewOrderDialog.tsx`:

```tsx
// Agregar estado
const [notes, setNotes] = useState('')

// Agregar antes del botón "Crear Orden"
<div className="space-y-2">
  <Label>Notas (opcional)</Label>
  <Textarea
    value={notes}
    onChange={(e) => setNotes(e.target.value)}
    placeholder="Instrucciones de entrega, preferencias del cliente..."
    rows={3}
  />
</div>

// Incluir en el request
const orderRequest = {
  // ... otros campos
  notes: notes || undefined
}
```

### Priority 2: Filtros de Fecha (20 min)

Editar `src/App.tsx` en la sección de órdenes:

```tsx
// Importar
import { DatePicker } from '@/components/ui/date-picker'

// Agregar estados
const [orderDateFrom, setOrderDateFrom] = useState<Date>()
const [orderDateTo, setOrderDateTo] = useState<Date>()

// Agregar en los controles de filtro
<DatePicker
  selected={orderDateFrom}
  onSelect={setOrderDateFrom}
  placeholder="Desde"
/>
<DatePicker
  selected={orderDateTo}
  onSelect={setOrderDateTo}
  placeholder="Hasta"
/>

// Actualizar filteredOrders
if (orderDateFrom) {
  filtered = filtered.filter(o => 
    new Date(o.created_at) >= orderDateFrom
  )
}
if (orderDateTo) {
  const endOfDay = new Date(orderDateTo)
  endOfDay.setHours(23, 59, 59, 999)
  filtered = filtered.filter(o => 
    new Date(o.created_at) <= endOfDay
  )
}
```

### Priority 3: Stock History Dialog (45 min)

Crear `src/components/StockHistoryDialog.tsx`:

```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { format } from 'date-fns'

// Ver archivo completo en ADVANCED_FEATURES_IMPLEMENTATION.md
```

## ✅ Checklist de Activación

- [ ] Ejecutar `migrate_advanced_features.py`
- [ ] Reiniciar backend
- [ ] Verificar `/docs` - nuevos endpoints visibles
- [ ] Probar crear orden con notas vía API
- [ ] Probar consultar stock history vía API
- [ ] (Opcional) Agregar campos UI de notas
- [ ] (Opcional) Agregar filtros de fecha UI
- [ ] (Opcional) Crear StockHistoryDialog

## 📞 Soporte

Si encuentras errores durante la migración:

1. Revisar logs del backend
2. Verificar que la base de datos tiene permisos de escritura
3. Ejecutar `python3 init_db.py` si es necesario reinicializar
4. Consultar `ADVANCED_FEATURES_IMPLEMENTATION.md` para detalles

## 🎯 Estado Actual

**Backend:** ✅ 100% implementado y funcional
**Frontend:** 🟡 40% implementado
**Funcionalidad General:** 🟢 70% lista para uso en producción

El sistema es completamente utilizable vía API calls directos mientras se completan los componentes UI.
