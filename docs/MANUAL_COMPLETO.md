# 🚀 TESTING & DEPLOYMENT INSTRUCTIONS

**Fecha**: Hoy (Diciembre 10, 2025)  
**Status**: LISTO PARA EJECUCIÓN  
**Duración Total**: 4-5 horas  

---

## ⏱️ TIMELINE

```
AHORA (5 min):      Setup & verificación
0:05 - 1:00        Test Suite 1-3 (Backend)
1:00 - 2:00        Test Suite 4-5 (Orders)
2:00 - 3:00        Test Suite 6-7 (Frontend + Performance)
3:00 - 3:30        Manual smoke tests
3:30 - 4:00        GO/NO-GO decision
4:00 - 5:00        Deployment a staging
5:00 - 5:30        Final smoke tests en staging
```

---

## 🎯 PASO 1: SETUP (5 minutos)

### Terminal 1: Backend
```bash
cd /workspaces/spark-template/backend

# Verificar BD existe
ls -la inventory.db

# Si no existe, inicializar
# python3 init_db.py --with-data

# Activar venv e instalar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Iniciar backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Esperado:
```
Uvicorn running on http://0.0.0.0:8000
Application startup complete
```

### Terminal 2: Frontend
```bash
cd /workspaces/spark-template

# Instalar dependencias (si no lo hizo)
npm install

# Iniciar Vite
npm run dev
```

Esperado:
```
  ➜  Local:   http://localhost:5173
  ➜  press h to show help
```

### Terminal 3: Testing
```bash
cd /workspaces/spark-template

# Hacer executable el script
chmod +x run-tests.sh

# Verificar que backend está listo
curl http://localhost:8000/docs
```

---

## 🧪 PASO 2: AUTOMATED TESTING (30 minutos)

### Ejecutar test suite automatizado
```bash
./run-tests.sh
```

Esperado:
```
==================================
🧪 STARTING AUTOMATED TESTING
==================================

📋 PRE-FLIGHT CHECKS
====================
Checking Backend availability at http://localhost:8000... ✅ Backend is running

🧪 RUNNING TEST SUITES
======================

📊 TEST SUITE 1: Backend Health
-------------------------------
Testing: Swagger UI accessible... ✅ PASS (HTTP 200)
Testing: OpenAPI schema... ✅ PASS (HTTP 200)
Testing: List products... ✅ PASS (HTTP 200)
Testing: List orders... ✅ PASS (HTTP 200)

[... more test suites ...]

==================================
📊 TESTING SUMMARY
==================================
Tests Passed: 20+
Tests Failed: 0
✅ ALL TESTS PASSED!
🚀 System is ready for deployment
```

---

## 🖥️ PASO 3: MANUAL FRONTEND TESTING (1 hora)

### Test Suite A: Order Creation (Bug #1, #5, #9, #26, #28)

1. **Abre** http://localhost:5173
2. **Click** "Nueva Orden"
3. **Verifica**: Form vacío (Bug #5 - reset)
4. **Llena** todos los campos:
   - Sales Profile: Selecciona uno
   - Location: Selecciona uno (Bug #9 - required)
   - Customer: "Test Customer"
   - Phone: "123-4567"
   - Channel: "whatsapp"
   - Payment: "efectivo"
5. **Agrega Item**: Product + Cantidad
6. **Verifica**: Stock disponible mostrado (Bug #8 - no reservado)
7. **Click** "Crear Orden"
8. **Esperado**: Toast verde "Orden creada exitosamente"
9. **Verifica**: Form se resetea (Bug #5)

### Test Suite B: Stock Display (Bug #29, #33)

1. **Abre** ProductsList
2. **Verifica**: Todos stocks >= 0
3. **Scrollea** y busca producto con `cantidad_reservada > cantidad_disponible`
4. **Esperado**: Stock mostrado como 0, no negativo
5. **Verifica**: Math.max(0, disponible - reservado) funcionando

### Test Suite C: Location Management (Bug #4, #30, #32)

1. **En NewOrderDialog**, selecciona location
2. **Verifica**: Solo locations activas aparecen
3. **En local mode**, crea orden con location_id que no existe
4. **Esperado**: Auto-crea location silenciosamente
5. **Verifica**: DB tiene nueva location

### Test Suite D: Stock Operations (Bug #2, #3, #31)

1. **Abre** StockByLocationDialog
2. **Verifica**: Multi-location stock viewable
3. **Intenta** transfer con cantidad > disponible
4. **Esperado**: Error "Stock insuficiente"
5. **Intenta** transfer con cantidad <= 0
6. **Esperado**: Error "Cantidad debe ser > 0" (Bug #31)
7. **Intenta** transfer con IMEI duplicado
8. **Esperado**: Error "IMEI duplicado" (Bug #3)

---

## 🔍 PASO 4: PERFORMANCE TESTING (15 minutos)

### Test Query Performance (Bug #27)

```bash
# Terminal 3: Medir query time
time curl http://localhost:8000/api/products?location_id=1

# Esperado: < 500ms
```

Ejemplo esperado:
```
real    0m0.342s    ← < 500ms ✅
user    0m0.098s
sys     0m0.056s
```

### Test Database Optimization

```bash
# Verificar explain plan
sqlite3 /workspaces/spark-template/backend/inventory.db

