# 🧪 TESTING EXECUTION PLAN - FASE 1.5 + 2

**Fecha**: Hoy (Diciembre 10, 2025)  
**Status**: En ejecución  
**Total Tests**: 15 bugs × 3 test cases = 45+ test cases  
**Tiempo Estimado**: 3-4 horas  

---

## 📋 TESTING SCHEDULE

### FASE 1.5 (8 bugs)
```
Test Suite 1: Backend Validations (Bugs #26, #28, #31, #32)
Test Suite 2: Frontend Validations (Bugs #5, #8, #9)
Test Suite 3: Stock Calculations (Bug #29)
```

### FASE 2 (7 bugs)
```
Test Suite 4: Order Transactions (Bug #1)
Test Suite 5: Stock & IMEI (Bugs #2, #3)
Test Suite 6: Location Management (Bug #4, #30)
Test Suite 7: Query Performance (Bug #27)
Test Suite 8: Stock Display (Bug #33)
```

---

## ✅ PRE-TESTING CHECKLIST

### Backend Setup
```bash
# Verificar BD
sqlite3 backend/inventory.db ".tables"

# Verificar dependencias instaladas
pip list | grep sqlalchemy

# Iniciar backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
# Verificar dependencias
npm list | grep react

# Iniciar frontend
npm run dev  # Port 5173
```

### Herramientas Testing
- Postman o curl para API testing
- Browser DevTools para frontend
- SQLite3 para DB inspection
- Swagger UI (http://localhost:8000/docs)

---

## 🧪 TEST SUITES DETALLADOS

### TEST SUITE 1: Backend Validations (30 min)

#### Bug #26: IMEI Validation Order ✅
**Objetivo**: Validar IMEI ANTES de decrementar stock

**Test Case 1.1**: IMEI válido
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "sales_profile_id": 1,
    "source_location_id": 1,
    "customer_name": "Test",
    "customer_phone": "123456",
    "canal": "whatsapp",
    "metodo_pago": "efectivo",
    "items": [{"product_id": 1, "cantidad": 1, "precio_unitario": 100}]
  }'

# Esperado: Status 201, orden creada
# Verificar: Stock decrementado
```

**Test Case 1.2**: IMEI duplicado
```bash
# Intentar crear 2 órdenes con mismo IMEI
# Esperado: 2da orden falla con 400 Bad Request
```

**Test Case 1.3**: Sin IMEI para producto serializado
```bash
# Crear orden sin IMEI para producto con IMEI requerido
# Esperado: Status 400, "IMEI required"
```

#### Bug #28: Rollback Improvements ✅
**Objetivo**: Verificar rollback automático en fallos

**Test Case 1.4**: Validación falla a mitad de orden
```bash
# Crear orden con item inválido en mitad de items[]
# Esperado: Toda orden falla, stock NO se afecta
# Verificar: SELECT cantidad_disponible = antes
```

#### Bug #31: Cantidad > 0 Validation ✅
**Objetivo**: Rechazar transfers con cantidad <= 0

**Test Case 1.5**: Transfer con cantidad = 0
```bash
curl -X POST http://localhost:8000/api/stock-transfers \
  -d '{"from_location_id": 1, "to_location_id": 2, "product_id": 1, "cantidad": 0}'

# Esperado: Status 400, "Cantidad debe ser > 0"
```

**Test Case 1.6**: Transfer con cantidad negativa
```bash
curl -X POST http://localhost:8000/api/stock-transfers \
  -d '{"from_location_id": 1, "to_location_id": 2, "product_id": 1, "cantidad": -5}'

# Esperado: Status 400, "Cantidad debe ser > 0"
```

#### Bug #32: Location Active Check ✅
**Objetivo**: Rechazar operaciones en locations inactivas

**Test Case 1.7**: Crear orden con location inactiva
```bash
# Marcar location como inactiva
UPDATE locations SET activo = FALSE WHERE id = 1

# Intentar crear orden
# Esperado: Status 400, "Location inactiva"

