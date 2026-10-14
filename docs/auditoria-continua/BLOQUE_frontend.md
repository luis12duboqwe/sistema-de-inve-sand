# Auditoría frontend SoftMobile (sólo lectura)
Commit `dba6763391d12c6c91c9904cba36725710f9280a`. Revisión estática; pruebas y runtime no ejecutados por este agente.
Cobertura: 61 archivos completos / 15295 líneas; 8 archivos parciales; 98 archivos src pendientes (exceptuando primitivas UI/proxies). No se modificó repo ni git.

## FE-01 — ALTA: Pagos mixtos con tarjeta calculan/importan totales incompatibles con backend
Estado: CONFIRMADO POR CODIGO.

**Evidencia**
- src/components/NewOrderDialog.tsx getOrderFinancials 590-642: recargo cardBaseAmount * tasa; total neto + ese recargo
- src/components/NewOrderDialog.tsx handleSubmit 750-767,820-833: método principal = mayor importe; financing_data prima independiente
- backend/app/utils/order_financing.py compute_financing_from_payload 102-150: rechaza efectivo/transferencia con financing_data y calcula recargo sobre total neto-prima
- backend/app/services/order_service.py create_order 236-246,280-287: total calculado persiste y commit; no conciliación breakdown en tramo creación leído

**Reproducción pendiente de ejecutar**: Neto1000, tasa5%, efectivo600 tarjeta400 prima0: UI1020; payload metodo efectivo + financing_data ->400. Efectivo400 tarjeta600 prima0: UI1030; backend total1050 y breakdown1030. Para extrafinanciamiento con monto tarjeta1000, plazo6 tasa10% y tarjeta normal5%: UI1100 pero breakdown1050 y método tarjeta (no financiamiento).

**Impacto**: Bloquea venta mixta o guarda cobro desglose diferente del total; modalidad financiamiento también pierde su enum si hay desglose.

**Recomendación**: Definir un contrato único de base tarjeta/financiamiento; mantener modalidad elegida, deducir pagos no tarjeta de monto financiado y validar suma breakdown vs total en servidor.

**Tests**: NewOrderDialog.test.tsx sólo nombre faltante; tests/browser/financing.spec.ts sólo alta banco, ninguna venta financiada; Añadir UI+PostgreSQL cash/card, transfer/card, financiación, prima, tasa0 y redondeos

## FE-02 — ALTA: Reintentos automáticos repiten mutaciones no idempotentes
Estado: RIESGO CONFIRMADO EN CLIENTE; DEDUP BACKEND A CRUZAR CON PADRE.

**Evidencia**
- src/lib/apiClient.ts request 338-401: retries=3 para cualquier method, UUID nuevo por intento, Failed to fetch reintenta
- src/lib/apiClient.ts createOrder 1203-1206, createStockTransfer1315-1321, restockProduct1079-1085: POST mediante request
- backend/app/services/order_service.py create_order 284: commit antes de entregar respuesta

**Reproducción pendiente de ejecutar**: POST venta accesorio efectivo con stock>=2. Backend confirma commit; perder/resetear respuesta al cliente para que fetch rechace Failed to fetch. Cliente envía el mismo cuerpo otra vez con X-Request-ID diferente.

**Impacto**: Cliente puede duplicar venta, stock o traslado por fallo de respuesta; consumos con IMEI/referencia únicos podrían fallar en vez de duplicar, sin resolver incertidumbre del usuario.

**Recomendación**: Reintentar sólo lecturas seguras mientras no exista idempotencia servidor; para mutaciones usar clave estable de operación persistida y respuesta deduplicada transaccional.

**Tests**: apiClient.test.ts no cubre fallo red después commit ni reintentos POST; Necesario backend+cliente con pérdida respuesta tras commit

## FE-03 — MEDIA: Venta rechazada cierra y borra el formulario como si hubiese terminado
Estado: CONFIRMADO POR CODIGO.