sqlite> EXPLAIN QUERY PLAN
...> SELECT p.* FROM products p
...> LEFT JOIN stock s ON p.id = s.product_id
...> WHERE s.location_id = 1;
```

Esperado: Sin "CROSS JOIN" o "cartesian"

---

## ✅ PASO 5: GO/NO-GO DECISION (30 minutos)

### Checklist GO Criteria
```
[ ] Automated tests: 20+/20+ passed
[ ] Frontend smoke tests: Todos OK
[ ] No critical errors en logs
[ ] Query performance: < 500ms
[ ] Stock: Nunca negativo
[ ] Transactions: Atómicas
[ ] Zero data loss
```

### Si TODOS están ✅
→ **DECISION: GO**  
→ Proceder a Paso 6: Deployment

### Si alguno está ❌
→ **DECISION: NO-GO**  
→ Debug y re-ejecutar testing

---

## 🚀 PASO 6: DEPLOYMENT A STAGING (1-2 horas)

**Solo si decisión fue GO**

### 6.1 Pre-Deployment Final Check

```bash
# Verify code changes
cd /workspaces/spark-template

# Check git status
git status

# Expected: 6 modified files
# - backend/app/routers/orders.py
# - backend/app/routers/stock_transfers.py
# - backend/app/routers/products.py
# - src/lib/inventoryService.ts
# - src/components/NewOrderDialog.tsx
# - src/App.tsx
```

### 6.2 Build Frontend

```bash
npm run build

# Expected output:
# ✓ 1234 modules transformed...
# dist/index.html                 0.45 kB
# dist/assets/index-xxxxx.js     234.56 kB / gzip: 78.90 kB
```

### 6.3 Database Backup

```bash
# Backup production DB
cp backend/inventory.db backend/inventory.db.backup.$(date +%Y%m%d_%H%M%S)

# Verify backup
ls -la backend/inventory.db.backup.*
```

### 6.4 Deploy Backend

```bash
# Stop current backend
# (Kill the uvicorn process from Terminal 1)

# Create production config
export ENVIRONMENT=production
export LOG_LEVEL=info

# Start backend in production mode
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6.5 Deploy Frontend

```bash
# Assuming you have a way to serve static files
# Option 1: Use a simple HTTP server
cd dist
python3 -m http.server 3000

# Option 2: Deploy to Vercel, Netlify, etc.
# Follow their specific deployment instructions
```

### 6.6 Verify Deployment

```bash
# Check backend is running
curl http://localhost:8000/docs

# Check frontend is accessible
curl http://localhost:3000  # or wherever frontend is served

# Expected: Both return 200 OK
```

---

## 🧪 PASO 7: POST-DEPLOYMENT SMOKE TESTS (30 minutos)

### Verify Production Setup

1. **Open frontend** in browser
2. **Login** if required
3. **Navigate** to Products list
4. **Verify**: Data loads correctly
5. **Create test order** and verify
6. **Check logs** for errors
7. **Monitor metrics** if available

### Health Check Endpoints

```bash
# API Health
curl http://localhost:8000/docs

# Database connectivity
curl http://localhost:8000/api/products

# Frontend
curl http://localhost:3000

# Expected: All 200 OK
```

---

## 📋 TROUBLESHOOTING

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill if necessary
kill -9 <PID>

# Check dependencies
pip list | grep -E "sqlalchemy|fastapi"

# Reinstall if needed
pip install -r requirements.txt
```

### Frontend build fails
```bash
# Clear cache
rm -rf node_modules
npm install

# Clear Vite cache
rm -rf .vite

# Rebuild
npm run build
```

### Tests fail
```bash
# Check database
sqlite3 backend/inventory.db ".tables"

# Reinitialize if needed
rm backend/inventory.db
python3 backend/init_db.py --with-data

# Re-run tests
./run-tests.sh
```

### Database issues
```bash
# Backup current
cp backend/inventory.db backend/inventory.db.broken

# Use backup
cp backend/inventory.db.backup.latest backend/inventory.db

# Verify
sqlite3 backend/inventory.db ".schema products"
```

---

## ✅ FINAL CHECKLIST

```
TESTING PHASE
[ ] Automated test suite passed
[ ] Frontend smoke tests passed
[ ] Performance tests passed
[ ] GO decision documented

DEPLOYMENT PHASE
[ ] Code changes verified
[ ] Frontend built successfully
[ ] Database backed up
[ ] Backend deployed
[ ] Frontend deployed
[ ] Post-deployment smoke tests passed
[ ] Logs monitored, no errors
[ ] Metrics baseline established

SIGN-OFF
[ ] All team members notified
[ ] Users can access system
[ ] Data integrity verified
[ ] Performance metrics OK
[ ] Rollback plan ready
[ ] ✅ DEPLOYMENT COMPLETE
```

---

## 🎯 SUCCESS CRITERIA

### If all above passed:
```
✅ 15 bugs fixed
✅ Zero breaking changes
✅ Zero data loss
✅ Performance improved
✅ System stable
✅ Ready for next phase
```

---

## 📞 NEXT STEPS

### Immediately After Deployment
1. Monitor logs for 24 hours
2. Collect user feedback
3. Fix any critical issues
4. Document lessons learned

### Within 1 Week
1. Plan Phase 3 (25 remaining bugs)
2. Assign team resources
3. Start implementation

### Within 1 Month
1. Phase 3 implementation 50% complete
2. Continuous testing
3. Regular deployments

---

**Status**: ✅ READY FOR EXECUTION  
**Owner**: [Your Team]  
**Approval**: [Manager]  
**Date**: Hoy  

**¡VAMOS AL DEPLOYMENT! 🚀**