# Restaurar
UPDATE locations SET activo = TRUE WHERE id = 1
```

---

### TEST SUITE 2: Frontend Validations (20 min)

#### Bug #5: Form Reset Complete ✅
**Objetivo**: Verificar reset de todos los campos

**Test Case 2.1**: Crear orden y cancelar
```
1. Abre http://localhost:5173
2. Click "Nueva Orden"
3. Llena todos los campos
4. Click "Cancelar"
5. Click "Nueva Orden" de nuevo
6. Verificar: Todos los campos están vacíos
```

**Test Case 2.2**: Reset después de crear
```
1. Crea una orden exitosa
2. Toast muestra "Order created"
3. Forma automáticamente se resetea
4. Todos los campos vacíos
```

#### Bug #8: Reserved Stock Filter ✅
**Objetivo**: Mostrar solo stock disponible (no reservado)

**Test Case 2.3**: Stock filter
```
1. Abre NewOrderDialog
2. Selecciona product
3. Verifica: stock_disponible - stock_reservado = stock_libre
4. Crea orden con cantidad X
5. stock_libre debe decrementar por X
```

#### Bug #9: Location Required ✅
**Objetivo**: Validar location antes de crear orden

**Test Case 2.4**: Sin location seleccionada
```
1. Abre NewOrderDialog
2. Intenta crear orden sin seleccionar location
3. Error: "Location required"
4. Submit deshabilitado
```

---

### TEST SUITE 3: Stock Calculations (15 min)

#### Bug #29: Stock >= 0 Validation ✅
**Objetivo**: Stock nunca negativo en frontend

**Test Case 3.1**: Stock display no negativo
```
1. Abre Products list
2. Verifica: Todos los stocks >= 0
3. Intenta crear orden que exceda stock
4. Error: "Stock insuficiente"
5. Stock en UI sigue siendo >= 0
```

---

### TEST SUITE 4: Order Transactions (45 min)

#### Bug #1: Order Update Transactional ✅
**Objetivo**: Actualizar orden de forma atómica

**Test Case 4.1**: Update válido
```bash
# Crear orden
curl -X POST http://localhost:8000/api/orders \
  -d '{orden_data}'

# Actualizar items
curl -X PUT http://localhost:8000/api/orders/1 \
  -d '{items: [{product_id: 1, cantidad: 5, precio_unitario: 150}]}'

# Esperado: Status 200, orden actualizada
# Verificar: Stock restituido y re-decrementado correctamente
```

**Test Case 4.2**: Update con stock insuficiente
```bash
# Intentar aumentar cantidad sin stock disponible
# Esperado: Status 400, "Stock insuficiente"
# Verificar: Orden NO cambió
```

**Test Case 4.3**: Update parcial falla
```bash
# Update con item válido + item inválido
# Esperado: Toda la operación falla
# Stock permanece consistente
```

**Test Case 4.4**: Snapshot validation
```bash
# Verificar en logs que:
# 1. Snapshot de items anterior capturado
# 2. Validación antes de cambios
# 3. Rollback automático si hay error
```

---

### TEST SUITE 5: Stock & IMEI (40 min)

#### Bug #2: Quantity Reservada Validation ✅
**Objetivo**: Validar cantidad_reservada antes de transfer

**Test Case 5.1**: Transfer con cantidad > disponible
```bash
# Stock: cantidad_disponible=10, cantidad_reservada=5
# Disponible real: 10-5=5

curl -X POST http://localhost:8000/api/stock-transfers \
  -d '{cantidad: 6}'  # > 5 disponible

# Esperado: Status 400, "Stock insuficiente"
```

**Test Case 5.2**: Multiple transfers simultáneo
```bash
# Crear 2 transfers de mismo stock simultáneamente
# Esperado: Primero OK, segundo falla
# Stock total decrementado solo 1 vez
```

#### Bug #3: IMEI Reservation En Transfers ✅
**Objetivo**: Reservar IMEIs durante transfer

**Test Case 5.3**: Transfer con IMEI
```bash
# Stock tiene 3 IMEIs: A, B, C

curl -X POST http://localhost:8000/api/stock-transfers \
  -d '{product_id: 1, cantidad: 2, imeis: [A, B]}'

# Esperado: Status 201
# Verificar: IMEIs A, B ahora reservados
```

**Test Case 5.4**: IMEI duplicado en transfer
```bash
curl -X POST http://localhost:8000/api/stock-transfers \
  -d '{product_id: 1, cantidad: 2, imeis: [A, A]}'

# Esperado: Status 400, "Duplicated IMEI"
```

**Test Case 5.5**: IMEI no disponible
```bash
# IMEI A ya reservado

curl -X POST http://localhost:8000/api/stock-transfers \
  -d '{product_id: 1, cantidad: 1, imeis: [A]}'

# Esperado: Status 400, "IMEI not available"
```

---

### TEST SUITE 6: Location Management (30 min)

#### Bug #4: Auto-Create Location ✅
**Objetivo**: Auto-crear location en local mode si no existe

**Test Case 6.1**: Local mode auto-create
```javascript
// En frontend console:
const service = await inventoryServiceFactory.getService()
const order = await service.createOrder({
  source_location_id: 999,  // No existe
  ...
})

// Esperado: Location 999 auto-creada
// Verificar: DB tiene nueva location
```

**Test Case 6.2**: API mode no auto-crea
```bash
# Toggle settings_use_api = true
# Intentar crear orden con location que no existe
# Esperado: Status 400, "Location not found"
# NO auto-crea
```

#### Bug #30: Null Location_ID Handling ✅
**Objetivo**: Validar y rechazar null location_id

**Test Case 6.3**: Update con null location_id
```bash
# Actualizar orden con source_location_id = null
# Esperado: Status 400, "Location required"
# Orden no cambia
```

**Test Case 6.4**: Update a location inactiva
```bash
# Actualizar source_location_id a location inactiva
# Esperado: Status 400, "Location inactiva"
```

---

### TEST SUITE 7: Query Performance (20 min)

#### Bug #27: Query Optimization ✅
**Objetivo**: Verificar performance de queries

**Test Case 7.1**: Query time baseline
```bash
# Medir tiempo de GET /api/products?location_id=1
time curl http://localhost:8000/api/products?location_id=1