**Evidencia**
- src/App.tsx NewOrderDialog.onSubmit 2429-2432 captura sin relanzar
- src/components/NewOrderDialog.tsx handleSubmit 813-837 await onSubmit y cierra; resetForm207-245 al cerrar

**Reproducción pendiente de ejecutar**: Completar venta válida en UI, responder400 (stock cambiado, referencia repetida, límite precio) al POST. App muestra toast error pero resuelve Promise; diálogo llama onOpenChange(false) y borra cliente/items.

**Impacto**: Usuario pierde entrada y puede confundir fallo con éxito. Si POST guarda pero GET products falla, también informa Error al crear orden aunque ya fue creada.

**Recomendación**: Propagar error de creación; separar persistencia confirmada de refresco fallido, mantener formulario cuando creación no confirmada.

**Tests**: NewOrderDialog.test.tsx no prueba rechazo onSubmit; App.saleCompletion.test.ts inspección texto, no integración submit

## FE-04 — ALTA: Traslado multi-modelo anunciado como una operación deja resultado parcial y repetir duplica líneas
Estado: CONFIRMADO POR CODIGO.

**Evidencia**
- src/components/TransferStockDialog.tsx handleSubmit 313-333: for POSTs individuales, catch conserva todas las líneas
- src/components/TransferStockDialog.tsx DialogDescription346-347 dice mover varios modelos en una sola operación

**Reproducción pendiente de ejecutar**: Dos accesorios A y B en traslado. POST A201; POST B409 por stock concurrente o500. A ya pendiente en servidor, UI sólo error y sigue con A/B. Volver Registrar repite POST A antes de B.

**Impacto**: Incumple atomicidad comercial; reserva/despacha A aunque lote no terminó, segunda ejecución puede duplicar A. No se reportan IDs exitosos ni refresca stock en fallo.

**Recomendación**: Endpoint batch con transacción única; mientras se implemente, mostrar y conservar progreso por línea, no reenviar exitosas, reconciliar antes de reintentar.

**Tests**: Sin test TransferStockDialog; E2E transfer-lifecycle.spec.ts sólo un accesorio; agregar lote+fallo línea2

## FE-05 — ALTA: Caché global de negocio permite mezclar datos de usuarios/ubicaciones entre sesiones y pestañas
Estado: CONFIRMADO POR CODIGO.

**Evidencia**
- src/App.tsx MainApp84-89 usa useKV inventory-products/orders/profiles/locations sin user/backend namespace
- src/App.tsx logout269-275 elimina auth pero no datasets ni dataLoaded
- src/App.tsx loadData381-434 no invalida previos al nuevo usuario, sin cancelación/respuesta guard; catch mantiene data y marca loaded
- src/hooks/use-kv.ts load+storage73-88 lee mismas claves; src/lib/kvStorage.ts prefix spark-kv sin usuario
- src/lib/apiClient.ts token283-299 queda en memoria; no evento storage auth

**Reproducción pendiente de ejecutar**: A ubicación1 carga datos; logout e ingresar B con orders:view ubicación2; bloquear GET de carga B: siguen orders A y dataLoaded true. Dos pestañas mantienen token en memoria distinto tras login/logout global y datasets de una se propagan por storage a otra.

**Impacto**: Exposición de clientes/ventas/stock fuera del alcance sesión actual, transitoria o hasta recarga exitosa; servidor no autoriza estos datos leídos desde navegador.

**Recomendación**: Estado negocio sólo en memoria o caché segregada por backend+usuario+alcance; limpiar/invalidate al logout/auth cambio, cancelar solicitudes antiguas y sincronizar auth entre tabs.

**Tests**: No tests App aislamiento sesión/tab; Añadir dos usuarios ubicaciones disjuntas, carga fallida y responses fuera de orden

## FE-06 — MEDIA: Lista transferencias corta silenciosamente a la primera página de50
Estado: CONFIRMADO POR CODIGO.

**Evidencia**
- src/lib/apiClient.ts listStockTransfers1326-1356 sólo una request sin page/per_page y descarta total/pages
- backend/app/routers/stock_transfers.py list_transfers184-185 defaults page1 per_page50
- src/components/TransferListDialog.tsx loadTransfers69-79 filtra ubicación local;291-293 estados locales

