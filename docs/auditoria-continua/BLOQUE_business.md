# Auditoría de negocio SoftMobile — solo lectura
Commit `dba6763391d12c6c91c9904cba36725710f9280a`; branch `main`.

Cobertura: 60 archivos leídos completos; 2 parciales. Revisión textual completa no equivale a prueba exhaustiva.

## Hallazgos

### BUS-01 — HIGH — Finalizar/cancelar/editar venta consume reserva ajena del mismo producto
Estado: REPRODUCED_SQLITE_LOGIC
Referencias: backend/app/routers/orders.py:111-141,145-193,610-631; backend/app/services/stock_transaction_helper.py:208-252; backend/app/routers/order_state_integrity.py:227-306,348-389
Evidencia: La creación pendiente ya descuenta cantidad_disponible y marca IMEI vendido. Los helpers de estado eligen primero cantidad_reservada >= item.cantidad sin identificar dueño; sólo luego consultan historial propio. Los handlers canónicos delegan en estos helpers.
Reproducción: Stock disponible=10; traslado pendiente reserva=3; crear venta cash cantidad=1 -> stock=9 reservado=3; finalizar -> stock=8 reservado=2. La venta descontó dos veces y traslado original ya no tiene reserva suficiente. Cancelar/editar pendiente también libera reserva del traslado sin reponer correctamente su venta.
Recomendación: Separar explícitamente venta ya descontada y reserva perteneciente a orden; mantener titular por movimiento/reserva y no deducir propiedad del agregado Stock.
Pruebas: Agregar regresiones API venta+traslado mismo producto para completar/cancelar/editar; conservar reserva del traslado y stock esperado. test_stock_concurrency actual sólo cubre competir por stock insuficiente, no stock sobrante+finalización.
Salida local:
```text
sale created 9 3
sale completed 8 2
```

### BUS-02 — HIGH — Recepción cero traslada todos IMEIs sin mover stock
Estado: REPRODUCED_SQLITE_LOGIC
Referencias: backend/app/routers/stock_transfers.py:419-447,514-549; backend/app/routers/stock_transfer_integrity.py:83-106
Evidencia: received_quantity=0 vacía scanned_imeis_set. La lista posterior obtiene todos seriales del transfer_id y sólo filtra si el set es truthy. Por tanto mueve todos al destino con recepción cero.
Reproducción: Transferencia serialized de 2 unidades A->B con reserva=2; confirmar received_quantity=0 e incident_notes, sin scanned_imeis. Estado confirmada, stock A=2/B=0, seriales location=B.
Recomendación: Seleccionar siempre únicamente seriales efectivamente recibidos; cero recibidos debe mover cero. Validar cantidad seriales movidos contra received_quantity.
Pruebas: Regresión API serialized received_quantity=0, 1 y total; comprobar ubicación IMEI, disponible/reservado y historial. test_stock_transfer_router_guards usa no serializados.
Salida local:
```text
transfer zero 2 0 [2, 2] source 1 dest 2
```

### BUS-03 — HIGH — Garantía permite IMEI de otro producto de la misma orden
Estado: REPRODUCED_SQLITE_LOGIC
Referencias: backend/app/services/stock_transaction_helper.py:431-470; backend/app/routers/returns.py:170-195; backend/app/routers/return_serial_integrity.py:123-164,378-394
Evidencia: El IMEI original se busca globalmente por string y sólo valida order_id/vendido. Nunca compara imei_record.product_id con product_id retornado. Wrapper canónico añade guards al reemplazo pero no al original.
Reproducción: Orden final con A y B, IMEI X de A vendido a esa orden. Solicitar warranty product_id=B quantity=1 imei=X condition=nuevo. Aceptado: stock B+1 y X de A liberado.
Recomendación: Exigir original.product_id==product_id y coherencia de ubicación y cantidad del serial antes de mutar.
Pruebas: Agregar garantía cruzada A/B misma orden: 400 y cero efectos en stocks/seriales/returns.
Salida local:
```text
cross product return accepted 1 returned product 2 imei product 1 sold False replacement None B stock 1
```