# Esperado: < 500ms (con datos de prueba)
# Verificar: No hay cartesian products
```

**Test Case 7.2**: Query con múltiples locations
```bash
# GET con múltiples location filters
# Esperado: < 1000ms incluso con datos grandes
```

**Test Case 7.3**: Database explain plan
```bash
sqlite3 backend/inventory.db
> EXPLAIN QUERY PLAN
  SELECT p.* FROM products p
  LEFT JOIN stock s ON p.id = s.product_id
  WHERE s.location_id = 1;

# Verificar: No hay "CROSS JOIN" o "cartesian product"
```

---

### TEST SUITE 8: Stock Display (15 min)

#### Bug #33: Stock Calculation Validation ✅
**Objetivo**: Stock nunca negativo en pantalla

**Test Case 8.1**: Negative stock handling
```javascript
// En App.tsx:
const stock_disponible = 5;
const stock_reservado = 10;
const stock_libre = Math.max(0, stock_disponible - stock_reservado);

// Esperado: stock_libre = 0 (no -5)
```

**Test Case 8.2**: Visual verification
```
1. Abre ProductsList
2. Verifica: Todos los stocks >= 0
3. Incluso si cantidad_disponible < cantidad_reservada
4. Muestra 0, no número negativo
```

---

## 📊 TESTING RESULTS TEMPLATE

```markdown
## TEST RESULTS - [Date]

### Phase 1.5 (8 bugs)
- [ ] Bug #5:  Form reset                    ✅/❌ [Notes]
- [ ] Bug #8:  Reserved stock filter         ✅/❌ [Notes]
- [ ] Bug #9:  Location required             ✅/❌ [Notes]
- [ ] Bug #26: IMEI validation order         ✅/❌ [Notes]
- [ ] Bug #28: Rollback improvements         ✅/❌ [Notes]
- [ ] Bug #29: Stock >= 0 validation         ✅/❌ [Notes]
- [ ] Bug #31: Cantidad > 0 validation       ✅/❌ [Notes]
- [ ] Bug #32: Location active check         ✅/❌ [Notes]

### Phase 2 (7 bugs)
- [ ] Bug #1:  Order update transactional    ✅/❌ [Notes]
- [ ] Bug #2:  Quantity reservada            ✅/❌ [Notes]
- [ ] Bug #3:  IMEI reservation              ✅/❌ [Notes]
- [ ] Bug #4:  Auto-create location          ✅/❌ [Notes]
- [ ] Bug #27: Query optimization            ✅/❌ [Notes]
- [ ] Bug #30: Null location_id              ✅/❌ [Notes]
- [ ] Bug #33: Stock calculation             ✅/❌ [Notes]

### Summary
- Total Passed: 15/15 ✅
- Total Failed: 0/15 ✅
- Status: GO FOR DEPLOYMENT ✅

### Issues Found
(None if all passed)

### Recommendations
(Next steps, issues to fix, etc.)
```

---

## 🚀 QUICK TEST SCRIPT (15 min version)

Si tienes solo 15 minutos:

```bash
# 1. Backend health check
curl http://localhost:8000/docs

# 2. Create test product with IMEI
curl -X POST http://localhost:8000/api/products \
  -d '{name: "Test Phone", imeis: ["IMEI001"], ...}'

# 3. Create order (should validate IMEI)
curl -X POST http://localhost:8000/api/orders \
  -d '{sales_profile_id: 1, source_location_id: 1, items: [{product_id: 1, ...}]}'

# 4. Update order (should be transactional)
curl -X PUT http://localhost:8000/api/orders/1 \
  -d '{items: [{product_id: 1, cantidad: 5, ...}]}'

# 5. Check stock never negative
curl http://localhost:8000/api/products/1/stock

# 6. Test query performance
time curl http://localhost:8000/api/products?location_id=1
```

---

## ✅ GO/NO-GO CRITERIA

### GO Criteria (todos deben estar ✅)
```
[✅] All 15 bugs pass testing
[✅] No critical errors in logs
[✅] Query performance < 500ms
[✅] Stock never negative
[✅] Zero data loss
[✅] Transactional integrity verified
```

### NO-GO Criteria (si alguno está ❌)
```
[❌] Any test fails
[❌] Critical errors in logs
[❌] Performance degradation
[❌] Data inconsistency
[❌] Breaking changes detected
```

---

## 🎯 NEXT STEPS

1. **Ejecutar**: Sigue cada TEST SUITE en orden
2. **Registrar**: Documenta resultados en template
3. **Decidir**: GO si todos pasan, NO-GO si alguno falla
4. **Actuar**: Si GO → deployment, si NO-GO → debug + re-test

---

**Status**: Lista para ejecución  
**Tiempo Total**: 3-4 horas  
**Próximo**: START TESTING 🧪