**Reproducción pendiente de ejecutar**: 51+ transferencias visibles, transferencia pendiente antigua fuera primera50. Abrir En tránsito puede mostrar ninguna aunque servidor tiene pendientes en página2. Filtro ubicación se aplica después del corte.

**Impacto**: Oculta recepciones pendientes e inventario en tránsito; contadores e historial falsos.

**Recomendación**: Paginar todas o implementar paginación UI con filtros estado/ubicación enviados servidor y total visible.

**Tests**: apiClient tests paginan users/roles/permissions pero no stock-transfers; TransferList test usa array2; agregar51+ y pendiente página2

## FE-07 — MEDIA: Notas API desaparecen de tarjeta y editor por notes/notas
Estado: CONFIRMADO POR CODIGO.

**Evidencia**
- backend/app/schemas/order.py OrderResponse369: notes; routers/orders.py serialize260: notes=order.notes
- src/lib/apiClient.ts mapApiOrder302-335 spread API sin asignación notas
- src/components/OrderCard.tsx 226-230 sólo order.notas; EditOrderDialog.tsx81,193 inicia order.notas

**Reproducción pendiente de ejecutar**: Crear orden con notes=instrucciones entrega. API responde notes; tarjeta no muestra texto y editor abre vacío. Escribir nueva nota guarda reemplazo sin exponer anterior.

**Impacto**: Se pierden visualmente instrucciones operativas/historial aunque DB las conserva inicialmente.

**Recomendación**: Normalizar en mapa API o usar notes de manera uniforme y migrar alias legacy explícitamente.

**Tests**: No test notas roundtrip de create/list/edit

## FE-08 — MEDIA: Reparación automática sigue escribiendo stock local en producción y anuncia corrección
Estado: CONFIRMADO POR CODIGO.

**Evidencia**
- src/lib/healthCheck.ts performAutoFix378-392 muta stock_disponible=0
- src/App.tsx HealthCheckDialog.onAutoFix2562-2585 setProducts/fixes setOrders/setProfiles sin servicio API ni guard producción
- src/components/HealthCheckDialog.tsx123-133 botón Reparación Automática

**Reproducción pendiente de ejecutar**: Con snapshot producto stock negativo diagnosticar y Reparación Automática en build productivo: writes spark-kv-inventory-products, toast reparación completada; no PUT/API autorizado y no movimiento auditado.

**Impacto**: Oculta discrepancia servidor, deja cache distinto de stock_items/DB y aparenta remedio definitivo. No prueba que stock negativo sea alcanzable por transacción normal.

**Recomendación**: Eliminar mutación browser negocio producción; diagnóstico servidor de invariantes y ajuste autorizado/auditado o mostrar reparación limitada cache explícita.

**Tests**: runtimePolicy.test.ts confirma inventory-products no es bloqueado; No test autorepair producción

## FE-09 — MEDIA: Accesorios serializados no tienen selección/validación IMEI en edición y garantía
Estado: INCONSISTENCIA UI CONFIRMADA; COMPORTAMIENTO BACKEND GARANTIA A CRUZAR.

**Evidencia**
- src/components/EditOrderDialog.tsx fetchIMEIs251, handleSubmit390-396 y selector644 se basan sólo categoria celular
- src/components/ReturnDialog.tsx handleSubmit115 y campos UI238 se basan sólo categoria celular
- src/components/NewOrderDialog.tsx selector1200 y carga529 sí soportan is_serialized

**Reproducción pendiente de ejecutar**: Producto categoria accesorio is_serialized=true vendido con serial. Editar/agregar a orden o garantía: interfaz no ofrece IMEI para accesorio, mientras NewOrder sí ofrece selección.

**Impacto**: Contrato serializado inconsistente; usuario no puede completar selección requerida desde UI, depende rechazo backend. En celulares is_serialized=false schema venta usa OR mientras selector usa?? y exige IMEI invisible.