### BUS-04 — MEDIUM — Garantía serializada se cierra sin entregar reemplazo
Estado: REPRODUCED_SQLITE_LOGIC
Referencias: backend/app/schemas/returns.py:43-63; backend/app/services/stock_transaction_helper.py:473-511; backend/app/routers/returns.py:200-210
Evidencia: replacement_imei opcional; helper sólo lo valida si viene. Router sólo consume reemplazo si existe record, y rama alternativa excluye serialized. Return.status=completed aunque no hubo salida.
Reproducción: Garantía serialized correcta condition=nuevo, original imei, omitir replacement_imei -> 201; original vuelve disponible y stock+1, ninguna salida.
Recomendación: Si sólo existe warranty_exchange exigir reemplazo para serialized, o diseñar lifecycle pendiente explícito hasta entregar reemplazo.
Pruebas: Negativo API serialized omit replacement: 422/400 sin efectos; garantía válida debe tener entrada y salida.
Salida local:
```text
serialized warranty no replacement accepted 1 source stock 1
```

### BUS-05 — HIGH — Retoma sobrescribe IMEI vendido/reservado/de otra sede
Estado: REPRODUCED_SQLITE_HELPER
Referencias: backend/app/services/stock_transaction_helper.py:254-332,618-660; backend/app/services/order_service.py:257-265
Evidencia: _upsert_trade_in_imei busca cualquier serial existente sin FOR UPDATE ni guards y reescribe producto, ubicación, vendido=False, order_id=None, sold_at=None. No decrementa stock del producto/sede originales y no limpia transfer_id. Es llamado en crear orden con retoma.
Reproducción: Crear venta con trade_in.imei igual a IMEI actualmente en stock de otra sede o vendido en otra orden. El serial existente se reasigna al producto retoma/sede actual, además se suma stock de retoma. Repetir mismo IMEI en retomas puede sumar múltiples unidades para un único serial.
Recomendación: Rechazar colisión salvo lifecycle de recompra explícito que bloquee serial, verifique propietario/estado y reconcilie inventario; deduplicar payload y auditar cambio.
Pruebas: Casos existente disponible/vendido/en traslado/sede no autorizada y duplicado dentro payload; probar dos retomas simultáneas en PG.
Salida local:
```text
sold IMEI overwritten False None 2
```

### BUS-06 — HIGH — Órdenes autorizadas exponen stock y seriales de sedes ajenas
Estado: REPRODUCED_SQLITE_LOGIC
Referencias: backend/app/routers/orders.py:194-202,205-231,305-342,814-843; backend/app/routers/product_imei_integrity.py:42-59
Evidencia: Filtro RBAC sólo limita Order. Serializer de producto anidado ignora location_id recibido y llama _serialize_product(product) con accessible_location_ids=None. Ese serializer incluye stock_items de todas sedes y el wrapper IMEI también trata None como acceso global.
Reproducción: Usuario can_view A, producto P con stock A y B, orden P en A. GET orden o listado devuelve item.product.stock_items para A y B.
Recomendación: Propagar scope de usuario a todas respuestas anidadas; también revisar update_product/restock y respuestas de mutación sin scope.
Pruebas: Regresión con mismo producto en dos sedes (fixture actual usa productos distintos, por eso no detecta), verificar nested stock_items/imeis en list/get/search/mutations.
Salida local:
```text
restricted order nested locations [1, 2]
```

### BUS-07 — HIGH — POST crear negocios sin clave idempotente duplica efectos al reintentar
Estado: CONFIRMED_STATIC
Referencias: backend/app/routers/orders.py:434-446; backend/app/services/order_service.py:159-300; backend/app/routers/stock_transfers.py:61-175; backend/app/routers/returns.py:93-247; backend/app/routers/multistore_ops_integrity.py:151-167
Evidencia: Venta cash y traslado no reciben ni persisten idempotency key. Cada ejecución crea nueva entidad. Garantía no serialized parcial puede repetirse hasta agotar cantidad vendida; receipt sólo dedup si invoice_number presente. Frontend root reporta retry POST ante Failed to fetch.
Reproducción: Servidor hace commit y respuesta se pierde. Reintento mismo POST cash nonserialized con stock suficiente crea segunda orden/descuenta otra unidad; traslado reserva dos veces; garantía parcial no serialized crea segundo reemplazo.
Recomendación: Clave idempotente estable por intento de negocio y constraint DB, guardar respuesta/hash dentro misma transacción; frontend no regenerar clave en retry.
Pruebas: Pruebas respuesta perdida después commit y doble request paralelo con misma key, claves distintas y payload distinto. Confirmar línea frontend en reporte principal.

