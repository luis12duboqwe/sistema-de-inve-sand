# Plan de Pruebas y Validaciones (V2.0)

Documento maestro que consolida las verificaciones necesarias para garantizar que el sistema opera correctamente tanto en modo local (Spark KV) como conectado al backend FastAPI.

---

## 1. Alcance
- Cobertura de funcionalidades críticas: inventario, órdenes, transferencias, IMEI, trade-in, financiamiento, IA, RBAC y sincronización dual-mode.
- Validación de flujos completos: creación → actualización → sincronización → consulta en backend.
- Compatibilidad entre navegadores (Chrome y Edge) y dispositivos (desktop/tablet/mobile).

---

## 2. Niveles de Prueba
| Nivel | Objetivo | Herramientas |
|-------|----------|--------------|
| Smoke | Confirmar que frontend y backend arrancan sin errores | `npm run dev`, `uvicorn app.main:app` |
| Funcional | Validar flujos CRUD y reglas de negocio | UI manual, Swagger (http://localhost:8000/docs) |
| Integración | Verificar dual-mode (local + API) usando `inventoryServiceFactory` | KV inspector, DevTools, FastAPI logs |
| Sincronización | Probar subida de eventos locales al backend tras reconexión | `syncService`, nuevo journal |
| Regresión | Re-ejecutar checklist previo antes de release | `docs/GUIA_TESTING.md` |

---

## 3. Escenarios Esenciales

### 3.1 Inventario Multi-Ubicación
- Crear productos en modo local, asignar stock por ubicación, validar que `stock_items` reflejan cantidades y reservados.
- Conectar a backend, verificar que los productos aparecen vía API (`GET /api/products`) con los mismos totales.
- Transferir stock entre ubicaciones y confirmar historial (`PendingTransfersDialog` + endpoint `POST /api/stock-transfers`).

### 3.2 Órdenes y Pagos
- Generar órdenes con distintos canales y métodos de pago, incluyendo financiamiento.
- Cancelar pedidos y asegurar que el stock se revierte (verificar logs locales y `GET /api/orders`).
- Simular trade-ins dentro del flujo de órdenes (productos `categoria='pendiente_revision'` → activación → venta).

### 3.3 IMEI y Productos Serializados
- Registrar IMEIs en una ubicación, transferirlos y venderlos.
- Consultar el historial desde frontend y API (`GET /api/imeis/history/{imei}`) para comprobar trazabilidad.

### 3.4 IA y Bots
- Configurar un `AIProfileConfig`, generar contexto y revisar `useAIStatus` tanto en local como en modo API.
- Procesar entradas del `AITrainingCenter` y validar que las FAQs se actualizan en ambos modos.

### 3.5 RBAC
- Crear roles/usuarios en local, luego habilitar API y confirmar que los endpoints respetan los mismos permisos (uso de `check_permission`).
- Intentar acciones sin permisos y verificar respuestas HTTP 403 en backend + mensajes en frontend.

### 3.6 Sincronización Local→API
- Desconectar backend, operar en local (crear productos, órdenes, transferencias, IMEIs).
- Reconectar: seguir proceso definido en `docs/SYNC_STRATEGY.md` y asegurar que el journal se vacía y el snapshot se actualiza.
- Generar conflictos intencionales (editar mismo producto en backend y local) y documentar el manejo.

---

## 4. Automatización Propuesta
- **Backend:** ampliar `backend/app/tests/` para cubrir órdenes, transfers, IMEI y RBAC (pytest + SQLite en memoria).
- **Frontend:** configurar `vitest` + `@testing-library/react` para componentes críticos (formularios de órdenes, transferencias, dialogs de IA).
- **E2E (futuro):** integrar Playwright para simular cambios de modo local/API y sincronización.

---

## 5. Evidencia y Reportes
- Registrar capturas/logs en `docs/testing-reports/<fecha>.md` con resultados de cada sesión.
- Adjuntar outputs de scripts (`test-system.sh`, pytest, vitest) y capturas de la consola del navegador.
- Documentar incidentes y resoluciones en issues de GitHub para trazabilidad.

---

## 6. Criterios de Salida
- 0 fallos críticos abiertos.
- Sincronización validada con al menos 50 eventos locales replicados correctamente.
- Cobertura básica de pruebas automatizadas ejecutada (backend + frontend unit tests).
- Checklist de `docs/GUIA_TESTING.md` completado y firmado.

---

## 7. Próximos Pasos
1. Implementar el journal y orquestador de sincronización descritos en `SYNC_STRATEGY.md` para habilitar pruebas reales.
2. Priorizar automatización en áreas de mayor riesgo (transferencias de stock, IMEI, sincronización).
3. Integrar los resultados de cada release en pipelines CI/CD.