**Recomendación**: Unificar función isSerialized por contrato servidor y soportar serial alfanumérico donde permitido en todos los flujos.

**Tests**: ReturnDialog.test.tsx sólo celular; NewOrderDialog test no serialized=false; Añadir accesorios serializados y celulares flagfalse

## FE-10 — MEDIA: Enviar fotos permite múltiples clics concurrentes; selección archivos comparte estado entre clientes
Estado: CONFIRMADO POR CODIGO.

**Evidencia**
- src/components/PhotoRequestsDashboard.tsx handleSendToCustomer117-133 setUploadingtrue
- src/components/PhotoRequestsDashboard.tsx botón285-296 no disabledUploading, mismo para Rechazar299-323
- src/components/PhotoRequestsDashboard.tsx state16-20 selectedFiles/mediaUrl global y handleOpenRequest43-57 no limpia

**Reproducción pendiente de ejecutar**: Abrir solicitud clienteA seleccionar archivos y cerrar sin subir. Abrir clienteB: mismos selectedFiles/mediaUrl presentes y botón sube a B. Doble clic Enviar genera dos POST concurrentes.

**Impacto**: Riesgo enviar foto al cliente incorrecto/duplicada; deduplicación envío backend necesita verificación separada.

**Recomendación**: Estado borrador por requestId o limpiar al cambiar/cerrar; deshabilitar acciones durante operación y exigir idempotencia envío servidor.

**Tests**: No tests dashboard ni dos clientes/tabs/submit concurrente

## FE-11 — BAJA: Hook WebSocket reconecta tras disconnect/cleanup usando token antiguo
Estado: DEFECTO LATENTE CONFIRMADO; SIN CONSUMIDOR ACTUAL.

**Evidencia**
- src/hooks/use-photo-request-websocket.ts onclose79-88 programa connect incondicional si autoReconnect;disconnect99-109 cierra socket después limpiar timer
- src/hooks/use-photo-request-websocket.ts useEffect111-121 cleanup disconnect; rg usePhotoRequestWebSocket sólo definición, ningún consumidor actual

**Reproducción pendiente de ejecutar**: Montar hook con token; disconnect/unmount -> close emite onclose asincrónico después clearTimeout; programa nuevo connect con closure token anterior.

**Impacto**: Fuga sockets y eventos luego logout si se conecta este hook. No afecta dashboard actual que usa polling; hallazgo latente.

**Recomendación**: Flag disposed/manualDisconnect y handlers nulos antes close; controlar reconexión según generación/token vigente.

**Tests**: Sin test hook; fake WebSocket cerrar/unmount/tokenchange

## Archivos leídos completos
- AGENTS.md
- src/App.tsx
- src/__tests__/App.saleCompletion.test.ts
- src/components/AIChatOrchestratorDialog.tsx
- src/components/EditOrderDialog.tsx
- src/components/HealthCheckDialog.tsx
- src/components/LoginDialog.tsx
- src/components/LoginPage.tsx
- src/components/NewOrderDialog.tsx
- src/components/NotificationCenter.tsx
- src/components/OrderCard.tsx
- src/components/PhotoRequestsDashboard.tsx
- src/components/PhotoRequestsDashboardDialog.tsx
- src/components/ReturnDialog.tsx
- src/components/TransferListDialog.tsx
- src/components/TransferStockDialog.tsx
- src/components/__tests__/NewOrderDialog.test.tsx
- src/components/__tests__/ReturnDialog.test.tsx
- src/components/__tests__/TransferListDialog.test.tsx
- src/hooks/__tests__/use-forecasting.test.ts
- src/hooks/use-ai-status.ts
- src/hooks/use-forecasting.ts
- src/hooks/use-health-check.ts
- src/hooks/use-initialize-data.ts
- src/hooks/use-keyboard-shortcuts.ts
- src/hooks/use-kv.ts
- src/hooks/use-mobile.ts
- src/hooks/use-optimization-alerts.ts
- src/hooks/use-optimization-insights.ts
- src/hooks/use-photo-request-websocket.ts
- src/hooks/use-rbac.ts
- src/hooks/use-realtime-sync.ts
- src/hooks/use-sync-detection.ts
- src/hooks/use-virtual-scroll.ts
- src/lib/__tests__/apiClient.test.ts
- src/lib/apiClient.ts
- src/lib/appViewModel.ts
- src/lib/chatOrchestrator.ts
- src/lib/config.ts
- src/lib/dataInitializer.ts
- src/lib/healthCheck.ts
- src/lib/inventoryServiceFactory.production.test.ts
- src/lib/kvStorage.ts
- src/lib/orderStatus.ts
- src/lib/orderStatusActions.ts
- src/lib/phoneValidator.ts
- src/lib/priceFormatter.ts
- src/lib/profileUtils.ts
- src/lib/runtimePolicy.test.ts
- src/lib/runtimePolicy.ts
- src/lib/utils.ts
- src/lib/validation/importProductsSchema.ts
- src/lib/validation/orderFormSchema.ts
- src/lib/validation/tradeInActivationSchema.ts
- src/lib/validation/tradeInPolicySchema.ts
- src/lib/validation/transferStockSchema.ts
- src/lib/validation/types.ts
- tests/browser/financing.spec.ts
- tests/browser/sale.spec.ts
- tests/browser/transfer-lifecycle.spec.ts
- backend/app/utils/order_financing.py