### BUS-08 — MEDIUM — Ajuste no serializado tiene dos commits y lectura de stock sin lock
Estado: CONFIRMED_STATIC
Referencias: backend/app/routers/products.py:1291-1362,721-795; backend/app/middleware/business_integrity.py:72-93
Evidencia: set_product_stock_at_location commit stock en 1334 y commit historial después en 1362. Un fallo entre ambos deja cambio sin rastro; además no SELECT FOR UPDATE. Middleware sólo bloquea serialized. PUT stock también lee sin lock aunque historia mismo commit.
Reproducción: Nonserialized ajuste: hacer fallar inserción StockHistory/segundo commit deja cantidad nueva durable. Con dos sesiones leer stock=10, venta consume 1 y commit, ajuste antiguo escribe absoluto sin lock; ledger previo/audit usa snapshot viejo.
Recomendación: Un solo transaction stock+historia+audit y bloqueo acorde Product->Stock; validar actual bajo lock y CAS cuando sea necesario.
Pruebas: Fallo inyectado segunda escritura debe rollback total; PG venta concurrente vs ajuste; no pruebas en producción.

### BUS-09 — MEDIUM — Valor de inventario suma costos/precios USD y HNL sin convertir
Estado: CONFIRMED_STATIC
Referencias: backend/app/routers/reports_final_integrity.py:212-223; backend/app/routers/reports.py:486-500; backend/app/utils/order_currency.py:57-61
Evidencia: Dashboard usa cantidad*Product.costo/precio crudo; resumen sede usa cantidad*Product.precio crudo. Los productos aceptan moneda USD y órdenes guardan HNL mediante conversion helper. Totales agregados mezclan unidades monetarias.
Reproducción: P USD costo=100 qty=1 y Q HNL costo=100 qty=1; dashboard inventory_value=200 aunque con tasa25 el valor HNL es2600.
Recomendación: Definir moneda/base/tasa de valoración de inventario y convertir consistentemente; snapshot tasa o documentar valoración actual.
Pruebas: Regresión dos monedas reconciliar dashboard/resumen contable, tasa explícita; actuales tests location usan sólo HNL.

### BUS-10 — MEDIUM — Venta commit antes de auditoría permite transacción durable sin audit y respuesta 500
Estado: CONFIRMED_STATIC
Referencias: backend/app/services/order_service.py:284-290; backend/app/routers/orders.py:443-446
Evidencia: OrderService hace commit de negocio y luego router llama log_audit_event y hace segundo commit. Un fallo en audit no puede revertir venta ya durable, viola atomicidad de operación sensible.
Reproducción: Inyectar fallo en log_audit_event/insert AuditLog después create_order: orden+stock ya persistidos, audit ausente y response failure puede gatillar retry BUS-07.
Recomendación: Transaction owner único en API; flush service y commit venta+audit una vez.
Pruebas: Regresión fallo audit exige cero orden/stock/IMEI efectos; respuesta perdida después commit probar idempotencia.

## Hipótesis pendientes

- BUS-H01: Ventas multi-producto bloquean en orden del payload (STATIC_CONCURRENCY_HYPOTHESIS). prepare_sale_items adquiere Product->Stock para cada item antes de avanzar, sin ordenar conjunto global. Requests [A,B] vs [B,A] pueden ciclo Product/Stock. No reproducido PostgreSQL. Siguiente: Dos ventas PG con barrera tras primer Product/Stock lock, timeout; comprobar una transacción deadlock y rollback completo.

- BUS-H02: Cambio is_serialized puede desactivar enforcement con seriales existentes (BUSINESS_POLICY_NEEDS_CONFIRMATION). Permite flag False sin reconciliar ProductIMEI/stock/transfers. _validate_imeis retorna [] al ser no serialized; venta deja seriales disponibles. Necesita acordar si toggle operativo permitido. Siguiente: Producto con IMEI disponible -> flag false -> venta sin IMEI -> flag true; verificar mismatch y aprobar regla comercial.

- BUS-H03: Cierre por sede toma cuatro consultas sin snapshot o bloqueo de ventas (STATIC_CONCURRENCY_HYPOTHESIS). cash/transfer/card/financing esperan desde queries separadas en READ COMMITTED. Venta finaliza entre métodos -> cierre mezcla snapshots; único cierre/día dificulta corrección. No PG reproducido. Siguiente: Finalización de pago mixto entre consultas, transacción consistente e inmutabilidad de cierre revisadas.

- BUS-H04: Conteo serializado incluye defectuosos y excluye reservas traslado del expected (STATIC_LOGIC_HYPOTHESIS). Conteo calcula expected por vendido=False y transfer_id=None, no excluye cuarentena. Stale compara available agregado contra expected, así transferencias pendientes pueden impedir aprobación aun sin cambio; defecto retornado puede contar como vendible. No reproducido. Siguiente: Conteo con serial defectuoso y transferencias pendientes; verificar scope físico vs stock disponible y reservado.

## Verificación y límites
- No production tests or runtime data accessed.
- No PostgreSQL concurrency tests run by this worker.
- Full text review means entire source read; does not imply all branches or database constraints dynamically exercised.
- Models rbac/system and identity/migration implementation are owned by other audit block; schemas location and stock_history not reviewed here.
- Exact executed inline reproductions appeared in tool transcript; setup used PYTHONDONTWRITEBYTECODE=1, local dummy DATABASE_URL pointing 127.0.0.1:1, separate sqlite:///:memory: engine. No persistent database written.