## Lecturas parciales (no equivalen a auditado completo)
- src/lib/inventoryServiceFactory.ts — 827-1138, service API wrappers and final factory (partial initial output truncated) — Rama selección producción + envoltorios críticos; no leído completo.
- src/lib/types.ts — rg notes/notas y contratos importados — Consulta puntual contratos; no lectura completa.
- backend/app/services/order_service.py — 165-360 — Cruce del contrato creación, cálculo y commit; backend integral delegado al padre.
- backend/app/routers/orders.py — 745-815, rg notes/notas — Cruce notas/recalcular total.
- backend/app/routers/stock_transfers.py — 177-187, rg dependencias/per_page — Cruce paginación y permisos.
- backend/app/routers/daily_close.py — 80-120 — Se descartó hipótesis de permiso config cierre bloqueando recepción.
- backend/app/schemas/order.py — 370-430, rg notes/notas — Cruce nombres fields.
- backend/app/routers/returns.py — rg list_returns/per_page — Consulta puntual; no auditoría función.

## No revisados
- src/ErrorFallback.tsx
- src/components/AIForecastingDialog.tsx
- src/components/AIProfileConfigDialog.tsx
- src/components/AIStatusDialog.tsx
- src/components/AIStatusWidget.tsx
- src/components/AITrainingCenter.tsx
- src/components/AdvancedSearchDialog.tsx
- src/components/BackendConnectionCheck.tsx
- src/components/ChannelHealthDialog.tsx
- src/components/CustomerHistoryDialog.tsx
- src/components/CustomerInsights.tsx
- src/components/CustomizeShortcutsDialog.tsx
- src/components/DailyCloseDialog.tsx
- src/components/DashboardStats.tsx
- src/components/EditProductDialog.tsx
- src/components/EditProfileDialog.tsx
- src/components/FinancingSettings.tsx
- src/components/ForecastingWidget.tsx
- src/components/IMEIHistoryDialog.tsx
- src/components/IMEIListDialog.tsx
- src/components/ImportProductsDialog.tsx
- src/components/KeyboardShortcutsDialog.tsx
- src/components/LocationsList.tsx
- src/components/LowStockAlert.tsx
- src/components/LowStockReportDialog.tsx
- src/components/ManageFAQsDialog.tsx
- src/components/ManageSuppliersDialog.tsx
- src/components/ManageUsersDialog.tsx
- src/components/MultiStoreControlDialog.tsx
- src/components/NewProductDialog.tsx
- src/components/NewProfileDialog.tsx
- src/components/NotificationSettingsDialog.tsx
- src/components/OptimizationInsightsDialog.tsx
- src/components/PendingTradeInsDialog.tsx
- src/components/PendingTransfersDialog.tsx
- src/components/PrintLabelsDialog.tsx
- src/components/ProductCard.tsx
- src/components/ProductIMEIRegistryDialog.tsx
- src/components/ProductLabel.tsx
- src/components/ProfileCard.tsx
- src/components/ProfileConfigPrompt.tsx
- src/components/ProfileDetailsDialog.tsx
- src/components/ProfileSettingsDialog.tsx
- src/components/ProfileSettingsSummary.tsx
- src/components/ProfileSetupGuide.tsx
- src/components/ProfilesConfigSummary.tsx
- src/components/PublicCatalog.tsx
- src/components/ReportsDialog.tsx
- src/components/RestockProductDialog.tsx
- src/components/ReturnsListDialog.tsx
- src/components/SalesHistoryDialog.tsx
- src/components/SalesProfilesList.tsx
- src/components/SettingsDialog.tsx
- src/components/StockByLocationDialog.tsx
- src/components/StockHistoryDialog.tsx
- src/components/StorageDiagnosticDialog.tsx
- src/components/SuperAdminControlPanelDialog.tsx
- src/components/SyncIndicator.tsx
- src/components/SyncSettingsDialog.tsx
- src/components/TradeInPoliciesDialog.tsx
- src/components/ValidationCodeDialog.tsx
- src/components/WarrantyCheckDialog.tsx
- src/components/__tests__/DailyCloseDialog.test.tsx
- src/components/__tests__/LoginDialog.test.tsx
- src/components/__tests__/LoginPage.test.tsx
- src/components/__tests__/SuperAdminControlPanelDialog.test.tsx
- src/components/__tests__/ValidationCodeDialog.test.tsx
- src/components/forms/RoleSelect.tsx
- src/index.css
- src/lib/__tests__/appViewModel.test.ts
- src/lib/__tests__/dataInitializer.test.ts
- src/lib/__tests__/importUtils.test.ts
- src/lib/__tests__/inventoryService.local.test.ts
- src/lib/__tests__/orderStatusActions.test.ts
- src/lib/__tests__/phoneValidator.test.ts
- src/lib/aiForecasting.ts
- src/lib/businessInsightsFallback.ts
- src/lib/exportUtils.ts
- src/lib/importUtils.ts
- src/lib/initialData.ts
- src/lib/inventoryService.ts
- src/lib/keyboardShortcuts.ts
- src/lib/kvStorage.manual.ts
- src/lib/kvStorage.test.ts
- src/lib/labelPrint.ts
- src/lib/optimizationAnalytics.ts
- src/lib/pdfExport.ts
- src/lib/reportUtils.ts
- src/lib/syncJournal.ts
- src/lib/syncService.ts
- src/lib/validation/__tests__/transferStockSchema.test.ts
- src/main.css
- src/main.tsx
- src/styles/theme.css
- src/test/msw/handlers.ts
- src/test/msw/server.ts
- src/test/setup.ts
- src/vite-end.d.ts

## Limitaciones
- No navegador/runtime ejecutado por agente
- No lint/build/tests ejecutados: padre los centraliza
- No archivos completos no revisados contados como auditados
- No garantías PostgreSQL/staging/producción inferidas del código
- Local inventoryService7343/syncService1013 no revisados por este agente; factory parcial
- No migraciones ni deploy en alcance
- Reproducciones descritas son pasos precisos derivados del código, no ejecuciones observadas

## Próximos pasos priorizados
1. Reproducir y corregir FE-01 contrato pagos/financiación con pruebas PostgreSQL+UI.
2. Idempotencia backend y cliente FE-02; atomicidad batch FE-04.
3. Aislar estado por usuario/backend/ubicación FE-05 y pruebas tabs/cambio sesión.
4. Flujos de error, paginación, notes y UI serializados FE-03/06/07/09.
5. Producción autorepair, medios por cliente y reconexión latente FE-08/10/11.
6. Completar módulos NOT REVIEWED; ejecutar gates frontend y browser centralizados por padre; no declarar producción verificada.