## Archivos y blobs
|Archivo|Estado|Líneas|Blob SHA|
|---|---|---:|---|
|AGENTS.md|FULL_TEXT_REVIEWED|165|e8682d75bd19dce994ff80f901087031f43d94fd|
|backend/app/routers/customers.py|FULL_TEXT_REVIEWED|274|fe00629fbe3dcf5be37ce53783e0778b1e97d3da|
|backend/app/routers/financing.py|FULL_TEXT_REVIEWED|182|0d6a1b6a865c0327998aefe3606c7e41594687bd|
|backend/app/routers/daily_close.py|FULL_TEXT_REVIEWED|307|09621f651abcc5af628624f1014c307a2481f40b|
|backend/app/utils/location_access.py|FULL_TEXT_REVIEWED|67|d984fc75d401a2f987197c516d13176ec03259bb|
|backend/app/routers/returns.py|FULL_TEXT_REVIEWED|256|627e6b49d977fb93421b35772a9ddf1f43f42af0|
|backend/app/routers/return_serial_integrity.py|FULL_TEXT_REVIEWED|394|4c931ed900246bba568c27c24014ede4d10580e2|
|backend/app/services/stock_transaction_helper.py|FULL_TEXT_REVIEWED|700|af8ddd486908e163be001d83ae5d3bea531d5b6e|
|backend/app/utils/order_integrity.py|FULL_TEXT_REVIEWED|207|432bc92e515262a8083ab98d8e87c0a38ca7fb19|
|backend/app/schemas/returns.py|FULL_TEXT_REVIEWED|121|1b2902520ee151a834ea8ffe0058468d3dbc8c51|
|backend/app/models/order.py|FULL_TEXT_REVIEWED|188|9c78d84c8c049948ba20adb1bafc5f5cef78ab5d|
|backend/app/utils/order_validators.py|FULL_TEXT_REVIEWED|119|c65e29f215325fa3742f254cbaacf5fe10ccabc3|
|backend/app/services/order_service.py|FULL_TEXT_REVIEWED|525|ddcd006ac839590e4ac6e2fdcad667543a059898|
|backend/app/routers/order_state_integrity.py|FULL_TEXT_REVIEWED|389|b333b62c9b2b494d772ccb5af58a603606052899|
|backend/app/utils/stock_manager.py|FULL_TEXT_REVIEWED|947|f061cf5bf503e0eb6b249ecaba07416005acb905|
|backend/app/routers/locations.py|FULL_TEXT_REVIEWED|309|a2d9404c3032394d076b9e131590eb2bf92620d5|
|backend/app/routers/suppliers.py|FULL_TEXT_REVIEWED|342|0a880111315cccf66ff6bd01cfc54d0facdc54f0|
|backend/app/routers/stock_history.py|FULL_TEXT_REVIEWED|248|c9df2dfb4faaa162951d0361b27265b30d0ed141|
|backend/app/routers/product_imei_integrity.py|FULL_TEXT_REVIEWED|103|e4ed597d3f3e60228e318cbc143e49aa4d771bb7|
|backend/app/routers/stock_transfer_integrity.py|FULL_TEXT_REVIEWED|180|856fc2b15eae08cfe86d5294b17f8be324e30592|
|backend/app/routers/imeis.py|FULL_TEXT_REVIEWED|430|720cb69252d9b93d04481c0bb4c3ec7875d88cc5|
|backend/app/utils/order_financing.py|FULL_TEXT_REVIEWED|237|74485865512e04c44dd6b5d94a2714191a79af95|
|backend/app/utils/order_currency.py|FULL_TEXT_REVIEWED|68|17a8a70af60c0df28af819d6a1df7f0b893a6bdf|
|backend/app/utils/order_tradeins.py|FULL_TEXT_REVIEWED|16|9ab315095ce492c18d1d58abbacef6ab0a89af93|
|backend/app/utils/order_queries.py|FULL_TEXT_REVIEWED|35|51b15288df693c12c48ba85604279c1bf92216fa|
|backend/app/routers/multistore_integrity.py|FULL_TEXT_REVIEWED|128|884c4b00b9c4c3a5e8073cc8fd9be14eb5275526|
|backend/app/routers/multistore_ops_integrity.py|FULL_TEXT_REVIEWED|418|1825cccbf050b578d8b2f8b0e840d52895dbcc3f|
|backend/app/routers/multistore_control.py|FULL_TEXT_REVIEWED|663|bc9c5477d281aee9dcf35513e265e363184583e1|
|backend/app/routers/orders.py|FULL_TEXT_REVIEWED|1183|749ffad0154ff7d3e1bf2c64947d797330d4ae3f|
|backend/app/routers/integrity_overrides.py|FULL_TEXT_REVIEWED|164|66227ddf016bf88b4f29d7296f9bc12ca49ebcb3|
|backend/app/middleware/business_integrity.py|FULL_TEXT_REVIEWED|141|5195244b79399bbd2664ca06e9a2e48b70c60032|
|backend/app/routers/stock_transfers.py|FULL_TEXT_REVIEWED|750|5483f6f0c9bfafc4eadcfdaad2960a343e93eb7e|
|backend/app/routers/products.py|FULL_TEXT_REVIEWED|1468|11af807da8c2f279ee7823df780b1fc865cb2507|
|backend/tests/conftest.py|FULL_TEXT_REVIEWED|6|65b4f2a737a62a1235bcd3070bac6431eb389994|
|backend/tests/test_return_serial_integrity.py|FULL_TEXT_REVIEWED|343|1692211f27da89c1f3dee612a809570c14d914b2|
|backend/tests/test_final_financial_and_order_concurrency.py|FULL_TEXT_REVIEWED|264|01934d5a67910260a8b12fd6c5f6111284f0acb3|
|backend/conftest.py|FULL_TEXT_REVIEWED|183|7428846797bf071b144623521d4d820a0a490bdc|
|backend/app/models/product.py|FULL_TEXT_REVIEWED|204|a56d57b09cf422f5b081df872abfa002c4bcac3a|
|backend/app/models/control.py|FULL_TEXT_REVIEWED|176|a0a87ff837e361452596587cf52d224037d51ca5|
|backend/app/utils/order_pricing.py|FULL_TEXT_REVIEWED|246|4b115657819b513e41a90a9feeae9877f34a4219|
|backend/app/utils/order_item_currency_integrity.py|FULL_TEXT_REVIEWED|157|373ca9675327e4f9805c6b9236174df942e133a8|
|backend/app/routers/reports_final_integrity.py|FULL_TEXT_REVIEWED|470|47626e5fa5253d1449381f3016835cdfdcf497bf|
|backend/app/schemas/control.py|FULL_TEXT_REVIEWED|173|5c83bdd2f6e5e16702839dc14e279cf4005cb9f3|
|backend/app/models/finance.py|FULL_TEXT_REVIEWED|47|68fda676ec42a63dd29ebc7a9924a07e318983cb|
|backend/app/models/location.py|FULL_TEXT_REVIEWED|131|67242fd093db7ccb243d7be2493fef8d79b91098|
|backend/app/routers/reports_integrity.py|FULL_TEXT_REVIEWED|660|dcc90917aae77ec1998ea562a007158a76fc1f7a|
|backend/app/routers/reports.py|FULL_TEXT_REVIEWED|708|8e7f2cf597ecf4e9569d6377260db9b4a1542947|
|backend/app/routers/order_search_integrity.py|FULL_TEXT_REVIEWED|107|859c2b78d580cc5242da6714a60c6ecebaa08f40|
|backend/app/routers/product_search_integrity.py|FULL_TEXT_REVIEWED|100|5f03ce8d716263f599f344f48765857e596d23e4|
|backend/app/schemas/product.py|FULL_TEXT_REVIEWED|184|4fbfb25614b7f5299ee016e0a47d139c239a8829|
|backend/app/schemas/finance.py|FULL_TEXT_REVIEWED|121|bebe67dd75d7fb3ee35624d312a8398ca27aa774|
|backend/app/schemas/imei.py|FULL_TEXT_REVIEWED|58|68e4d7c94c3500c03648002d3678bb0c38491c10|
|backend/app/schemas/daily_close.py|FULL_TEXT_REVIEWED|52|20ebfdbf25ad634ea67c14a51e126240d183f035|
|backend/app/schemas/order_secure.py|FULL_TEXT_REVIEWED|39|5d62b341022fc9b1e2c9eca3deb4062a8ee94131|
|backend/tests/test_stock_transfer_router_guards.py|FULL_TEXT_REVIEWED|194|424fe960144959a252a1dd5528307826a9cdf372|
|backend/tests/test_return_promotion_integrity.py|FULL_TEXT_REVIEWED|176|f64a6a0cc4684af0e2149fb10e268e5405679021|
|backend/tests/test_location_access_filters.py|FULL_TEXT_REVIEWED|409|8116a03b8d539f6973cd8dae2b7888961ac08728|
|backend/tests/test_stock_transaction_helper_concurrency.py|FULL_TEXT_REVIEWED|267|cca06ee3fb289ef398e79d47e81bdfddff266f67|
|backend/tests/test_stock_concurrency.py|FULL_TEXT_REVIEWED|292|4373c301ac4cccd1e0ff12c70955aa638cbe5486|
|backend/app/schemas/order.py|FULL_TEXT_REVIEWED|594|15571e91b774c8e6c4555bb66c7ad48d915366ed|
|backend/app/database.py|PARTIAL_REVIEWED|53|a187fdb02c8fcfe09f5f34f87b4694b53ae0e34b|
|backend/app/main.py|PARTIAL_REVIEWED|429|2fbf087ff76a25a067db330de75d3e925957fb68|

## Plan priorizado
1. TDD regressions BUS-01/02/03/05/06 first on isolated PostgreSQL.
2. Agree return lifecycle BUS-04 and serialization-toggle rule.
3. Implement business idempotency and single transaction owner before enabling POST retries.
4. Then fix audit atomicity, manual adjustment locking, currency valuation; broaden PG locks and staging E2E.
5. Preserve no-production-testing constraint and no fixes until entire audit accepted.
