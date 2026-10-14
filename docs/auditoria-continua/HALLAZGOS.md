# Hallazgos vigentes

110 entradas provisionales:34HIGH,63MEDIUM,12LOW,1INFORMATIONAL. Fallos, riesgos, pruebas, docs y local están clasificados; no equivale a110 vulnerabilidades explotadas distintas. Registro íntegro en HALLAZGOS.json.

## BUS-01 — Finalizar/cancelar/editar venta consume reserva ajena del mismo producto

Gravedad: HIGH. Estado: REPRODUCED_SQLITE_LOGIC. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/routers/orders.py:111-141,145-193,610-631', 'backend/app/services/stock_transaction_helper.py:208-252', 'backend/app/routers/order_state_integrity.py:227-306,348-389']; ['_release_pending_order_reservations', 'persist_prepared_sale_items', 'update_order_status_canonical']

Evidencia concreta: La creación pendiente ya descuenta cantidad_disponible y marca IMEI vendido. Los helpers de estado eligen primero cantidad_reservada >= item.cantidad sin identificar dueño; sólo luego consultan historial propio. Los handlers canónicos delegan en estos helpers.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Stock disponible=10; traslado pendiente reserva=3; crear venta cash cantidad=1 -> stock=9 reservado=3; finalizar -> stock=8 reservado=2. La venta descontó dos veces y traslado original ya no tiene reserva suficiente. Cancelar/editar pendiente también libera reserva del traslado sin reponer correctamente su venta.

Corrección recomendada: Separar explícitamente venta ya descontada y reserva perteneciente a orden; mantener titular por movimiento/reserva y no deducir propiedad del agregado Stock.

Pruebas: Agregar regresiones API venta+traslado mismo producto para completar/cancelar/editar; conservar reserva del traslado y stock esperado. test_stock_concurrency actual sólo cubre competir por stock insuficiente, no stock sobrante+finalización.

Fuente: BLOQUE_business.json

## BUS-02 — Recepción cero traslada todos IMEIs sin mover stock

Gravedad: HIGH. Estado: REPRODUCED_SQLITE_LOGIC. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/routers/stock_transfers.py:419-447,514-549', 'backend/app/routers/stock_transfer_integrity.py:83-106']; ['confirm_transfer', 'confirm_transfer_integrity']

Evidencia concreta: received_quantity=0 vacía scanned_imeis_set. La lista posterior obtiene todos seriales del transfer_id y sólo filtra si el set es truthy. Por tanto mueve todos al destino con recepción cero.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Transferencia serialized de 2 unidades A->B con reserva=2; confirmar received_quantity=0 e incident_notes, sin scanned_imeis. Estado confirmada, stock A=2/B=0, seriales location=B.

Corrección recomendada: Seleccionar siempre únicamente seriales efectivamente recibidos; cero recibidos debe mover cero. Validar cantidad seriales movidos contra received_quantity.

Pruebas: Regresión API serialized received_quantity=0, 1 y total; comprobar ubicación IMEI, disponible/reservado y historial. test_stock_transfer_router_guards usa no serializados.

Fuente: BLOQUE_business.json

## BUS-03 — Garantía permite IMEI de otro producto de la misma orden

Gravedad: HIGH. Estado: REPRODUCED_SQLITE_LOGIC. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/services/stock_transaction_helper.py:431-470', 'backend/app/routers/returns.py:170-195', 'backend/app/routers/return_serial_integrity.py:123-164,378-394']; ['_prepare_return_items_integrity', 'create_return', 'prepare_return_items']

Evidencia concreta: El IMEI original se busca globalmente por string y sólo valida order_id/vendido. Nunca compara imei_record.product_id con product_id retornado. Wrapper canónico añade guards al reemplazo pero no al original.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Orden final con A y B, IMEI X de A vendido a esa orden. Solicitar warranty product_id=B quantity=1 imei=X condition=nuevo. Aceptado: stock B+1 y X de A liberado.

Corrección recomendada: Exigir original.product_id==product_id y coherencia de ubicación y cantidad del serial antes de mutar.

Pruebas: Agregar garantía cruzada A/B misma orden: 400 y cero efectos en stocks/seriales/returns.

Fuente: BLOQUE_business.json

## BUS-04 — Garantía serializada se cierra sin entregar reemplazo

Gravedad: MEDIUM. Estado: REPRODUCED_SQLITE_LOGIC. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/schemas/returns.py:43-63', 'backend/app/services/stock_transaction_helper.py:473-511', 'backend/app/routers/returns.py:200-210']; ['create_return', 'prepare_return_items']

Evidencia concreta: replacement_imei opcional; helper sólo lo valida si viene. Router sólo consume reemplazo si existe record, y rama alternativa excluye serialized. Return.status=completed aunque no hubo salida.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Garantía serialized correcta condition=nuevo, original imei, omitir replacement_imei -> 201; original vuelve disponible y stock+1, ninguna salida.

Corrección recomendada: Si sólo existe warranty_exchange exigir reemplazo para serialized, o diseñar lifecycle pendiente explícito hasta entregar reemplazo.

Pruebas: Negativo API serialized omit replacement: 422/400 sin efectos; garantía válida debe tener entrada y salida.

Fuente: BLOQUE_business.json

## BUS-05 — Retoma sobrescribe IMEI vendido/reservado/de otra sede

Gravedad: HIGH. Estado: REPRODUCED_SQLITE_HELPER. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/services/stock_transaction_helper.py:254-332,618-660', 'backend/app/services/order_service.py:257-265']; ['create_order', 'process_trade_ins']

Evidencia concreta: _upsert_trade_in_imei busca cualquier serial existente sin FOR UPDATE ni guards y reescribe producto, ubicación, vendido=False, order_id=None, sold_at=None. No decrementa stock del producto/sede originales y no limpia transfer_id. Es llamado en crear orden con retoma.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Crear venta con trade_in.imei igual a IMEI actualmente en stock de otra sede o vendido en otra orden. El serial existente se reasigna al producto retoma/sede actual, además se suma stock de retoma. Repetir mismo IMEI en retomas puede sumar múltiples unidades para un único serial.

Corrección recomendada: Rechazar colisión salvo lifecycle de recompra explícito que bloquee serial, verifique propietario/estado y reconcilie inventario; deduplicar payload y auditar cambio.

Pruebas: Casos existente disponible/vendido/en traslado/sede no autorizada y duplicado dentro payload; probar dos retomas simultáneas en PG.

Fuente: BLOQUE_business.json

## BUS-06 — Órdenes autorizadas exponen stock y seriales de sedes ajenas

Gravedad: HIGH. Estado: REPRODUCED_SQLITE_LOGIC. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/routers/orders.py:194-202,205-231,305-342,814-843', 'backend/app/routers/product_imei_integrity.py:42-59']; ['_serialize_product_for_order', '_serialize_product_integrity']

Evidencia concreta: Filtro RBAC sólo limita Order. Serializer de producto anidado ignora location_id recibido y llama _serialize_product(product) con accessible_location_ids=None. Ese serializer incluye stock_items de todas sedes y el wrapper IMEI también trata None como acceso global.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Usuario can_view A, producto P con stock A y B, orden P en A. GET orden o listado devuelve item.product.stock_items para A y B.

Corrección recomendada: Propagar scope de usuario a todas respuestas anidadas; también revisar update_product/restock y respuestas de mutación sin scope.

Pruebas: Regresión con mismo producto en dos sedes (fixture actual usa productos distintos, por eso no detecta), verificar nested stock_items/imeis en list/get/search/mutations.

Fuente: BLOQUE_business.json

## BUS-07 — POST crear negocios sin clave idempotente duplica efectos al reintentar

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/orders.py:434-446', 'backend/app/services/order_service.py:159-300', 'backend/app/routers/stock_transfers.py:61-175', 'backend/app/routers/returns.py:93-247', 'backend/app/routers/multistore_ops_integrity.py:151-167']; ['create_order', 'create_purchase_receipt_integrity', 'create_transfer']

Evidencia concreta: Venta cash y traslado no reciben ni persisten idempotency key. Cada ejecución crea nueva entidad. Garantía no serialized parcial puede repetirse hasta agotar cantidad vendida; receipt sólo dedup si invoice_number presente. Frontend root reporta retry POST ante Failed to fetch.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Servidor hace commit y respuesta se pierde. Reintento mismo POST cash nonserialized con stock suficiente crea segunda orden/descuenta otra unidad; traslado reserva dos veces; garantía parcial no serialized crea segundo reemplazo.

Corrección recomendada: Clave idempotente estable por intento de negocio y constraint DB, guardar respuesta/hash dentro misma transacción; frontend no regenerar clave en retry.

Pruebas: Pruebas respuesta perdida después commit y doble request paralelo con misma key, claves distintas y payload distinto. Confirmar línea frontend en reporte principal.

Fuente: BLOQUE_business.json

## BUS-08 — Ajuste no serializado tiene dos commits y lectura de stock sin lock

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/products.py:1291-1362,721-795', 'backend/app/middleware/business_integrity.py:72-93']; ['dispatch', 'set_product_stock_at_location']

Evidencia concreta: set_product_stock_at_location commit stock en 1334 y commit historial después en 1362. Un fallo entre ambos deja cambio sin rastro; además no SELECT FOR UPDATE. Middleware sólo bloquea serialized. PUT stock también lee sin lock aunque historia mismo commit.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Nonserialized ajuste: hacer fallar inserción StockHistory/segundo commit deja cantidad nueva durable. Con dos sesiones leer stock=10, venta consume 1 y commit, ajuste antiguo escribe absoluto sin lock; ledger previo/audit usa snapshot viejo.

Corrección recomendada: Un solo transaction stock+historia+audit y bloqueo acorde Product->Stock; validar actual bajo lock y CAS cuando sea necesario.

Pruebas: Fallo inyectado segunda escritura debe rollback total; PG venta concurrente vs ajuste; no pruebas en producción.

Fuente: BLOQUE_business.json

## BUS-09 — Valor de inventario suma costos/precios USD y HNL sin convertir

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/reports_final_integrity.py:212-223', 'backend/app/routers/reports.py:486-500', 'backend/app/utils/order_currency.py:57-61']; ['get_dashboard_stats_final', 'get_stock_summary_by_location', 'product_amount_in_hnl']

Evidencia concreta: Dashboard usa cantidad*Product.costo/precio crudo; resumen sede usa cantidad*Product.precio crudo. Los productos aceptan moneda USD y órdenes guardan HNL mediante conversion helper. Totales agregados mezclan unidades monetarias.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: P USD costo=100 qty=1 y Q HNL costo=100 qty=1; dashboard inventory_value=200 aunque con tasa25 el valor HNL es2600.

Corrección recomendada: Definir moneda/base/tasa de valoración de inventario y convertir consistentemente; snapshot tasa o documentar valoración actual.

Pruebas: Regresión dos monedas reconciliar dashboard/resumen contable, tasa explícita; actuales tests location usan sólo HNL.

Fuente: BLOQUE_business.json

## BUS-10 — Venta commit antes de auditoría permite transacción durable sin audit y respuesta 500

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/services/order_service.py:284-290', 'backend/app/routers/orders.py:443-446']; ['create_order']

Evidencia concreta: OrderService hace commit de negocio y luego router llama log_audit_event y hace segundo commit. Un fallo en audit no puede revertir venta ya durable, viola atomicidad de operación sensible.

Impacto: Consultar evidencia y explicación del bloque; requiere validación del alcance real antes de corregir.

Reproducción: Inyectar fallo en log_audit_event/insert AuditLog después create_order: orden+stock ya persistidos, audit ausente y response failure puede gatillar retry BUS-07.

Corrección recomendada: Transaction owner único en API; flush service y commit venta+audit una vez.

Pruebas: Regresión fallo audit exige cero orden/stock/IMEI efectos; respuesta perdida después commit probar idempotencia.

Fuente: BLOQUE_business.json

## OPS-01 — Backup automático Compose escribe fuera del volumen persistente

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['deploy/docker-compose.prod.yml:73-77', 'deploy/.env.prod.example:44', 'deploy/prepare-prod-env.sh:297', 'deploy/backup-postgres.sh:5,11,17-20']; backup service / backup loop

Evidencia concreta: Env compartido BACKUP_DIR=/app/backups; backup sólo monta backend_backups:/backups. Script respeta BACKUP_DIR. Offsite y healthcheck leen /backups.

Impacto: Dumps diarios quedan en filesystem efímero del container, no se replican; al recrear backup se pierden. Gate espera backups que no aparecen.

Reproducción: Preparar env estándar y resolver configuración de backup: destino efectivo /app/backups no es mount /backups. No Docker real ejecutado.

Corrección recomendada: Override environment BACKUP_DIR=/backups en servicio backup; probar dump sintético por stack y persistencia tras recreación.

Pruebas: Los cinco shell tests pasan porque no comprueban wiring env+volume.

Fuente: BLOQUE_deploy.json

## OPS-02 — Healthcheck operativo exige una ruta que nginx bloquea

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['deploy/ops-healthcheck.sh:66', 'deploy/nginx.conf:28-30', 'deploy/release-now.sh:100']; ops-healthcheck step 2

Evidencia concreta: curl -fsS http://127.0.0.1:${frontend_port}/api/metrics versus location = /api/metrics return 404. set -e aborta.

Impacto: Release y healthcheck fallan incluso con backend saludable, antes de verificar backups/provenance.

Reproducción: Comparación exacta de ruta y server config; no HTTP producción ejecutado.

Corrección recomendada: Consultar métricas desde backend dentro de red Docker; mantener bloqueo público y añadir integration test del nginx real.

Pruebas: test-ops-healthcheck-timeout sustituye curl por éxito incondicional, oculta conflicto.

Fuente: BLOQUE_deploy.json

## OPS-03 — Backup VPS anuncia éxito aunque pg_dump falle

Gravedad: HIGH. Estado: REPRODUCED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/backup_database.sh:105-121,183-192']; create_backup/main

Evidencia concreta: create_backup se evalúa como condición if: Bash desactiva errexit dentro de función. pipeline pg_dump exit42 seguido gzip es fallido pero se ignora, se crea sidecar y último log retorna0.

Impacto: Backups SQL vacíos/incompletos certificados por checksum, falsa señal de recuperación, además se borran backups antiguos.

Reproducción: pg_dump sintético exit42 en PATH y BACKUP_DIR temporal. Exit script0; SQL descomprimido0 bytes; .sha256 existe; SUCCESS. Evidencia /tmp/audit-deploy-backup-repro.json.

Corrección recomendada: Validar pipeline explícitamente con if ! ...; escribir temporal, comprobar SQL no vacío/gzip, publicar atómicamente sólo tras éxito; no ejecutar retención tras fallo.

Pruebas: Reproducción fresca ejecutada; no DB ni backups reales.

Fuente: BLOQUE_deploy.json

## OPS-04 — Migración monetaria SQLite bloquea arranque por parámetros Decimal

Gravedad: HIGH. Estado: REPRODUCED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/utils/pricing_policy_migration.py:215-217,225-232', 'backend/app/main.py:100-103']; run_pricing_policy_migration

Evidencia concreta: SQL text sin tipo enlaza decimal.Decimal a sqlite3, que rechaza binding.

Impacto: Actualización legado SQLite con órdenes USD falla startup, no sirve tráfico.

Reproducción: DB in-memory con ai_profile_configs/products/orders/order_items, producto100USD, orden100. ProgrammingError Error binding parameter1 type decimal.Decimal not supported; /tmp/audit-pricing-repro.py + /tmp/audit-deploy-pricing-repro.json.

Corrección recomendada: Usar parámetros tipados Numeric compatibles o serialización decimal exacta para SQLite, añadir prueba SQLite de migración monetaria.

Pruebas: Repro venv exact requirements, Python3.12; tests actuales monetarios usan fixture PostgreSQL.

Fuente: BLOQUE_deploy.json

## OPS-05 — Bootstrap VPS nuevo no genera SETUP_TOKEN obligatorio

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['deploy/vps/install-vps.sh:302-353,365-371', 'backend/app/config.py:129-132']; write_env/init_database

Evidencia concreta: Here-doc backend/.env no contiene SETUP_TOKEN; Settings en production exige al menos32 caracteres. init_db importa app.database/settings.

Impacto: Instalación nueva falla inicialización/arranque pese a documentación de instalador completo.

Reproducción: Ejecutar Settings con variables del here-doc y sin token: guard producción rechaza. No instalador real ejecutado.

Corrección recomendada: Generar token seguro en bootstrap y documentar uso inicial, probar import config con env generado sintético.

Pruebas: test-install-vps-db-preservation cubre reejecución, no config bootstrap nuevo.

Fuente: BLOQUE_deploy.json

## OPS-06 — Ruta env relativa recomendada se invalida al cambiar directorio en release

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['deploy/release-now.sh:8,95-97', 'deploy/README.md:159', 'deploy/ops-healthcheck.sh:8,45', 'deploy/backup-now.sh:6', 'deploy/restore-backup.sh:6']; release-now deployment step

Evidencia concreta: ENV_FILE conserva ./deploy/.env.prod; validadores realpath sólo en procesos hijos. Después cd deploy docker --env-file ./deploy/.env.prod busca deploy/deploy/.env.prod. PROD_ENV_FILE relativa también se resuelve respecto de compose.

Impacto: Comando de lanzamiento documentado falla después de gates costosos; otros entrypoints relativos pueden fallar Compose.

Reproducción: Desde raíz release-now ./deploy/.env.prod; seguir resolución cwd antes/después cd, sin desplegar.

Corrección recomendada: Normalizar ENV_FILE a ruta absoluta tras validar existencia en todos entrypoints. Añadir fake docker que verifica paths.

Pruebas: prepare env test cubre validate-prod normalization, no parent release.

Fuente: BLOQUE_deploy.json

## OPS-07 — Restore no reemplaza BD existente y no es atómico

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['deploy/restore-backup.sh:26-41', 'deploy/backup-now.sh:22-24', 'deploy/backup-postgres.sh:24-30']; restore-backup

Evidencia concreta: Dumps plain pg_dump sin --clean; restore psql ON_ERROR_STOP sin single transaction ni target limpio. En schema existente primer CREATE falla; comandos previos a cualquier fallo quedan commit.

Impacto: Procedimiento documentado como sobrescritura no restaura instancia existente; fallo en DB vacía puede dejar esquema parcialmente restaurado.

Reproducción: Backup generado contiene CREATE TABLE; destino con tabla homónima produce already exists, ON_ERROR_STOP corta. No restore real autorizado/ejecutado.

Corrección recomendada: Procedimiento explícito restauración a nueva BD limpia con verificación y switch; exigir checksum de archivo actual por hash, transacción donde viable; mantenimiento previo y rollback documentado.

Pruebas: DR usa container PostgreSQL limpio; no prueba restore-backup existente.

Fuente: BLOQUE_deploy.json

## OPS-08 — --truncate migra después de confirmar truncado en transacción separada

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/migrate_sqlite_to_postgres.py:124-132,254-255,270-280']; main/_truncate_tables

Evidencia concreta: TRUNCATE ... CASCADE se commit en _truncate_tables antes de iniciar copia target_engine.begin. Si faltan campos/falla FK/copia, rollback sólo revierte inserciones, destino anterior queda vacío.

Impacto: Fallo migración con reemplazo autorizado pierde datos anteriores del destino y cascadas dependientes; sólo existe backup SQLite fuente.

Reproducción: Destino con datos, --truncate, fuente sin campo obligatorio: _required_target_columns... falla después del commit truncate. No truncate real ejecutado.

Corrección recomendada: Preflight completo antes de borrar; integrar truncate+insert en misma transacción, backup del destino y reparar sequences antes de publicar éxito.

Pruebas: test_sqlite_to_postgres_migration.py sólo helpers SQLite; no fallo de copia tras truncate PostgreSQL.

Fuente: BLOQUE_deploy.json

## OPS-09 — Utilidad demo de credenciales elimina otras configuraciones del perfil

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/seed_channel_credentials.py:31-51,183-196,239-244']; _parse_profile_config/populate_credentials/clear_credentials

Evidencia concreta: Cuando JSON incluye channel_integrations dict, parser devuelve únicamente ese campo; populate y clear pretenden preservar otros campos pero trabajan con objeto recortado. Config {exchange_rate:24.5,channel_integrations:{...}} pierde exchange_rate; --clear devuelve None.

Impacto: Operador que ejecuta utilidad sobre perfiles existentes pierde tipo de cambio y otras políticas de negocio/configuración. No es ejecutada por startup/deploy canonical.

Reproducción: Trazado estático de dict input con exchange_rate e integrations por parser; no utilidad ni DB real ejecutadas.

Corrección recomendada: Preservar copia completa del dict y normalizar sólo channel_integrations; rechazar producción para demo; tests para preservar configuraciones con --populate/--clear.

Pruebas: Lectura completa; sin ejecución según ampliación sólo lectura.

Fuente: BLOQUE_deploy.json

## FE-01 — Pagos mixtos con tarjeta calculan/importan totales incompatibles con backend

Gravedad: HIGH. Estado: FRONTEND_CONTRACT_REJECTED_BY_BACKEND_GUARD. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/NewOrderDialog.tsx getOrderFinancials 590-642: recargo cardBaseAmount * tasa; total neto + ese recargo', 'src/components/NewOrderDialog.tsx handleSubmit 750-767,820-833: método principal = mayor importe; financing_data prima independiente', 'backend/app/utils/order_financing.py compute_financing_from_payload 102-150: rechaza efectivo/transferencia con financing_data y calcula recargo sobre total neto-prima', 'backend/app/order_integrity.py before_flush valida suma del desglose contra total; reproducción aislada HTTP400 y rollback deja cero órdenes.']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/components/NewOrderDialog.tsx getOrderFinancials 590-642: recargo cardBaseAmount * tasa; total neto + ese recargo', 'src/components/NewOrderDialog.tsx handleSubmit 750-767,820-833: método principal = mayor importe; financing_data prima independiente', 'backend/app/utils/order_financing.py compute_financing_from_payload 102-150: rechaza efectivo/transferencia con financing_data y calcula recargo sobre total neto-prima', 'backend/app/utils/order_integrity.py before_flush valida suma del desglose contra total; reproducción aislada HTTP400 y rollback deja cero órdenes.']

Impacto: Bloquea venta mixta por contrato inconsistente; la modalidad de financiación puede perder su enum. El guard ORM rechaza el desglose inconsistente antes del commit; no se confirmó corrupción persistida.

Reproducción: Neto1000, tasa5%, efectivo600 tarjeta400 prima0: UI1020; payload metodo efectivo + financing_data ->400. Efectivo400 tarjeta600 prima0: UI1030; backend total1050 y breakdown1030. Para extrafinanciamiento con monto tarjeta1000, plazo6 tasa10% y tarjeta normal5%: UI1100 pero breakdown1050 y método tarjeta (no financiamiento).

Corrección recomendada: Definir un contrato único de base tarjeta/financiamiento; mantener modalidad elegida y conciliar pagos con el guard servidor existente.

Pruebas: ['NewOrderDialog.test.tsx sólo nombre faltante', 'tests/browser/financing.spec.ts sólo alta banco, ninguna venta financiada', 'Añadir UI+PostgreSQL cash/card, transfer/card, financiación, prima, tasa0 y redondeos']

Fuente: BLOQUE_frontend.json

## FE-02 — Reintentos automáticos repiten mutaciones no idempotentes

Gravedad: HIGH. Estado: CONFIRMED_STATIC_CLIENT_RETRY_AND_BACKEND_NO_IDEMPOTENCY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/apiClient.ts request 338-401: retries=3 para cualquier method, UUID nuevo por intento, Failed to fetch reintenta', 'src/lib/apiClient.ts createOrder 1203-1206, createStockTransfer1315-1321, restockProduct1079-1085: POST mediante request', 'backend/app/services/order_service.py create_order 284: commit antes de entregar respuesta']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/lib/apiClient.ts request 338-401: retries=3 para cualquier method, UUID nuevo por intento, Failed to fetch reintenta', 'src/lib/apiClient.ts createOrder 1203-1206, createStockTransfer1315-1321, restockProduct1079-1085: POST mediante request', 'backend/app/services/order_service.py create_order 284: commit antes de entregar respuesta']

Impacto: Cliente puede duplicar venta, stock o traslado por fallo de respuesta; consumos con IMEI/referencia únicos podrían fallar en vez de duplicar, sin resolver incertidumbre del usuario.

Reproducción: POST venta accesorio efectivo con stock>=2. Backend confirma commit; perder/resetear respuesta al cliente para que fetch rechace Failed to fetch. Cliente envía el mismo cuerpo otra vez con X-Request-ID diferente.

Corrección recomendada: Reintentar sólo lecturas seguras mientras no exista idempotencia servidor; para mutaciones usar clave estable de operación persistida y respuesta deduplicada transaccional.

Pruebas: ['apiClient.test.ts no cubre fallo red después commit ni reintentos POST', 'Necesario backend+cliente con pérdida respuesta tras commit']

Fuente: BLOQUE_frontend.json

## FE-03 — Venta rechazada cierra y borra el formulario como si hubiese terminado

Gravedad: MEDIUM. Estado: CONFIRMADO POR CODIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/App.tsx NewOrderDialog.onSubmit 2429-2432 captura sin relanzar', 'src/components/NewOrderDialog.tsx handleSubmit 813-837 await onSubmit y cierra; resetForm207-245 al cerrar']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/App.tsx NewOrderDialog.onSubmit 2429-2432 captura sin relanzar', 'src/components/NewOrderDialog.tsx handleSubmit 813-837 await onSubmit y cierra; resetForm207-245 al cerrar']

Impacto: Usuario pierde entrada y puede confundir fallo con éxito. Si POST guarda pero GET products falla, también informa Error al crear orden aunque ya fue creada.

Reproducción: Completar venta válida en UI, responder400 (stock cambiado, referencia repetida, límite precio) al POST. App muestra toast error pero resuelve Promise; diálogo llama onOpenChange(false) y borra cliente/items.

Corrección recomendada: Propagar error de creación; separar persistencia confirmada de refresco fallido, mantener formulario cuando creación no confirmada.

Pruebas: ['NewOrderDialog.test.tsx no prueba rechazo onSubmit', 'App.saleCompletion.test.ts inspección texto, no integración submit']

Fuente: BLOQUE_frontend.json

## FE-04 — Traslado multi-modelo anunciado como una operación deja resultado parcial y repetir duplica líneas

Gravedad: HIGH. Estado: CONFIRMADO POR CODIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/TransferStockDialog.tsx handleSubmit 313-333: for POSTs individuales, catch conserva todas las líneas', 'src/components/TransferStockDialog.tsx DialogDescription346-347 dice mover varios modelos en una sola operación']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/components/TransferStockDialog.tsx handleSubmit 313-333: for POSTs individuales, catch conserva todas las líneas', 'src/components/TransferStockDialog.tsx DialogDescription346-347 dice mover varios modelos en una sola operación']

Impacto: Incumple atomicidad comercial; reserva/despacha A aunque lote no terminó, segunda ejecución puede duplicar A. No se reportan IDs exitosos ni refresca stock en fallo.

Reproducción: Dos accesorios A y B en traslado. POST A201; POST B409 por stock concurrente o500. A ya pendiente en servidor, UI sólo error y sigue con A/B. Volver Registrar repite POST A antes de B.

Corrección recomendada: Endpoint batch con transacción única; mientras se implemente, mostrar y conservar progreso por línea, no reenviar exitosas, reconciliar antes de reintentar.

Pruebas: ['Sin test TransferStockDialog', 'E2E transfer-lifecycle.spec.ts sólo un accesorio; agregar lote+fallo línea2']

Fuente: BLOQUE_frontend.json

## FE-05 — Caché global de negocio permite mezclar datos de usuarios/ubicaciones entre sesiones y pestañas

Gravedad: HIGH. Estado: CONFIRMADO POR CODIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/App.tsx MainApp84-89 usa useKV inventory-products/orders/profiles/locations sin user/backend namespace', 'src/App.tsx logout269-275 elimina auth pero no datasets ni dataLoaded', 'src/App.tsx loadData381-434 no invalida previos al nuevo usuario, sin cancelación/respuesta guard; catch mantiene data y marca loaded', 'src/hooks/use-kv.ts load+storage73-88 lee mismas claves; src/lib/kvStorage.ts prefix spark-kv sin usuario', 'src/lib/apiClient.ts token283-299 queda en memoria; no evento storage auth']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/App.tsx MainApp84-89 usa useKV inventory-products/orders/profiles/locations sin user/backend namespace', 'src/App.tsx logout269-275 elimina auth pero no datasets ni dataLoaded', 'src/App.tsx loadData381-434 no invalida previos al nuevo usuario, sin cancelación/respuesta guard; catch mantiene data y marca loaded', 'src/hooks/use-kv.ts load+storage73-88 lee mismas claves; src/lib/kvStorage.ts prefix spark-kv sin usuario', 'src/lib/apiClient.ts token283-299 queda en memoria; no evento storage auth']

Impacto: Exposición de clientes/ventas/stock fuera del alcance sesión actual, transitoria o hasta recarga exitosa; servidor no autoriza estos datos leídos desde navegador.

Reproducción: A ubicación1 carga datos; logout e ingresar B con orders:view ubicación2; bloquear GET de carga B: siguen orders A y dataLoaded true. Dos pestañas mantienen token en memoria distinto tras login/logout global y datasets de una se propagan por storage a otra.

Corrección recomendada: Estado negocio sólo en memoria o caché segregada por backend+usuario+alcance; limpiar/invalidate al logout/auth cambio, cancelar solicitudes antiguas y sincronizar auth entre tabs.

Pruebas: ['No tests App aislamiento sesión/tab', 'Añadir dos usuarios ubicaciones disjuntas, carga fallida y responses fuera de orden']

Fuente: BLOQUE_frontend.json

## FE-06 — Lista transferencias corta silenciosamente a la primera página de50

Gravedad: MEDIUM. Estado: CONFIRMADO POR CODIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/apiClient.ts listStockTransfers1326-1356 sólo una request sin page/per_page y descarta total/pages', 'backend/app/routers/stock_transfers.py list_transfers184-185 defaults page1 per_page50', 'src/components/TransferListDialog.tsx loadTransfers69-79 filtra ubicación local;291-293 estados locales']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/lib/apiClient.ts listStockTransfers1326-1356 sólo una request sin page/per_page y descarta total/pages', 'backend/app/routers/stock_transfers.py list_transfers184-185 defaults page1 per_page50', 'src/components/TransferListDialog.tsx loadTransfers69-79 filtra ubicación local;291-293 estados locales']

Impacto: Oculta recepciones pendientes e inventario en tránsito; contadores e historial falsos.

Reproducción: 51+ transferencias visibles, transferencia pendiente antigua fuera primera50. Abrir En tránsito puede mostrar ninguna aunque servidor tiene pendientes en página2. Filtro ubicación se aplica después del corte.

Corrección recomendada: Paginar todas o implementar paginación UI con filtros estado/ubicación enviados servidor y total visible.

Pruebas: ['apiClient tests paginan users/roles/permissions pero no stock-transfers', 'TransferList test usa array2; agregar51+ y pendiente página2']

Fuente: BLOQUE_frontend.json

## FE-07 — Notas API desaparecen de tarjeta y editor por notes/notas

Gravedad: MEDIUM. Estado: CONFIRMADO POR CODIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/schemas/order.py OrderResponse369: notes; routers/orders.py serialize260: notes=order.notes', 'src/lib/apiClient.ts mapApiOrder302-335 spread API sin asignación notas', 'src/components/OrderCard.tsx 226-230 sólo order.notas; EditOrderDialog.tsx81,193 inicia order.notas']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['backend/app/schemas/order.py OrderResponse369: notes; routers/orders.py serialize260: notes=order.notes', 'src/lib/apiClient.ts mapApiOrder302-335 spread API sin asignación notas', 'src/components/OrderCard.tsx 226-230 sólo order.notas; EditOrderDialog.tsx81,193 inicia order.notas']

Impacto: Se pierden visualmente instrucciones operativas/historial aunque DB las conserva inicialmente.

Reproducción: Crear orden con notes=instrucciones entrega. API responde notes; tarjeta no muestra texto y editor abre vacío. Escribir nueva nota guarda reemplazo sin exponer anterior.

Corrección recomendada: Normalizar en mapa API o usar notes de manera uniforme y migrar alias legacy explícitamente.

Pruebas: ['No test notas roundtrip de create/list/edit']

Fuente: BLOQUE_frontend.json

## FE-08 — Reparación automática sigue escribiendo stock local en producción y anuncia corrección

Gravedad: MEDIUM. Estado: CONFIRMADO POR CODIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/healthCheck.ts performAutoFix378-392 muta stock_disponible=0', 'src/App.tsx HealthCheckDialog.onAutoFix2562-2585 setProducts/fixes setOrders/setProfiles sin servicio API ni guard producción', 'src/components/HealthCheckDialog.tsx123-133 botón Reparación Automática']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/lib/healthCheck.ts performAutoFix378-392 muta stock_disponible=0', 'src/App.tsx HealthCheckDialog.onAutoFix2562-2585 setProducts/fixes setOrders/setProfiles sin servicio API ni guard producción', 'src/components/HealthCheckDialog.tsx123-133 botón Reparación Automática']

Impacto: Oculta discrepancia servidor, deja cache distinto de stock_items/DB y aparenta remedio definitivo. No prueba que stock negativo sea alcanzable por transacción normal.

Reproducción: Con snapshot producto stock negativo diagnosticar y Reparación Automática en build productivo: writes spark-kv-inventory-products, toast reparación completada; no PUT/API autorizado y no movimiento auditado.

Corrección recomendada: Eliminar mutación browser negocio producción; diagnóstico servidor de invariantes y ajuste autorizado/auditado o mostrar reparación limitada cache explícita.

Pruebas: ['runtimePolicy.test.ts confirma inventory-products no es bloqueado', 'No test autorepair producción']

Fuente: BLOQUE_frontend.json

## FE-09 — Accesorios serializados no tienen selección/validación IMEI en edición y garantía

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_UI_SERIAL_CONTRACT. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/EditOrderDialog.tsx fetchIMEIs251, handleSubmit390-396 y selector644 se basan sólo categoria celular', 'src/components/ReturnDialog.tsx handleSubmit115 y campos UI238 se basan sólo categoria celular', 'src/components/NewOrderDialog.tsx selector1200 y carga529 sí soportan is_serialized']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/components/EditOrderDialog.tsx fetchIMEIs251, handleSubmit390-396 y selector644 se basan sólo categoria celular', 'src/components/ReturnDialog.tsx handleSubmit115 y campos UI238 se basan sólo categoria celular', 'src/components/NewOrderDialog.tsx selector1200 y carga529 sí soportan is_serialized']

Impacto: Contrato serializado inconsistente; usuario no puede completar selección requerida desde UI, depende rechazo backend. En celulares is_serialized=false schema venta usa OR mientras selector usa?? y exige IMEI invisible.

Reproducción: Producto categoria accesorio is_serialized=true vendido con serial. Editar/agregar a orden o garantía: interfaz no ofrece IMEI para accesorio, mientras NewOrder sí ofrece selección.

Corrección recomendada: Unificar función isSerialized por contrato servidor y soportar serial alfanumérico donde permitido en todos los flujos.

Pruebas: ['ReturnDialog.test.tsx sólo celular', 'NewOrderDialog test no serialized=false', 'Añadir accesorios serializados y celulares flagfalse']

Fuente: BLOQUE_frontend.json

## FE-10 — Enviar fotos permite múltiples clics concurrentes; selección archivos comparte estado entre clientes

Gravedad: MEDIUM. Estado: CONFIRMADO POR CODIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/PhotoRequestsDashboard.tsx handleSendToCustomer117-133 setUploadingtrue', 'src/components/PhotoRequestsDashboard.tsx botón285-296 no disabledUploading, mismo para Rechazar299-323', 'src/components/PhotoRequestsDashboard.tsx state16-20 selectedFiles/mediaUrl global y handleOpenRequest43-57 no limpia']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/components/PhotoRequestsDashboard.tsx handleSendToCustomer117-133 setUploadingtrue', 'src/components/PhotoRequestsDashboard.tsx botón285-296 no disabledUploading, mismo para Rechazar299-323', 'src/components/PhotoRequestsDashboard.tsx state16-20 selectedFiles/mediaUrl global y handleOpenRequest43-57 no limpia']

Impacto: Riesgo enviar foto al cliente incorrecto/duplicada; deduplicación envío backend necesita verificación separada.

Reproducción: Abrir solicitud clienteA seleccionar archivos y cerrar sin subir. Abrir clienteB: mismos selectedFiles/mediaUrl presentes y botón sube a B. Doble clic Enviar genera dos POST concurrentes.

Corrección recomendada: Estado borrador por requestId o limpiar al cambiar/cerrar; deshabilitar acciones durante operación y exigir idempotencia envío servidor.

Pruebas: ['No tests dashboard ni dos clientes/tabs/submit concurrente']

Fuente: BLOQUE_frontend.json

## FE-11 — Hook WebSocket reconecta tras disconnect/cleanup usando token antiguo

Gravedad: LOW. Estado: DEFECTO LATENTE CONFIRMADO; SIN CONSUMIDOR ACTUAL. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/hooks/use-photo-request-websocket.ts onclose79-88 programa connect incondicional si autoReconnect;disconnect99-110 cierra socket después limpiar timer', 'src/hooks/use-photo-request-websocket.ts useEffect111-121 cleanup disconnect; rg usePhotoRequestWebSocket sólo definición, ningún consumidor actual']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/hooks/use-photo-request-websocket.ts onclose79-88 programa connect incondicional si autoReconnect;disconnect99-110 cierra socket después limpiar timer', 'src/hooks/use-photo-request-websocket.ts useEffect111-121 cleanup disconnect; rg usePhotoRequestWebSocket sólo definición, ningún consumidor actual']

Impacto: Fuga sockets y eventos luego logout si se conecta este hook. No afecta dashboard actual que usa polling; hallazgo latente.

Reproducción: Montar hook con token; disconnect/unmount -> close emite onclose asincrónico después clearTimeout; programa nuevo connect con closure token anterior.

Corrección recomendada: Flag disposed/manualDisconnect y handlers nulos antes close; controlar reconexión según generación/token vigente.

Pruebas: ['Sin test hook; fake WebSocket cerrar/unmount/tokenchange']

Fuente: BLOQUE_frontend.json

## SEC-AI-001 — JWT sin permiso IA accede a conversaciones e inventario global

Gravedad: HIGH. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/ai_intelligence.py:444-459 acepta cualquier usuario activo', 'backend/app/routers/ai_slug_integrity.py:56-72 delega context sin autorización adicional', 'backend/app/routers/ai_intelligence.py:1111-1149 selecciona cliente por teléfono suministrado; 1176-1304 stock sin scope; 1400-1403 historial sin perfil; 1490-1522 devuelve memoria e historial']; ['_canonicalize_slug', '_require_ai_integration_auth', 'get_ai_context']

Evidencia concreta: ['backend/app/routers/ai_intelligence.py:444-459 acepta cualquier usuario activo', 'backend/app/routers/ai_slug_integrity.py:56-72 delega context sin autorización adicional', 'backend/app/routers/ai_intelligence.py:1111-1149 selecciona cliente por teléfono suministrado; 1176-1304 stock sin scope; 1400-1403 historial sin perfil; 1490-1522 devuelve memoria e historial']

Impacto: Exposición de conversaciones, memoria de clientes e inventario de otras sedes a usuarios sin permiso IA; validar alcance con JWT real.

Reproducción: Usuario Invitado activo, o usuario limitado a tienda A, POST /api/ai/context con slug válido y teléfono de cliente B. Obtiene previous_context, ai_memory, admin_phone e inventario exacto de otras ubicaciones; no requiere OpenAI.

Corrección recomendada: Separar credencial de integración acotada por perfil/canal de JWT staff; exigir permiso IA y acceso cliente/perfil/ubicación. Filtrar todos los recuperadores y limitar datos de respuesta.

Pruebas: ['Negativos Invitado sin ai:manage, usuario scope A frente B, teléfono ajeno y perfil diferente; verificar 403 y no mutaciones.']

Fuente: BLOQUE_security-ai.json

## SEC-AI-002 — Creación de ventas por IA omite orders:create

Gravedad: HIGH. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/ai_intelligence.py:2223-2229 depende solo _require_ai_integration_auth', 'backend/app/routers/ai_intelligence.py:2146-2197 solo valida ubicación para JWT', 'backend/app/services/order_service.py:159-245 no verifica permiso orders:create', 'backend/app/utils/location_access.py:7-28 permite todas ubicaciones a roles sistema sin filas explícitas']; ['_create_order_from_ai_payload', '_is_privileged_role_without_scope', 'create_order']

Evidencia concreta: ['backend/app/routers/ai_intelligence.py:2223-2229 depende solo _require_ai_integration_auth', 'backend/app/routers/ai_intelligence.py:2146-2197 solo valida ubicación para JWT', 'backend/app/services/order_service.py:159-245 no verifica permiso orders:create', 'backend/app/utils/location_access.py:7-28 permite todas ubicaciones a roles sistema sin filas explícitas']

Impacto: La IA puede crear una venta sin el permiso comercial exigido a un operador, alterando inventario y cifras fuera de la autorización esperada.

Reproducción: JWT Invitado activo sin orders:create y sin filas UserLocationAccess; POST /api/ai/create-order con perfil válido, ubicación e item con stock no serializado. Pasa RBAC y llega a venta/stock. Incluso cuenta sin rol con can_edit explícito pasa.

Corrección recomendada: Para JWT exigir orders:create además de can_edit; para servicio acotar perfiles y ubicaciones autorizadas. Aplicar el mismo guard a order_intent de handle-message.

Pruebas: ['Prueba DB PostgreSQL con Invitado y stock: 403, stock/órdenes inmutables; mismo caso vía order_intent.']

Fuente: BLOQUE_security-ai.json

## SEC-AI-003 — Respuesta duplicada puede pertenecer a otro cliente

Gravedad: HIGH. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/ai_intelligence.py:2245-2269 latest_assistant filtra sales_profile_id y role, no customer_id ni message_id']; ['handle_message_without_n8n']

Evidencia concreta: ['backend/app/routers/ai_intelligence.py:2245-2269 latest_assistant filtra sales_profile_id y role, no customer_id ni message_id']

Impacto: Un cliente puede recibir una respuesta almacenada para otro, con fuga de contexto y atención equivocada.

Reproducción: Procesar mensaje A con ID M; luego cliente B genera última respuesta en mismo perfil; reintentar M como A. reply devuelve contenido de B. Puede provocarse con payload message_id arbitrario conocido.

Corrección recomendada: Persistir respuesta vinculada a clave mensaje/canal/cuenta/cliente y devolver solo esa respuesta; jamás fallback al último assistant del perfil.

Pruebas: ['Dos clientes intercalados y retries; assert reply de A y ausencia texto de B. test_ai_workflow.py:481-512 solo cubre mismo cliente.']

Fuente: BLOQUE_security-ai.json

## SEC-AI-004 — Pronóstico rápido evade restricción por ubicación

Gravedad: HIGH. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/forecasting.py:14-28 recibe location_id libre y no usa current_user para scope', 'backend/app/services/forecasting_service.py:26-29 location_id sustituye scope; 64-106 stock/ventas se consultan globalmente si omitido']; ['generate_sales_forecasts', 'get_forecasts']

Evidencia concreta: ['backend/app/routers/forecasting.py:14-28 recibe location_id libre y no usa current_user para scope', 'backend/app/services/forecasting_service.py:26-29 location_id sustituye scope; 64-106 stock/ventas se consultan globalmente si omitido']

Impacto: Usuarios restringidos pueden obtener pronósticos/inventario de otras sedes mediante el endpoint rápido.

Reproducción: Usuario reports:view limitado a A solicita /api/forecasting/predict?location_id=B o sin filtro; obtiene stock exacto y demanda de B/global.

Corrección recomendada: Alinear con analytics/forecast: validar ubicación y require_location_access, aplicar location_ids accesibles por defecto.

Pruebas: ['Usuario scoped A: B 403; sin filtro solo A; no filas acceso retorna vacío para roles custom.']

Fuente: BLOQUE_security-ai.json

## CH-001 — Corrección de webhook no cubre idempotencia del endpoint IA ni limpieza compartida

Gravedad: HIGH. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/channel_webhook_integrity.py:34-99,360-470 recupera pending_delivery y release de fallos', 'backend/app/routers/ai_intelligence.py:493-530 elimina todo registro expirado y commit previo a procesamiento', 'backend/app/routers/ai_intelligence.py:2245-2269 no libera reclamo ante fallo posterior']; ['_claim_message', '_cleanup_processed_messages', 'handle_message_without_n8n']

Evidencia concreta: ['backend/app/routers/channel_webhook_integrity.py:34-99,360-470 recupera pending_delivery y release de fallos', 'backend/app/routers/ai_intelligence.py:493-530 elimina todo registro expirado y commit previo a procesamiento', 'backend/app/routers/ai_intelligence.py:2245-2269 no libera reclamo ante fallo posterior']

Impacto: Reintentos o limpieza de mensajes pueden repetir efectos comerciales o perder recuperabilidad del envío.

Reproducción: A) /api/ai/handle-message con message_id: fallo get_ai_context/OpenAI/order y retry: duplicate-guard sin completar efecto. B) insertar pending_delivery/manual_recovery expirado; cualquier handle-message nuevo con ID ejecuta cleanup y borra respuesta de recuperación; retry webhook vuelve a IA.

Corrección recomendada: Unificar protocolo de deduplicación y limpieza; preservar estados ambiguos/delivery pendientes en TODOS consumidores. Persistir estado/resultado y decidir recovery antes de replay.

Pruebas: ['PostgreSQL fallo antes/después de side effects + retry IA; fila pending_delivery/manual_recovery expirada sobrevive limpieza IA; retry no repite órdenes/fotos.']

Fuente: BLOQUE_security-ai.json

## CH-005 — n8n sigue con contrato training inválido y sin entrega Meta

Gravedad: MEDIUM. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['docs/n8n/whatsapp_ai_flow.json: nodo Enviar a Cola POST /api/ai/training-queue con sales_profile_id/question/original_answer', 'backend/app/routers/ai_intelligence.py:1681-1698 ruta POST real /training/submit; 1721-1725 training-queue solo GET', 'docs/n8n/whatsapp_ai_flow.json: Responder WhatsApp es respondToWebhook, no nodo Meta Graph', 'docs/INTEGRACION_N8N.md: contratos contradictorios context/log/training']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['docs/n8n/whatsapp_ai_flow.json: nodo Enviar a Cola POST /api/ai/training-queue con sales_profile_id/question/original_answer', 'backend/app/routers/ai_intelligence.py:1681-1698 ruta POST real /training/submit; 1721-1725 training-queue solo GET', 'docs/n8n/whatsapp_ai_flow.json: Responder WhatsApp es respondToWebhook, no nodo Meta Graph', 'docs/INTEGRACION_N8N.md: contratos contradictorios context/log/training']

Impacto: El flujo n8n versionado no acredita entrenamiento ni respuesta entregada al cliente real.

Reproducción: Importar plantilla; rama entrenamiento llama método inexistente (405); response webhook por sí misma no envía mensaje Graph. No se verificó ejecución n8n ni puente externo que transforme respuesta.

Corrección recomendada: Definir ruta oficial nativa vs puente n8n, corregir endpoint/esquema y referencia datos del webhook tras HTTP request; añadir envío real o documentar adaptador.

Pruebas: ['Staging sin clientes reales: contrato entrada-context-reply-training-entrega y retry; verificar nodo Meta simulado.']

Fuente: BLOQUE_security-ai.json

## CH-006 — Clave deduplicación global sin cuenta/canal/cliente

Gravedad: MEDIUM. Estado: RIESGO DE DISEÑO CONFIRMADO; COLISIÓN REAL NO VERIFICADA. Evidencia: RISK_PENDING_VERIFICATION.

Archivo/función: ['backend/app/models/ai.py:102-106 message_id unique global', 'backend/app/routers/channel_webhook_integrity.py:71-81 lookup solo ID', 'backend/app/routers/channel_webhook_integrity.py:277-321 cached_delivery_context y envío usan event.channel/customer_id sin cotejar claim.customer_phone/channel']; ['_claim_message', '_prepare_incoming_event']

Evidencia concreta: ['backend/app/models/ai.py:102-106 message_id unique global', 'backend/app/routers/channel_webhook_integrity.py:71-81 lookup solo ID', 'backend/app/routers/channel_webhook_integrity.py:277-321 cached_delivery_context y envío usan event.channel/customer_id sin cotejar claim.customer_phone/channel']

Impacto: Identificadores coincidentes entre cuentas/canales pueden suprimir mensajes legítimos o reutilizar respuesta ajena.

Reproducción: Colisión ID en dos canales/cuentas: segundo mensaje se omite; si primero pending_delivery, segunda entrega puede reutilizar su respuesta al recipient del segundo evento. Factibilidad de colisión real Meta no demostrada; API IA permite IDs libres.

Corrección recomendada: Clave compuesta canal/cuenta/message_id, enlazar recipient/profile inmutable y validar reintento. Separar namespace IDs IA/nativos.

Pruebas: ['Mismo ID distintos canales/cuentas/customer: no omisión ni reenvío cruzado.']

Fuente: BLOQUE_security-ai.json

## PHOTO-001 — Fotos ignoran canal de origen persistido

Gravedad: MEDIUM. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/photo_requests.py:147 guarda origin_channel', 'backend/app/routers/photo_requests.py:245-256 resolver usa notas/primer canal y omite origin_channel', 'backend/app/routers/channel_webhook_integrity.py:259-266 construye payload sin channel_hint', 'backend/app/routers/ai_intelligence.py:2283-2297 infiere primer canal perfil para solicitud']; ['_mark_delivered', '_resolve_request_channel', 'create_photo_request_internal', 'handle_message_without_n8n']

Evidencia concreta: ['backend/app/routers/photo_requests.py:147 guarda origin_channel', 'backend/app/routers/photo_requests.py:245-256 resolver usa notas/primer canal y omite origin_channel', 'backend/app/routers/channel_webhook_integrity.py:259-266 construye payload sin channel_hint', 'backend/app/routers/ai_intelligence.py:2283-2297 infiere primer canal perfil para solicitud']

Impacto: Fotos solicitadas por un canal pueden enviarse por otro y no llegar al cliente que las pidió.

Reproducción: Perfil canales [whatsapp,instagram], solicitud origin_channel=instagram sin notas especiales: envío selecciona whatsapp. En webhook Instagram la IA también infiere WhatsApp.

Corrección recomendada: Propagar canal/cuenta reales desde IncomingEvent y resolver primero origin_channel validado; conservar account context para entrega.

Pruebas: ['Perfil multicanal: solicitudes IG/Messenger salen por canal/cuenta originales.']

Fuente: BLOQUE_security-ai.json

## PHOTO-002 — Envío de lote de fotos no es reintentable sin duplicados

Gravedad: MEDIUM. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/photo_requests.py:690-695 selecciona media sin lock', 'backend/app/routers/photo_requests.py:734-757 y 775-795 envía media secuencial y caption', 'backend/app/routers/photo_requests.py:804-826 marca todos después de todas entregas']; ['_send_whatsapp_media_items', 'send_photos_to_customer']

Evidencia concreta: ['backend/app/routers/photo_requests.py:690-695 selecciona media sin lock', 'backend/app/routers/photo_requests.py:734-757 y 775-795 envía media secuencial y caption', 'backend/app/routers/photo_requests.py:804-826 marca todos después de todas entregas']

Impacto: Un fallo después de envíos parciales hace que reintentar duplique fotos ya aceptadas por el proveedor.

Reproducción: Dos media: primera aceptada, segunda/caption falla. Todas quedan unsent; retry reenvía primera. Dos llamadas concurrentes ven mismo lote y entregan dos veces.

Corrección recomendada: Reclamo transaccional/outbox por media y guardar ID/estado de entrega inmediatamente; cuarentena de resultados ambiguos, concurrencia e idempotencia.

Pruebas: ['Mock Meta acepta media1 y falla media2/caption; retry solo pendiente. Dos solicitudes concurrentes PostgreSQL no duplican.']

Fuente: BLOQUE_security-ai.json

## AN-001 — Analytics y forecast usan fecha creación en lugar de fecha venta

Gravedad: MEDIUM. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/analytics.py:92-114 usa Order.created_at y <= last_month_end (date a medianoche)', 'backend/app/services/forecasting_service.py:110-125 usa Order.created_at', 'backend/app/routers/ai_business_integrity.py:101-112 usa effective_sale_column, contraparte ya canónica']; ['generate_business_insights_integrity', 'generate_sales_forecasts', 'get_dashboard_stats']

Evidencia concreta: ['backend/app/routers/analytics.py:92-114 usa Order.created_at y <= last_month_end (date a medianoche)', 'backend/app/services/forecasting_service.py:110-125 usa Order.created_at', 'backend/app/routers/ai_business_integrity.py:101-112 usa effective_sale_column, contraparte ya canónica']

Impacto: Ventas se asignan al período de creación y sesgan cierre mensual, demanda y pronóstico.

Reproducción: Orden pendiente creada hace 2 meses y completada hoy: no computa venta actual en analytics/forecast. Venta último día mes a 12:00 queda fuera revenue_last_month.

Corrección recomendada: Usar effective_sale_column/at, ventanas [inicio, siguiente_inicio) y acordar moneda/refunds con reportes canónicos.

Pruebas: ['Venta validada posterior creación; último día mes mediodía y límite siguiente mes; reconciliación con reportes.']

Fuente: BLOQUE_security-ai.json

## AN-002 — Cache forecast ignora parámetros y caducidad

Gravedad: MEDIUM. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/routers/analytics.py:149-162 cacheable no considera days_history ni limit y retorna summary tal cual', 'backend/app/routers/analytics.py:177-183 cache almacena resultado ya truncado', 'backend/app/jobs/forecasting_job.py:32-40 precalcula 90 días sin metadato days_history']; ['generate_forecast', 'start_forecasting_job']

Evidencia concreta: ['backend/app/routers/analytics.py:149-162 cacheable no considera days_history ni limit y retorna summary tal cual', 'backend/app/routers/analytics.py:177-183 cache almacena resultado ya truncado', 'backend/app/jobs/forecasting_job.py:32-40 precalcula 90 días sin metadato days_history']

Impacto: Parámetros de pronóstico diferentes pueden recibir el mismo resultado obsoleto y orientar compras incorrectas.

Reproducción: Consulta history60 limit1 precarga cache; siguiente history365 limit200 devuelve summary limit1/history60. Sin scheduler, cache permanece hasta restart o force_refresh.

Corrección recomendada: Clave por filtros/history/scope, cache objeto completo y aplicar limit por solicitud, TTL explícito.

Pruebas: ['Requests history/limit distintos devuelven datos propios; avance reloj invalida cache.']

Fuente: BLOQUE_security-ai.json

## AUTH-001 — Cambiar contraseña no invalida JWT anterior

Gravedad: MEDIUM. Estado: CONFIRMADO POR CÓDIGO. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/app/auth.py:44-87 JWT valida sub/exp y usuario activo', 'backend/app/routers/auth_router.py:453-454 y 580-581 cambia hash sin token version']; ['update_user_me']

Evidencia concreta: ['backend/app/auth.py:44-87 JWT valida sub/exp y usuario activo', 'backend/app/routers/auth_router.py:453-454 y 580-581 cambia hash sin token version']

Impacto: Una sesión/token previamente sustraído puede seguir accediendo después del cambio de contraseña hasta su caducidad.

Reproducción: Token robado válido; usuario/admin cambia contraseña; JWT anterior sigue autorizado hasta exp. Si username antiguo se reutiliza en otra cuenta, sub puede apuntar a nueva identidad.

Corrección recomendada: JWT con subject ID estable y token_version/password_changed_at; revocar sesiones tras cambio/reset contraseña.

Pruebas: ['Token anterior rechazado tras reset; reutilizar username no migra identidad.']

Fuente: BLOQUE_security-ai.json

## T01 — El único E2E PostgreSQL acepta competidor 500/503 como éxito de control de concurrencia; no comprueba ausencia de orden, items, pagos o ledger parcial del perdedor.

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_TEST_GAP. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['tests/e2e/test_postgres_runtime_e2e.py:219-230']; ['test_postgres_real_auth_readiness_and_stock_concurrency']

Evidencia concreta: ['tests/e2e/test_postgres_runtime_e2e.py:219-230']

Impacto: Un gate puede aprobar concurrencia con fallo interno y efectos parciales del competidor sin detectar inconsistencia.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Exigir estado de conflicto esperado 400/409 y mensaje, exactamente una orden e items/IMEI/stock/historial coherentes; forzar solapamiento con barrera.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_tests.json

## T02 — NewOrderDialog solo comprueba nombre vacío; tests de App son inspección textual y no ejecutan App. No verifican venta real serializada, pagos múltiples, financiamiento, selección localización, error/reintento ni estados UI al fallar API.

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_TEST_GAP. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/__tests__/NewOrderDialog.test.tsx:26-45', 'src/__tests__/App.saleCompletion.test.ts:1-26']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/components/__tests__/NewOrderDialog.test.tsx:26-45', 'src/__tests__/App.saleCompletion.test.ts:1-26']

Impacto: No se detectan regresiones de venta serializada, pagos/financiación o formulario perdido por probar sólo nombre faltante y texto de App.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Añadir tests montaje con MSW y browser PostgreSQL para venta completa y error, verificando payload y persistencia final.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_tests.json

## T03 — Suite de migración SQLite->PostgreSQL utiliza SQLite como target en todos los casos; no verifica conversión PG, secuencias, constraints ni rollback de migración completa.

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_TEST_GAP. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/tests/test_sqlite_to_postgres_migration.py:14-99']; ['test_copy_uses_real_legacy_columns_and_allows_new_nullable_fields']

Evidencia concreta: ['backend/tests/test_sqlite_to_postgres_migration.py:14-99']

Impacto: Una migración puede aprobar tests SQLite y fallar con secuencias, constraints y tipos de PostgreSQL real.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Añadir CLI completo sobre SQLite legacy y schema PG aislado con datos representativos, referencias, inserción posterior, fallo intermedio y rollback.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_tests.json

## T04 — test_transfer_reservation_blocks_concurrent_order usa barrier.wait y join sin timeout; workers no capturan errores inesperados. Un worker caído y otro ok puede satisfacer asserts generales; deadlock puede colgar gate.

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_TEST_GAP. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/tests/test_stock_concurrency.py:85-169']; ['test_transfer_reservation_blocks_concurrent_order']

Evidencia concreta: ['backend/tests/test_stock_concurrency.py:85-169']

Impacto: Un bloqueo o worker fallido puede dejar CI colgado o resultados incompletos sin probar conservación de stock.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Timeouts de barrera, lock_timeout/statement_timeout PostgreSQL, errores compartidos, join acotado y comprobar dos outcomes con conflicto exacto.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_tests.json

## T05 — E2E PG usa DATABASE_URL recibido sin aislamiento ni guardia de DB descartable. Hace setup inicial y escrituras; solo verifica prefijo postgresql.

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_TEST_GAP. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['tests/e2e/test_postgres_runtime_e2e.py:40-51', 'tests/e2e/test_postgres_runtime_e2e.py:103-194']; ['_setup_admin', '_start_backend']

Evidencia concreta: ['tests/e2e/test_postgres_runtime_e2e.py:40-51', 'tests/e2e/test_postgres_runtime_e2e.py:103-194']

Impacto: Si DATABASE_URL apunta al negocio por error, el E2E hace escrituras contra ese destino porque no exige base descartable.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Crear schema/test database único mediante helper y cleanup; rechazar explícitamente DSN no destinado a pruebas.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_tests.json

## T06 — Cierre, devolución y recepción frontend solo mockean éxito; falta rechazar promesas, mantener diálogo/datos, bloquear doble submit y evitar callback éxito/refresh falso ante error.

Gravedad: LOW. Estado: CONFIRMED_STATIC_TEST_GAP. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/__tests__/DailyCloseDialog.test.tsx:64-101', 'src/components/__tests__/ReturnDialog.test.tsx:54-125', 'src/components/__tests__/TransferListDialog.test.tsx:43-135']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['src/components/__tests__/DailyCloseDialog.test.tsx:64-101', 'src/components/__tests__/ReturnDialog.test.tsx:54-125', 'src/components/__tests__/TransferListDialog.test.tsx:43-135']

Impacto: La UI puede cerrar operación rechazada, perder borrador o duplicar acciones sin que los tests de éxito lo detecten.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Añadir mockRejectedValue y doble clic/concurrent submit; asserts callback no invocado y UI permite retry coherente.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_tests.json

## T07 — Fixtures por defecto suplantan auth como superusuario. Las suites de negocio prueban DB y rutas pero no autenticación JWT; api_usage Uvicorn también fakea auth. Negativos existentes en suites dedicadas sí son sustantivos y E2E SQLite autentica realmente.

Gravedad: INFORMATIONAL. Estado: CONFIRMED_STATIC_TEST_GAP. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/conftest.py:75-103', 'backend/tests/test_api_usage.py:48-71']; ['_enable_test_overrides']

Evidencia concreta: ['backend/conftest.py:75-103', 'backend/tests/test_api_usage.py:48-71']

Impacto: Suites comerciales verdes con superusuario simulado no prueban que JWT, roles y sedes reales rechacen accesos indebidos.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Separar fixture client autenticado real por defecto de client bypass explícito; parametrizar RBAC real en endpoints críticos. No interpretar número backend como cobertura auth completa.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_tests.json

## UTIL-01 — Arranque Windows resembra PostgreSQL y puede sobrescribir stock existente

Gravedad: HIGH. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['start-backend.bat:38-42', 'backend/init_db.py:20-27,80-83', 'backend/app/utils/demo_seed.py:293-329', 'backend/app/config.py:33-35']; ['_sync_stock']

Evidencia concreta: El BAT decide inicializar por ausencia de inventory.db, independiente de DATABASE_URL. En PostgreSQL ese archivo normalmente no existe; init_db --with-data opera en engine configurado y _sync_stock actualiza cantidades existentes a valores demo sin StockHistory en rama update. No ejecutado.

Impacto: Reiniciar desde Windows puede reemplazar cantidades de negocio por demo sin historial si DATABASE_URL usa PostgreSQL.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Separar creación esquema de seeding; nunca sembrar en launcher; datos demo solo operación explícita sobre entorno aislado.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-02 — cleanup_v2 elimina documentación canónica

Gravedad: HIGH. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['cleanup_v2.sh:32-34,39-48,97-101']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Incluye COMIENZA_AQUI.md (existente y requerido por AGENTS) en FILES_TO_DELETE; mv sin -n puede sobrescribir docs/ARQUITECTURA.md si existe fuente histórica. CWD sin anclaje. No ejecutado.

Impacto: La limpieza elimina runbooks vigentes necesarios para desplegar, recuperar y mantener el sistema.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Retirar utilidades destructivas legacy o convertirlas a plan/dry-run explícito con backup y lista validada.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-03 — Calendar pierde botones accesibles para navegar meses

Gravedad: MEDIUM. Estado: confirmed_render. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/ui/calendar.tsx:61-67', 'node_modules/react-day-picker/dist/cjs/components/Nav.js', 'src/components/AdvancedSearchDialog.tsx:104-110']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: DayPicker9 espera PreviousMonthButton/NextMonthButton interactivos; wrapper devuelve svg. SSR produce nav con dos SVG type=button sin button/role/tabIndex. Navegación mouse mantiene onclick, pero Tab/Enter/Space nativos faltan; SVG incluye Chevron hijo redundante.

Impacto: Navegación de fechas queda sin botones accesibles; impide seleccionar períodos con teclado o ayudas.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Mantener botones de DayPicker y personalizar Chevron, actualizar classNames al API v9. Verificar rango y navegación teclado.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-04 — Progress omite valor semántico ARIA

Gravedad: LOW. Estado: confirmed_render. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/ui/progress.tsx:6-25']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: value se extrae y sólo modifica transform; no pasa a Root. SSR value65 da data-state indeterminate sin aria-valuenow. Consumido en SettingsDialog, OptimizationInsightsDialog, AIForecastingDialog.

Impacto: Lectores de pantalla no conocen el valor de progreso de operaciones.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Pasar value a Root y verificar ARIA 0/65/100.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-05 — test-system tolera tests frontend fallidos y concluye éxito

Gravedad: MEDIUM. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['test-system.sh:3-4,10']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: npm run test:coverage || echo ... continúa; backend exitoso hace terminar script 0 y Todas las pruebas finalizaron.

Impacto: Operador puede recibir mensaje de pruebas aprobadas pese fallo frontend y desplegar una regresión.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Propagar estado no cero de todos gates; no tratar tests fallidos como ausencia de tests.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-06 — Quickstart canónico llama setup faltante

Gravedad: MEDIUM. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['start-all.sh:9-26', 'README.md:38-55', 'COMIENZA_AQUI.md:5-12']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Cuando no existe backend/venv o node_modules hace chmod/ejecución setup-complete.sh; archivo no existe en SHA. Sigue sin set-e y puede anunciar configuración/arranque exitosos. .venv permitido por otros launchers tampoco lo reconoce.

Impacto: La instalación según quickstart se detiene al invocar un script ausente.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Alinear quickstart a instalación existente, crear venv explícitamente y usar launcher fail-fast con checks reales.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-07 — Simulaciones n8n no autentican discovery protegido y simulan éxito por prints

Gravedad: MEDIUM. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['test_n8n_simulation.py:21-36', 'simulate_whatsapp_flow.py:13-29', 'verify_learning.py:11-17', 'backend/app/routers/sales_profiles.py:61']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: GET sales-profiles sin bearer ni _headers; endpoint exige check_any_permission. X-N8N-Token no sustituye JWT de discovery. Scripts retornan/capturan excepciones sin exit no cero; test_n8n_flow no tiene asserts y puede pasar pytest tras error. Algunos POST log no comprueban status y anuncian éxito.

Impacto: Simulación muestra éxito sin acreditar discovery autenticado ni integración efectiva.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Usar JWT de usuario fixture autorizado, service endpoints con token separado, timeout y raise/assert por cada resultado; aislar datos demo y cleanup.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-08 — Configurador PostgreSQL rompe credenciales con caracteres normales e interpola SQL privilegiado

Gravedad: MEDIUM. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['setup-postgres.sh:120-142,156,179']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Password con apóstrofe se inserta literalmente en CREATE USER PASSWORD; identificadores sin quoting/validación; operaciones psql ignoran PG_HOST/PG_PORT elegidos, conectan al postgres local. URL no percent-encode para @ / #, sed replacement no escapa &, |.

Impacto: Credenciales ordinarias pueden generar URL/SQL inválidos; la utilidad privilegiada requiere escapado y parametrización.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Usar quoting identificadores/literales psql, destino host/port único y URL con urllib quote; escribir dotenv sin sed interpolado.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-09 — Root check_*.py auditan SQLite legacy y ocultan fallos

Gravedad: LOW. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['check_db_direct.py:4-25', 'check_ai_tables.py:4-36', 'check_user_role.py:5-31', 'check_users_schema.py:6-36', 'inspect_last_order.py:4-8']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Rutas inventory.db fijas no DATABASE_URL; varios imprimen error pero código0. inspect_last_order abre connect sin comprobar existencia y crea archivo vacío. No validan PostgreSQL productivo.

Impacto: Diagnósticos auditan SQLite legado y pueden informar sobre una base ajena a producción PostgreSQL.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Marcar compatibilidad SQLite, URI mode=ro y códigos de salida correctos; herramientas productivas deben usar engine config explícito y no exponer registros cliente.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-10 — reset_system anuncia reseteo aunque no aplica a PostgreSQL y mata uvicorn globalmente

Gravedad: MEDIUM. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['reset_system.sh:6-23']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: pkill -f uvicorn mata todos procesos coincidentes del usuario; rm backend/inventory.db ignora DATABASE_URL y sin backup; init_db crea tablas sin vaciar PG existente. No set-e y siempre anuncia éxito. No ejecutado.

Impacto: Operador cree haber reseteado PostgreSQL aunque herramienta sólo trata SQLite y puede terminar otros procesos Uvicorn.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Retirar reset legacy del camino operativo; pruebas sólo DB aislada, PID concreto y confirmación/backup explícitos.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-11 — Dialog y AlertDialog fuerzan pantalla completa también desktop

Gravedad: LOW. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/ui/dialog.tsx:59-62', 'src/components/ui/alert-dialog.tsx:58-60']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: !w-screen !h-[100dvh] !max-w-none !max-h-none son important y prevalecen sobre sm:w/height/max*. La intención responsive y max-width del caller no se aplica.

Impacto: Diálogos ocupan toda la pantalla en escritorio y degradan operativa paralela/contexto.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Limitar important al breakpoint móvil o quitarlo; comprobar contenido crítico desktop/mobile.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## UTIL-12 — ChartTooltipContent oculta valores cero

Gravedad: LOW. Estado: confirmed_static_unused. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/ui/chart.tsx:248-252']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Guard item.value && devuelve 0 desnudo en React, sin span ni formato previsto; cero se oculta o queda texto crudo. No consumidores de wrapper chart fuera UI encontrados; bug latente.

Impacto: Valores financieros cero se ocultan y parecen datos faltantes en gráficos.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Comprobar != null y renderizar formato para 0.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## DOC-01 — LIMITATIONS contradice conversión USD implementada

Gravedad: MEDIUM. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['docs/LIMITATIONS.md:5-15', 'docs/ARQUITECTURA.md:17', 'docs/PROMPT_NEGOCIACION_BOT.md:79-92', 'backend/app/utils/order_currency.py:15-59', 'backend/app/services/order_service.py:176']; ['create_order']

Evidencia concreta: LIMITATIONS afirma no conversión automática/moneda solo compatibilidad; helper convierte catálogo+costo USD a HNL con exchange_rate del perfil y fallback25; la guía negociación lo describe. Arquitectura HNL final es correcto pero compatibilidad-only es impreciso.

Impacto: La documentación induce a asumir ausencia de conversión USD y puede promover cambios redundantes o incorrectos.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Documentar catálogo USD→ledger HNL, tasa utilizada y límites reales sobre historial y monedas soportadas.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## DOC-02 — Guías de producción vigentes aparentes omiten gates y dan falsa preparación

Gravedad: MEDIUM. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['SETUP_PRODUCCION_RAPIDO.md:1-14,105-128,218', 'docs/PROD_INFRA_SECURITY.md:17-35,87-96', 'docs/DEPLOYMENT_PROD.md:42-49,94-105', 'setup-production.sh:203']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Guías antiguas no rotuladas histórico remiten a root setup manual/cron o compose sin perfiles backup/offsite y no gate validate-prod; afirman producción lista. Contradicen runbook canónico que exige offsite, DR, secretos fuertes, CI y reglas release.

Impacto: Guías que omiten recuperación, SHA, configuración y gates pueden llevar a declarar producción lista sin evidencia.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Convertir cada guía histórica a redirect/banner canónico; scripts root producción deben delegar a deploy gate.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## DOC-03 — Integración n8n tiene JSON corrupto y contratos obsoletos

Gravedad: MEDIUM. Estado: confirmed_static. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['docs/INTEGRACION_N8N.md:23-37,66-99,146-159', 'docs/AI_REPORTING_SCOPE.md:13-28', 'TEST_N8N.md:25-35']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: §3 JSON queda abierto y se mezcla con §4; sales_profile_id/query y message_source/platform vs scripts actuales slug/message_content/role/content; seguridad dice API pública y propone implementar auth pese RBAC existente. AI scope aún exige N8N y marca Prometheus futuro aunque runbook actual los soporta.

Impacto: JSON y contratos n8n obsoletos impiden configurar el flujo prometido de atención automatizada.

Reproducción: Escenario descrito por evidencia estática; reproducción runtime pendiente salvo resultado explícito en el bloque.

Corrección recomendada: Reescribir usando schemas actuales y una prueba contractual fixture; autenticación exacta X-N8N-Token versus JWT.

Pruebas: Añadir regresión específica y ejecutar gates aplicables en entorno descartable.

Fuente: BLOQUE_utilities.json

## PROD-01 — Producción no tiene provenance verificable y conserva cambios fuera de GitHub

Gravedad: HIGH. Estado: OBSERVED_READ_ONLY. Evidencia: OBSERVED_PRODUCTION_READ_ONLY.

Archivo/función: ['VPS /var/www/inventario checkout y configuración runtime; evidencia no publica secretos']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['2026-10-14 GET https://invjear.com/api/health y /api/ready HTTP200; X-Release-SHA: unknown.', 'WorkingDirectory systemd /var/www/inventario/backend; checkout HEAD1cfa35e9ba2e1db28e43285fac482d18021426ef sucio: backend/backup_database.sh,src/App.tsx,src/components/AIStatusWidget.tsx,tests/browser/receipt.spec.ts.', 'Comparación blob working files contra SHA auditado: 348 src+backend/app,346 iguales,diferentes App.tsx y AIStatusWidget.tsx; ningún ausente. No prueba el bundle servido.']

Impacto: No se puede garantizar que pruebas de GitHub representan frontend desplegado ni rollback reproducible.

Reproducción: GET health/ready y comparación de blobs de solo lectura; no cambió configuración ni archivos VPS.

Corrección recomendada: Tras fase auditada y autorización, recuperar diffs por PR y desplegar checkout limpio con APP_BUILD_SHA y artefactos identificados.

Pruebas: Verificar header SHA esperado, bundle/imágenes, ausencia deriva y smoke real.

Fuente: VERIFICACIONES.md

## PROD-02 — Backup off-site obligatorio sin destino configurado

Gravedad: HIGH. Estado: OBSERVED_READ_ONLY. Evidencia: OBSERVED_PRODUCTION_READ_ONLY.

Archivo/función: ['VPS /var/www/inventario checkout y configuración runtime; evidencia no publica secretos']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: ['Solo presencia de variables en /var/www/inventario/backend/.env: REQUIRE_OFFSITE_BACKUP=true; BACKUP_RCLONE_DESTINATION vacío/ausente. No se expusieron secretos.', 'Issue38 abierto; rulesets API sólo21015275 branch main activo, no tag v*.']

Impacto: Pérdida de servidor puede dejar sin copia externa recuperable. ReadinessHTTP200 no valida offsite.

Reproducción: Comprobar presencia booleana de configuración y evidencia privada de copia; copia real no ejecutada en auditoría.

Corrección recomendada: Configurar destino externo tras decisión/credenciales; copia y verificación por contenido y restauración aislada.

Pruebas: rclone check download, restore DR con RPO/RTO completo, reglas tags.

Fuente: VERIFICACIONES.md

## OBS-01 — Etiquetas métricas ilimitadas para rutas arbitrarias

Gravedad: HIGH. Estado: REPRODUCED_ISOLATED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/main.py:237-263', 'backend/app/utils/prometheus_metrics.py']; ['collect_runtime_metrics']

Evidencia concreta: Veinte rutas /uploads diferentes que devuelven 404 crean veinte series de contador y veinte de histograma. La normalización mantiene segmentos arbitrarios y /uploads está exento del limitador general.

Impacto: Memoria y cardinalidad de métricas pueden crecer con peticiones externas.

Reproducción: Ejecutar TestClient con veinte URL únicas inexistentes bajo /uploads y contar etiquetas antes/después. No se envió carga a producción.

Corrección recomendada: Etiquetar por plantilla de ruta y limitar rutas desconocidas.

Pruebas: Comprobar cardinalidad constante con rutas desconocidas y límites de uploads.

Fuente: CONTINUACION_02.json

## OBS-02 — Contexto de logs global se mezcla entre peticiones async

Gravedad: MEDIUM. Estado: REPRODUCED_ISOLATED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/utils/logging_config.py:222-259', 'backend/app/middleware/request_context.py']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: LogContext sustituye LogRecordFactory global. Contextos A/B solapados atribuyen el log de A a B y dejan una factoría anterior tras salir.

Impacto: Correlación y auditoría de incidentes pueden atribuir peticiones al identificador equivocado.

Reproducción: Intercalar enter A, enter B, log A, exit A, exit B.

Corrección recomendada: Usar contexto por tarea y factoría estable.

Pruebas: Prueba async de dos solicitudes con correlación independiente y restauración.

Fuente: CONTINUACION_02.json

## OBS-03 — Inicialización duplicada de Sentry sobrescribe configuración

Gravedad: MEDIUM. Estado: REPRODUCED_ISOLATED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/main.py:73-74', 'backend/app/utils/observability.py', 'backend/app/utils/sentry_config.py']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Dos inicializadores llaman init del SDK; el segundo omite opciones de profiling/PII presentes en el primero. Verificado con SDK simulado, sin conexión a Sentry.

Impacto: Telemetría configurada puede diferir de lo esperado.

Reproducción: Configurar DSN ficticio y registrar las dos llamadas con DummySDK.

Corrección recomendada: Unificar inicialización y política de opciones.

Pruebas: Una inicialización con opciones finales explícitas.

Fuente: CONTINUACION_02.json

## MODEL-01 — Modelo analytics no puede importarse

Gravedad: LOW. Estado: REPRODUCED_ISOLATED_LATENT. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['backend/app/models/analytics.py:32-43']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: SQLAlchemy rechaza el atributo declarativo reservado metadata con InvalidRequestError. El módulo no está importado por el modelo canónico; no afecta el arranque observado.

Impacto: Integrar posteriormente ese módulo rompería la importación.

Reproducción: Importar app.models.analytics en subproceso aislado.

Corrección recomendada: Renombrar atributo Python manteniendo nombre de columna si procede.

Pruebas: Importación de todos los módulos de modelos.

Fuente: CONTINUACION_02.json

## FE-12 — Exportación CSV corrompe comillas y conserva fórmulas

Gravedad: MEDIUM. Estado: REPRODUCED_ISOLATED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['src/lib/exportUtils.ts:3-18', 'src/components/StockHistoryDialog.tsx']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: El campo a"b se serializa con barra invertida, no doble comilla CSV; csv.reader no recupera el valor original. =1+1 queda sin neutralizar. No se ejecutó una fórmula en una hoja real.

Impacto: Datos exportados pueden alterarse; riesgo de fórmulas al abrir hojas.

Reproducción: Exportar a"b y =1+1 con el helper real y leer con csv.reader.

Corrección recomendada: Escapado CSV estándar y política de celdas formula.

Pruebas: Roundtrip de comillas, saltos, separadores y prefijos de fórmula.

Fuente: CONTINUACION_02.json

## FE-13 — Reporte excluye costo de regalías y usa fecha de creación

Gravedad: MEDIUM. Estado: REPRODUCED_ISOLATED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['src/lib/reportUtils.ts:50-123', 'src/components/ReportsDialog.tsx']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Venta total 1000, costo pagado 600 y regalo costo 100 produce margen 40%, aunque corresponde 30%. Venta creada en septiembre y completada en octubre se asigna a septiembre.

Impacto: Rentabilidad y cierres mensuales pueden informar valores incorrectos.

Reproducción: Ejecutar generateReportData con ambos fixtures del JSON de reproducción.

Corrección recomendada: Incluir todo costo entregado y definir fecha contable coherente.

Pruebas: Regalías y órdenes que cruzan meses.

Fuente: CONTINUACION_02.json

## FE-14 — Catálogo público nuevo usa API localhost por defecto

Gravedad: HIGH. Estado: OBSERVED_PRODUCTION_BROWSER_WITH_STATIC_ROOT_CAUSE. Evidencia: OBSERVED_PRODUCTION_READ_ONLY.

Archivo/función: ['src/components/PublicCatalog.tsx', 'src/App.tsx:2786']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: PublicCatalog lee settings_api_url con localhost:8000/api por defecto. La ruta pública se muestra antes de BackendConnectionCheck; un visitante sin KV no normaliza la API al origen. Incluye destino WhatsApp de ejemplo.

Impacto: Visitantes nuevos pueden no ver catálogo ni contactar al negocio correcto.

Reproducción: Abrir /catalogo en navegador limpio desplegado; prueba browser todavía pendiente.

Corrección recomendada: Resolver API pública por origen y configurar contacto real.

Pruebas: Visita limpia de producción sin almacenamiento previo.

Fuente: CONTINUACION_02.json

## FE-15 — Errores de API se presentan como historiales vacíos

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryServiceFactory.ts:1760-1990', 'src/components/AITrainingCenter.tsx']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Capturas de errores retornan [] o null en varios lectores; componentes muestran ausencia de datos o todo al día.

Impacto: Interrupciones pueden ocultar historial y tareas pendientes.

Reproducción: Simular error de API en lectores de historial/training queue y observar resultado vacío. Runtime UI pendiente.

Corrección recomendada: Propagar estado de error distinguible del resultado vacío.

Pruebas: Error HTTP/red y resultados realmente vacíos.

Fuente: CONTINUACION_02.json

## SYNC-01 — Sincronización usa IDs locales y continúa tras dependencias fallidas

Gravedad: HIGH. Estado: REPRODUCED_MOCK_API. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['src/lib/syncService.ts']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Ubicación local 1 creada como remota 100; creación producto envía location_id=1. Si creación producto 7 falla, update siguiente usa ID7 y se marca sincronizado.

Impacto: Puede escribir entidad remota equivocada o asociar inventario a otra sucursal si coinciden IDs.

Reproducción: API mock del servicio real con remapeo 1→100 y creación fallida 7.

Corrección recomendada: Remapear todas las claves y bloquear dependencias sin ID remoto.

Pruebas: IDs divergentes, colisiones y fallos de creación antes de update.

Fuente: CONTINUACION_02.json

## SYNC-02 — Diario pierde eventos concurrentes y pendientes al truncar

Gravedad: MEDIUM. Estado: REPRODUCED_MEMORY_KV. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['src/lib/syncJournal.ts']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Dos recordEvent simultáneos persisten uno. Al añadir sobre 5000 eventos pendientes se elimina el pendiente más antiguo.

Impacto: Cambios locales pueden perderse sin sincronizar.

Reproducción: Promise.all con dos eventos; después agregar uno a 5000 pendientes usando KV en memoria.

Corrección recomendada: Persistencia serializada y retención que preserve pendientes.

Pruebas: Concurrencia y límite con todos los eventos pendientes.

Fuente: CONTINUACION_02.json

## SA-01 — Cancelación administrativa no bloquea estado del traslado

Gravedad: HIGH. Estado: GROUNDED_RISK_PENDING_POSTGRES. Evidencia: RISK_PENDING_VERIFICATION.

Archivo/función: ['backend/app/routers/super_admin.py:955-1027']; ['super_admin_cancel_transfer']

Evidencia concreta: Lee traslado pendiente sin FOR UPDATE y luego bloquea stock sin refrescar estado. Puede competir con confirmación canónica; requiere comprobar intercalación PostgreSQL.

Impacto: Riesgo de cancelar traslado confirmado o liberar reservas agregadas ajenas.

Reproducción: Coordinar confirmación y cancelación en PostgreSQL descartable; no ejecutado.

Corrección recomendada: Bloquear traslado y revalidar estado dentro de transacción coherente.

Pruebas: Carrera confirm/cancel con otra reserva del mismo producto.

Fuente: CONTINUACION_02.json

## SA-02 — Purga parcial puede dejar totales y devoluciones incoherentes

Gravedad: HIGH. Estado: GROUNDED_STATIC_CONDITIONAL. Evidencia: RISK_PENDING_VERIFICATION.

Archivo/función: ['backend/app/routers/super_admin.py:805-899']; ['purge_product_for_admin']

Evidencia concreta: Purga elimina ítems del producto de órdenes mixtas sin reconciliar totales/pagos; devuelve eliminación de todas las devoluciones de órdenes que contienen el producto. Producción tiene purga desactivada según comprobación anterior.

Impacto: Si se habilita, pérdida de trazabilidad de otros productos y cifras históricas inconsistentes.

Reproducción: Fixture mixto en DB descartable; no se ejecutó ninguna purga.

Corrección recomendada: Definir política de retención y consistencia antes de habilitar.

Pruebas: Órdenes/devoluciones mixtas y validación de totales.

Fuente: CONTINUACION_02.json

## TEST-08 — Pruebas de invariantes aceptan pérdida de actualizaciones

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_TEST_ORACLE. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/tests/test_stock_manager_invariants.py']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Threads parten de stock5 y pueden escribir1; el test sólo exige no negativo. Reservas simultáneas y errores recolectados no tienen oráculo estricto de conservación.

Impacto: Tests verdes no demuestran integridad concurrente de stock.

Reproducción: Revisar asserts y errores recolectados; ejecución PostgreSQL pendiente.

Corrección recomendada: Afirmar stock exacto, reservas, resultados y ausencia de errores no previstos.

Pruebas: Transacciones concurrentes reales con conservación de cantidades.

Fuente: CONTINUACION_02.json

## DOC-04 — Instrucciones activas de Copilot prescriben borrar BD y arquitectura obsoleta

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['.github/copilot-instructions.md:9,19-32,294-315', 'src/lib/inventoryServiceFactory.ts:828-840', 'AGENTS.md:17-23,62-70', 'docs/PRODUCCION_FINAL.md:146-164']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Archivo de instrucciones para asistentes declara SQLite, local default sin distinguir producción, no tests frontend, y tras cambios de modelo manda Delete backend/inventory.db + init_db --with-data. Código actual fuerza API en production y migra con ledger/fail-fast; AGENTS prohíbe reset/reseed como shortcut.

Impacto: Desarrolladores/asistentes pueden reintroducir fallback de escritura local o destruir instalación SQLite legado al seguir una instrucción aparentemente vigente; también omitir regresiones configuradas. No demuestra ejecución insegura actual: AGENTS y canonical tienen prioridad.

Reproducción: Lectura exacta instrucciones versus código runtimePolicy/factory y AGENTS; no acciones ejecutadas.

Corrección recomendada: Sincronizar .github/copilot-instructions.md con AGENTS y referir runbook; quitar delete/reseed y declarar matriz tests real.

Pruebas: Revisión documental de invariantes y comprobación de links/comandos; ninguna prueba runtime necesaria para cambio docs.

Fuente: CONT03_docs.json

## DOC-05 — Guía canales confunde firma HMAC con verify token y recomienda borrar credenciales reales

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['CHANNELS_CONFIGURATION.md:378-390', 'backend/app/routers/channel_integrations.py:207-225', 'backend/seed_channel_credentials.py:168-211,220-260']; ['_verify_meta_signature', 'populate_credentials']

Evidencia concreta: Ante Firma inválida HTTP401 se atribuye causa a verify_token y recomienda seed --clear + --populate sin limitar a testing. Error real compara X-Hub-Signature-256 HMAC raw_body con META_APP_SECRET; no usa verify_token. Script clear/populate opera todos perfiles activos con credenciales ficticias.

Impacto: Operador intentando recuperar webhooks elimina tokens reales de todos perfiles y los sustituye por demos, provocando caída de mensajería sin solucionar firma. También se materializa pérdida de config documentada OPS-09.

Reproducción: Trazado estático exacto del error a _verify_meta_signature versus pasos guide y alcance all active profiles de utilidad; no se ejecutó seed.

Corrección recomendada: Distinguir challenge GET verify_token de firma POST app_secret; troubleshooting debe validar firma/cuerpo/secret y nunca seed demo sobre instalación real.

Pruebas: Prueba documental de casos GET challenge versus POST bad signature; guard producción en utilidad se evalúa por PR separado.

Fuente: CONT03_docs.json

## DOC-06 — Documentación upgrade prescribe migraciones que no existen

Gravedad: LOW. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['CHANGELOG_AI_IMPROVEMENTS_V2.md:145-149,199-203', 'docs/GUIA_TRANSFERENCIAS.md:159-164']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Nombra backend/migrate_add_ai_memory_and_queue.py e indica ejecutar migrate_stock_transfers.py; rg --files no encuentra ambos en SHA auditado. Auto_migrations actual cubre otras nueve compatibilidades, no script nombrado. Documentos fechados históricos, canonical startup no invoca estas rutas.

Impacto: Operador siguiendo guía específica de upgrade recibe file not found y no tiene procedimiento verificable para agregar campos a schema antiguo; no prueba que despliegue fresco falle.

Reproducción: Inventario rastreado de paths exactos ausentes comparado instrucciones; no migraciones ejecutadas.

Corrección recomendada: Rotular históricos y redirigir ACTUALIZAR_INSTALACION_EXISTENTE/runbook; documentar baselines soportados y migración real para cada campo antes de ofrecer upgrade.

Pruebas: Verificar existencia de cada path/comando documentado y smoke upgrade sólo con DB descartable.

Fuente: CONT03_docs.json

## CONT03-NS-01 — Conexiones técnicas muestra canales del formulario comercial anterior

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/SalesProfilesList.tsx:149,382-403,453,488,523,1101-1124']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: openTechnicalConfig asigna perfil y credenciales pero no setCanales(profile.canales); renderIntegrationsSection depende de canales compartido, inicial vacío. Solo openEdit lo asigna (347).

Impacto: Super Admin no ve campos para conectar canal; después de editar otro perfil ve secciones de canales equivocados y no los reales del perfil técnico.

Reproducción: Abrir app desde cero con perfil WhatsApp y pulsar Conexiones: muestra encabezado pero ninguna sección token/phoneID. Editar perfil Messenger, cerrar, abrir Conexiones de WhatsApp: aparece Messenger.

Corrección recomendada: Derivar canales desde technicalConfigProfile dentro renderer técnico o tener estado separado y copiar profile.canales al abrir.

Pruebas: Render fresh con perfil WhatsApp -> Phone Number ID/Access Token visibles; intercalar edición Messenger y conexión WhatsApp -> solo campos del perfil técnico.

Fuente: CONT03_components-ns.json

## CONT03-NS-02 — Reabastecimiento conserva IMEIs al cambiar producto serializado

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/RestockProductDialog.tsx:86-106,126-134,225-250']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Array imeis solo cambia por cantidad/isSerialized/open y se conserva prev; seleccionar producto cambia productId/productSearch, no resetea imeis/scanInput. Al volver a serializado, el efecto conserva contenido.

Impacto: Un serial físico escaneado para producto A puede ingresarse al inventario de B sin nueva revisión. Backend verifica unicidad pero no puede conocer que escaneo pertenecía a otro modelo.

Reproducción: Seleccionar A serializado cantidad1, escanear IMEI nuevo M; cambiar buscador a B serializado y seleccionar B; Guardar envía productId B con M. Alternativa cerrar sin guardar y reabrir: arrays anteriores persisten.

Corrección recomendada: Resetear borrador de seriales al cambiar producto y al abandonar/reabrir flujo; advertir antes de perder escaneo; conservar draft solo vinculado al mismo productId.

Pruebas: Prueba render cambiar A a B sin nuevo escaneo no permite guardar; request B no lleva M. Reabrir/cambiar serializado->no->serializado elimina serial anterior.

Fuente: CONT03_components-ns.json

## CONT03-NS-03 — Activar retoma y trasladarla son dos operaciones con estado parcial

Gravedad: HIGH. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/PendingTradeInsDialog.tsx:96-132,245-248', 'backend/app/routers/stock_transfers.py:132']; ['create_transfer']

Evidencia concreta: handleActivate primero confirma updateProduct activo/celular; después crea traslado. Si creación falla, catch solo toast y no compensa/reporta activación durable. No busy guard ni botón disabled. Crear transferencia deja estado pendiente, pero toast afirma transferido.

Impacto: Retoma puede quedar activada en origen aunque operador ve error; al recargar desaparece de pendientes y no completa ubicación elegida. Doble clic duplica intentos de traslado. Mensaje éxito no distingue despacho pendiente de recepción.

Reproducción: Mock updateProduct resuelve y createStockTransfer rechaza: producto ya activo, UI mantiene formulario y dice Error al activar. Recargar pendientes excluye producto categoria celular. Si ambas resuelven el traslado sigue pendiente mientras toast dice transferido.

Corrección recomendada: Un endpoint transaccional para activación+solicitud traslado, o protocolo explícito con status parcial y recovery de traslado existente; bloquear submit; mostrar transferencia solicitada pendiente recepción.

Pruebas: Prueba fallo segundo paso verifica estado comunicado y recovery sin reactivar/duplicar; doble submit produce una operación; successful create pending no se anuncia recepción.

Fuente: CONT03_components-ns.json

## CONT03-NS-04 — Atajos diagnóstico de stock generan borradores sobrescritos o incompatibles

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/SuperAdminControlPanelDialog.tsx:170-171,362-367,826-856', 'backend/app/routers/super_admin_integrity.py:52-62']; ['_assert_serialized_stock_target']

Evidencia concreta: Atajos asignan product/location y campos correctivos; useEffect selectedStock sobrescribe campos con valores originales al cambiar selección. Marcar defectuosa fija available=imeiCount+reserved y defective=oldDefective+extra; backend exige available+defective-reserved==imeiCount, imposible si defective>0.

Impacto: Corrección asistida no aplica objetivo mostrado y falla 409 o vuelve a stock original. Operador debe resolver manualmente inconsistencia, con propuesta no fiable.

Reproducción: Issue stock5 IMEI4, res0 def0; primer click Marcar defectuosa selecciona fila y efecto reescribe stock original. Con selección ya vigente, click deja available4 defective1 -> backend physical5 vs IMEI4 ->409.

Corrección recomendada: Separar hidratación selección de draft correctivo y usar modelo físico canónico para propuestas; describir límites de diagnóstico defectuoso y conciliación serial.

Pruebas: Render stock5/IMEI4 click atajo debe mantener propuesta; contrato payload canonical debe pasar o mostrar por qué no puede corregirse automáticamente; no enviar silenciosamente stock original.

Fuente: CONT03_components-ns.json

## TEST-09 — Webhooks de entrega se prueban con validación de firma deshabilitada

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_TEST_GAP. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['backend/tests/test_channel_integrations.py:49,144', 'backend/tests/test_channel_webhook_delivery_integrity.py:46,97,163,214,269', 'backend/tests/test_channel_integrations.py:121-132']; ['test_ai_failure_releases_processing_claim_and_same_message_can_retry', 'test_channels_health_snapshot', 'test_whatsapp_webhook_processes_and_replies']

Evidencia concreta: Todos los POST webhook de integración/delivery/retry fijan META_APP_SECRET vacío. Único uso no vacío comprueba snapshot health.signature_validation_enabled; no existe request firmado válido, firma ausente, firma incorrecta ni cuerpo manipulado en backend/tests (lectura completa + búsqueda signature/hmac/X-Hub/META_APP_SECRET).

Impacto: Los gates no detectan regresión en frontera autenticación webhook de proveedores, ni efectos DB al rechazar firmas. Brecha test; no demuestra bypass implementación.

Reproducción: Estática: enumerar META_APP_SECRET/headers en todos tests; una implementación que ignore firma conservaría los mismos oráculos de POST existentes. No se ha ejecutado mutación del programa.

Corrección recomendada: Añadir pruebas HTTP con secret no vacío y bytes crudos: HMAC correcto acepta, ausente/inválido/cuerpo alterado rechaza y deja ProcessedMessage/logs/orders sin efectos.

Pruebas: TestClient PostgreSQL descartable, sin llamadas Meta reales, parametrizar whatsapp/messenger/instagram y cuentas distintas.

Fuente: CONT03_tests.json

## LOCAL-01 — Persistencia local de venta/IMEI/historial no es atómica y silencia fallo

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:275-283,295-303,315-323,1618-1625,4849-4862']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Setters IMEI y ambos historiales capturan error KV y resuelven. createOrder escribe products/stock/orders/items antes de seriales, sin rollback; compra también Promise.all con setters silenciosos. Incluso rollback addProduct no ve fallo IMEI ocultado.

Impacto: Efectos parciales y éxito falso en modo local; datos financieros y seriales dejan de reconciliar. No duplicación de BUS-10 backend: es implementación local independiente.

Reproducción: KV.set rechaza sólo inventory-product-imeis (quota/error). createOrder serialized escribe orden/reserva/items y devuelve éxito sin reservar IMEI; un siguiente pedido puede reutilizar ese serial. Fallar inventory-orders deja stock reservado sin orden.

Corrección recomendada: Propagar errores setters; una unidad commit atómica local (p.ej IndexedDB) o rollback verificable que no anuncie éxito ante persistencia parcial.

Pruebas: Prueba fault-injection por cada clave persistida; exigir rollback snapshot entero o rechazo sin cambio; almacenamiento mock debe clonear como JSON no compartir referencias.

Fuente: CONT03_core.json

## LOCAL-02 — Eliminar orden cancelada o pendiente fabrica stock y no libera seriales creados

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:1333-1341,3168-3277,1851-1880']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: deleteOrder suma item.cantidad para cualquier estado y no reduce cantidad_reservada; cancelOrder ya restauró final o liberó reserva pendiente. Item creado no guarda imeis (1333), deleteOrder libera IMEI únicamente si item.imeis existe.

Impacto: Stock fantasma y serial vendido sin orden; UI local permite eliminación de canceladas. No es BUS-01 reserva ajena: este es doble reposición/cancel-delete y pérdida lista item.

Reproducción: Stock5. Crear pendiente qty1 -> disp5 res1. cancelOrder -> disp5 res0. deleteOrder -> disp6. Alternativa pending delete -> disp6 res1 sin orden. Serializado crear/finalizar/delete: stock aumenta pero IMEI sigue vendido porque item.imeis undefined.

Corrección recomendada: Restaurar según lifecycle y efecto propio real; nunca reponer cancelada; liberar reservas pending; persistir IMEIs por ítem y guard audit retention.

Pruebas: create/cancel/delete pendiente y final; assert disponible5 reservado0 y original IMEI disponible; verificar item.imeis tras create/list.

Fuente: CONT03_core.json

## LOCAL-03 — updateOrderStatus ignora lifecycle y deja cancelación local sin liberar reserva

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:2017-2111']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: No lock, no matriz transición y sólo maneja entrada a estado final. Asigna estado cancelada sin cancelOrder. También permite final->pending y posterior edición que usa reservas agregadas.

Impacto: Reservas bloqueadas por venta cancelada y resultados concurrentes no conservados. Transiciones server protegidas no validan esta implementación local.

Reproducción: En modo local crear pendiente qty1 stock5 res1; updateOrderStatus(id,cancelada) -> cancelada pero res1 e IMEI order_id conservados. Con dos finalizaciones Promise.all ambas leen snapshot pending y guardan estados/historia sin serialización.

Corrección recomendada: Delegar cancelada a cancelOrder, adquirir lock y usar matriz estricta final/inmutable con titular de reserva explícito.

Pruebas: Tests cada transición admitida/negada y concurrent finalization/cancel. Verificar efectos stock,IMEI y journal, no sólo enum.

Fuente: CONT03_core.json

## LOCAL-04 — Editar pedido reemplaza precio histórico y omite conversión, retoma y financiamiento

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:2395-2408,2457-2474,2483-2494']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: updateOrder reconstruye items con Product.precio crudo, total=sum catálogo; no preserva precio negociado, costo snapshot ni resta trade_ins ni recargo financing_details existente. Guarda total pero deja financing_details viejo.

Impacto: Reescritura monetaria histórica en modo local; contrato local deja de coincidir API y flujo UI. Relacionado FE-01 pero distinto cálculo editar.

Reproducción: Producto USD precio100, tasa25; orden inicial HNL2500 con custom o conversión. Editar sólo nombre con UI (envía items) -> nuevo total100 HNL. Orden HNL1000 retoma200 prima100 tasa10% pasa de870 a1000, detalles viejos mantienen financed700 y cuota distinta.

Corrección recomendada: Preservar campos de ítems originales, normalizar moneda y recalcular retoma/financiación bajo contrato común; cambios no financieros no tocar items.

Pruebas: Regresión cambio nombre con items idénticos preserva total/precio/costo; USD, descuento, retoma y financiación; suma breakdown==total.

Fuente: CONT03_core.json

## LOCAL-05 — Aprobar conteo obsoleto resucita stock vendido y puede dejar reserva mayor que disponible

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:4872-4902,4917-4970']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: createInventoryCount guarda expected/difference. approve escribe counted absoluto sin comprobar esperado contra actual ni reservas, historia usa difference original aunque stockAnterior actual cambió. Serial selector no excluye order_id.

Impacto: Stock duplicado y ledger falso por concurrencia temporal aunque método usa lock al aprobar; potencial reserva impossible.

Reproducción: Conteo draft expected10,counted10. Venta final consume1 -> stock9. Aprobar draft -> stock10 historia cantidad0 (anterior9,nuevo10). Stock10 reservado5, conteo counted2 -> disp2 reservado5. Serialized: serial reservado a order puede aparecer en count y luego quedar location undefined.

Corrección recomendada: Versionar snapshot conteo y revalidar bajo lock, aplicar ajuste coherente o requerir recuento; excluir/respetar seriales reservados y recalcular delta actual.

Pruebas: Conteo draft seguido por venta/traslado/reabastecimiento; exigir stale rejection o delta reconciliado, stock>=reservado y history delta exacto; serial reservado.

Fuente: CONT03_core.json

## LOCAL-06 — Recepción compra acepta cantidad negativa y duplicados IMEI dentro línea

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:4809-4862']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Sólo valida existencia producto, length imeis==quantity y colisiones contra imeis existentes antes del loop. Dos strings iguales en misma línea pasan porque validación se hace antes de push; no validación finita positiva/integer quantity,unit_cost ni location existente.

Impacto: Negativo stock normal desde entrada y violación unicidad serial modo local; tipos numéricos no sustituyen validación runtime.

Reproducción: createPurchaseReceipt accesorio qty=-1 unit_cost100 -> reduce stock, recibo costo-100. Producto serial quantity2 imeis[X,X] sin X previamente -> registra dos records misma string y stock+2.

Corrección recomendada: Esquema runtime equivalente servidor, deduplicar IMEIs payload completo y comprobar product/location/supplier/activo antes de mutar.

Pruebas: Payload quantities -1,NaN,0,fraction, costos negativos y location inválida; duplicates dentro línea y entre líneas; snapshot inalterado al rechazar.

Fuente: CONT03_core.json

## LOCAL-07 — Garantía local permite devolución infinita y reutiliza IMEI defectuoso como vendible

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:5162-5210,5211-5334,5336-5387']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: createReturn sólo exige existencia orden; no mira orderItems ni estado ni cantidad ya retornada, originalIMEI order/product; pone original vendidofalse sin marcar bloqueado/defectuoso. Reemplazo encontrado se vende sin comprobar vendido/reservado/producto; cantidad salida1 vs quantity arbitraria.

Impacto: Inventario fabricado y defecto revendido, reemplazos de otra venta/reserva reasignados localmente. BUS-03/04 existentes servidor son relacionados, no equivalentes a ausencia general de validación local.

Reproducción: Orden qty1: repetir warranty qty1 condition nuevo aumenta stock cada vez; solicitar product_id ajeno crea stock para producto no comprado. Garantía defectuoso original serialX se libera y getAvailableIMEIs incluyeX si existe stock sano del mismo producto.

Corrección recomendada: Contrato warranty-only runtime, validar pertenencia y límite acumulado, bloquear serial defectuoso, validar reemplazo único disponible antes de writes.

Pruebas: Pedido no final, qty negativa/>vendida/repetida, producto ajeno, serial original cruzado, reemplazo vendido/en transferencia, defectuoso no aparece available.

Fuente: CONT03_core.json

## LOCAL-08 — Financiamiento local convierte tasa0 a4% y original_total incluye recargo

Gravedad: LOW. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:1565,1581-1590,7060']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: createBank normal_card_rate||0.04 y createOrder mismo fallback; tasa0 es válida pero falsy. original_total se calcula desde total ya recargado más retoma.

Impacto: Cobro no acordado en modo local; resultados diferentes servidor. Caso tasa normal0 no cubierto test opción financiada rate0.

Reproducción: Banco rate0 crear (o actualizar0), pedido tarjeta neto1000 months0 ->1040. Banco5% pedido1000 retoma0 -> original_total1050 en vez1000. Prima superior neto clamp financed0 y acepta total prima inflada.

Corrección recomendada: Usar?? preservando0 y validar finitud/intervalos/primavsneta; original_total del subtotal original antes modificar total.

Pruebas: rate0 normal y financiación; prima0,igual,mayor,negativa; assert original_total antes recargo.

Fuente: CONT03_core.json

## LOCAL-09 — Transferencias locales no toman lock ni validan cantidades positivas/destino diferente

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC_LOCAL_ONLY. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/lib/inventoryService.ts:3830-3863,4023-4064,4355-4394,4425-4457']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: CRUD transfer no inventoryLock.acquire, a diferencia createOrder/restock; createStockTransfer comprueba available<request.cantidad pero no >0/integer ni from!=to. Dos llamadas leen snapshots stock/transfers e IDs max+1.

Impacto: Stock libre inventado y pérdida reservas/entidades en modo local; AsyncLock tampoco protege tabs diferentes. Distinto batch parcial FE-04.

Reproducción: Qty=-2 accesorio disp5res0 -> reserva-2, free7. Qty1 origen=destino aceptado. Promise.all dos transferencias qty4 disp5 leen ambos available5 y luego writes uno sobre otro/IDs iguales. Carrera transfer vs order puede perder reservas aunque order esté bajo lock exclusivo que transfer no usa.

Corrección recomendada: Validación runtime y lock compartido en todas mutaciones; para tabs almacenamiento transaccional con CAS/version o Web Locks.

Pruebas: Negativos qty0,-1,.5,NaN y same location; concurrencia same/tab y tabs, assert cantidades e IDs únicos/journal exacto.

Fuente: CONT03_core.json

## AM-01 — Grabador de atajos mantiene captura global tras guardar/cancelar/cerrar

Gravedad: LOW. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/CustomizeShortcutsDialog.tsx:54-95,98-118,213-215']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: handleStartRecording registra window.keydown preventDefault/stopPropagation; sólo Escape o timer30s lo desregistran. Save/Cancel/cierre no disponen del handler ni cleanup; Enter se guarda como nueva tecla aunque UI dice Enter para guardar.

Impacto: Bloquea escribir y atajos en formularios siguientes durante hasta30s; listeners se acumulan al editar consecutivos.

Reproducción: Abrir personalizar, grabar Ctrl+K, clic Guardar/Cancelar, cerrar, escribir en búsqueda/venta antes30s: evento sigue preventDefault. Enter tras combinación cambia binding a Enter en vez confirmar.

Corrección recomendada: Guardar referencia del listener y cleanup inmediato al terminar/cerrar/unmount; manejar Enter según texto UI.

Pruebas: React Testing Library fakeTimers: verificar typing después Save/Cancel/unmount y Enter confirma una sola combinación; contar listeners activos.

Fuente: CONT03_components-am.json

## AM-02 — Crear FAQ con categoría opcional falla contra contrato backend requerido

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/ManageFAQsDialog.tsx:94-111,177-185', 'src/lib/apiClient.ts:2199-2205', 'src/lib/inventoryServiceFactory.ts:2541-2542', 'backend/app/schemas/faq.py:9-17']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: UI etiqueta categoría Opcional y manda categoria:undefined cuando vacía; JSON.stringify omite campo, factory no añade default, FAQEntryCreate.categoria es str requerido. Pydantic local devolvió missing categoria.

Impacto: Ruta normal de creación con pregunta/respuesta válida falla422 pese formulario decir válido.

Reproducción: Crear Nueva FAQ; ingresar pregunta/respuesta sin categoría; enviar -> backend422.

Corrección recomendada: Alinear categoría obligatoria en UI o default explícito en backend; validar antes envío.

Pruebas: Integration API payload exacto de UI + UI error retaining form; considerar test category omitted/default.

Fuente: CONT03_components-am.json

## AM-03 — Filtros del centro de gráficas no filtran top productos ni resumen de sedes

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/DashboardStats.tsx:162-166,377-406,442-471,479-524,572-666,838-927']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: filteredOrders usa filtros; serviceTopProducts y serviceStatsByLocation provienen de consultas sin parámetros y siempre tienen prioridad si no vacíos. getRefundAmountInRange usa todos returnsData sin asociar a filteredOrders.

Impacto: Selector sede/fecha/canal/perfil aparenta cambiar todo, pero top y ventas por sede siguen globales/default30d; reembolsos de sedeB pueden descontarse de ventas sedeA.

Reproducción: API retorna top global P_B y summaries A/B; seleccionar filtro A donde sólo P_A vendió. Gráfica top mantiene P_B y resumen muestra B. Con refundB100 y saleA100 same date, filtered revenue A muestra0.

Corrección recomendada: Propagar scope/fechas a queries canónicas y generar todas gráficas desde mismo dataset filtrado, incluyendo devoluciones.

Pruebas: Render con datos A/B y mocks API global; activar cada filtro y verificar todas métricas/gráficas y returns comparten scope.

Fuente: CONT03_components-am.json

## AM-04 — Reporte de stock bajo ignora reservas y contradice alerta operativa

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/LowStockReportDialog.tsx:55-67', 'src/components/LowStockAlert.tsx:29-35']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: LowStockReport usa stockItem.cantidad_disponible, no stock_libre ni cantidad_reservada. LowStockAlert sí resta reservas.

Impacto: Reporte/export omite faltantes de stock libre y recomienda mal reposición cuando inventario está reservado en traslados.

Reproducción: Producto disponible10 reservado10 libre0: LowStockAlert agotado, LowStockReport no aparece por cantidad10>5.

Corrección recomendada: Usar stock_libre o max(disponible-reservado,0) en reporte. Definir significado de physical vs sellable uniformemente.

Pruebas: Render mismos products/locations en ambos componentes disponible10 reservado10, parcial y0; export debe coincidir.

Fuente: CONT03_components-am.json

## AM-05 — Control multitienda borra borradores al renderizar padre

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/MultiStoreControlDialog.tsx:488-545,550-568', 'src/App.tsx:2528-2551']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: App construye permissions={{...}} nuevo en cada render. availableTabs memo depende objeto permissions y loadData callback también. Efecto inicial depende availableTabs/loadData y mientras open reinicializa ubicación, receiptLines/countLines/scanner y tab.

Impacto: Refresco global o actualización unrelated del padre pierde líneas/capturas de compras/conteo sin advertir; cambia tab/sede durante trabajo.

Reproducción: Abrir Multitienda, seleccionar sedeB, añadir líneas y escanear; provocar rerender App conservando mismos permisos/locations/products con nuevo permissions literal -> vuelve sede inicial y borrador cero.

Corrección recomendada: Inicializar borrador sólo transición closed->open o reset explícito; depender flags primitivos/memo objeto y desacoplar carga de datos de reset de formulario.

Pruebas: RTL rerender con permissions:{...sameValues}; verificar drafts/tab/selections permanecen; rerender productos actualizado y heartbeat padre.

Fuente: CONT03_components-am.json

## AM-06 — Configuración IA puede guardar respuesta de perfil anterior en perfil actual

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/AIProfileConfigDialog.tsx:39-65,71-82']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: loadConfig(id) setConfig sin abort/generation/id guard; handleSave usa salesProfileId de props actual sobrescribiendo sales_profile_id del config. Cambiar/reabrir mientras requestA pendiente y resolverA despuésB mezcla contenido.

Impacto: Personalidad/política/tasa/estado IA de un bot puede sobrescribir otro inadvertidamente.

Reproducción: ConfigA GET lento; cerrar/cambiar salesProfileIdB/reabrir; GET B resuelve y luego A; Guardar usa URLB pero {...configA,sales_profile_id:B}.

Corrección recomendada: Reset inmediato por id y ignorar/abortar respuesta antigua; guardar sólo config cargada para id actual.

Pruebas: Deferred promises por id con orden inverso, abrir/cerrar/seleccionarB y guardar; nunca persistir A en B.

Fuente: CONT03_components-am.json

## AM-07 — Desglose de cierre diario atribuye pago mixto entero al método principal

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/DailyCloseDialog.tsx:44-55,146-153,320-331', 'backend/app/routers/daily_close.py:69-86', 'backend/app/schemas/daily_close.py:28-41']; ['_build_order_summary']

Evidencia concreta: DailyCloseOrder/summary omiten payment_breakdown; UI agrupa order.total completo por order.metodo_pago. Backend de cierre por sede sí contabiliza componentes, por tanto dos pantallas difieren.

Impacto: Responsable conciliación ve efectivo/transferencias/card incorrectos y puede aprobar cierre con supuesto desglose falso.

Reproducción: Orden total100 cash40 transferencia60 con metodo_pago=efectivo; daily-close muestra Efectivo100 y transferencia0.

Corrección recomendada: Incluir breakdown en API summary y sumar cada componente; si no hay datos no llamar desglose conciliable.

Pruebas: Crear venta mixta y comparar pending summary/UI vs cierre location_expected, sumas por componente.

Fuente: CONT03_components-am.json

## AM-08 — Editor de accesos por sede no carga permisos existentes

Gravedad: MEDIUM. Estado: CONFIRMED_STATIC. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['src/components/MultiStoreControlDialog.tsx:199-207,903-936,1486-1506']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: accessFlags inicia can_view=true restofalse y sólo cambia por Checkbox; seleccionar user/location nunca llama listUserLocationAccess ni setAccessFlags existente. Guardar recupera acceso pero elimina selected location y lo reemplaza con flags del formulario desinformado.

Impacto: Editar un permiso puede revocar otros existentes o aplicar flags del usuario anterior a nuevo usuario inadvertidamente.

Reproducción: UsuarioA/sedeA tenía can_edit y can_close_cash=true. Seleccionarlo UI muestra false; marcar can_count_stock y guardar reemplaza ambos antiguos false. Seleccionar usuarioB conserva flagsA.

Corrección recomendada: Cargar flags seleccionados antes permitir edición/guardar; distinguir crear de editar y reset al cambiar objetivo.

Pruebas: RTL/API muestra flags existentes al seleccionar y cambio puntual preserva no editados; cambio user/location y races loaders.

Fuente: CONT03_components-am.json

## CONT03-PDF01 — PDF imprime campos negocio como HTML activo sin escape

Gravedad: MEDIUM. Estado: REPRODUCED_HTML_INJECTION_XSS_CONDITIONAL. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['src/lib/pdfExport.ts:5,245-254,266,310-314,400-403,479', 'src/lib/pdfExport.ts:529,677-685,704', 'backend/app/schemas/order.py:262-276', 'backend/app/utils/validators.py:142-169']; ['validate_text_field']

Evidencia concreta: Interpolaciones customer_name, notas, nombre/marca/modelo producto, perfil y campos financiación directamente en string HTML y document.write popup about:blank. Fixture con customer_name=<img src=x onerror=...> se conserva literalmente. Backend validate_text_field permite caracteres especiales y no invoca sanitize_html.

Impacto: Manipular visualmente recibo/reportes con etiquetas arbitrarias y contenido falso. Ejecución JavaScript potencial en desarrollo u origen sin CSP restrictiva; NO confirmada en producción.

Reproducción: Transpilar pdfExport.ts con typescript.transpileModule; stub window.open.document.write captura HTML generado. generateOrderPDF fixture con customer_name marcado confirma includes(input)=true. No solicitudes reales ni carga de payloads externos.

Corrección recomendada: Construir documento con textContent/nodos DOM o escapar toda interpolación HTML; separar documento imprimible de strings no confiables y conservar CSP.

Pruebas: Campos con < > comillas y markup deben quedar texto; prueba navegador local con CSP idéntica producción y opener; validar impresión automática bajo CSP.

Fuente: CONT03_utils.json

## CONT03-OPT01 — Optimización cuenta órdenes canceladas/pendientes como demanda y compras reales

Gravedad: MEDIUM. Estado: REPRODUCED_ISOLATED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['src/lib/optimizationAnalytics.ts:111,131-141,198-209,282-300,376-391', 'src/hooks/use-optimization-insights.ts:30-49']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Todos análisis reciben profileOrders filtrados sólo por perfil, sin isFinalSaleStatus; ventas recientes, total vendido, VIP y revenue incluyen estados no finales. _completedOrders se declara pero no utiliza (línea527).

Impacto: Falsa demanda, recomendaciones de precios/reposición y clasificación clientes VIP a partir de compras canceladas.

Reproducción: Producto stock20/precio1000 y una orden cancelada reciente cantidad24 produce underpriced suggestedPrice1080 potentialImpact1920; demanda real cero.

Corrección recomendada: Separar ventas finales de pipeline/cancelaciones; aplicar effective sale date consistente en cálculos ventas.

Pruebas: Canceladas y pendientes no suman vendido/revenue/VIP; ventas finalizadas sí. Fecha contable cruzando meses como extensión AN-001.

Fuente: CONT03_utils.json

## CONT03-OPT02 — ProductMix declara pérdidas con costo supuesto basado en catálogo actual

Gravedad: MEDIUM. Estado: REPRODUCED_ISOLATED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['src/lib/optimizationAnalytics.ts:380-391,413-429']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: profit=totalRevenue-totalQuantity*product.precio*0.6 ignora OrderItem.costo_unitario y Product.costo, sin convertir producto USD. Se presenta como productos vendiendo por debajo del costo, no como estimación.

Impacto: Cambiar precio catálogo altera retroactivamente pérdida histórica y puede aconsejar descontinuar producto rentable.

Reproducción: Venta HNL100 con costo_unitario90 (margen10) y precio actual1000 retorna poor_performer impact500.

Corrección recomendada: Usar costo histórico entregado de todos items, incluyendo regalos, y fallback legacy explícito coherente; no llamar pérdida real a un supuesto60%.

Pruebas: Costo histórico independiente precio actual; costos regalos; USD catálogo con ledgerHNL.

Fuente: CONT03_utils.json

## CONT03-OPT03 — Clientes sin teléfono se fusionan como un único VIP

Gravedad: LOW. Estado: REPRODUCED_ISOLATED. Evidencia: REPRODUCED_ISOLATED.

Archivo/función: ['src/lib/optimizationAnalytics.ts:282-299,307-316']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: customer_phone vacío comparte key unknown, conserva primer nombre y suma todas órdenes de clientes distintos.

Impacto: Segmentación/recomendaciones lealtad atribuyen compras ajenas al primer comprador. Principalmente datos legacy/local con teléfono vacío.

Reproducción: Tres órdenes total2000 con teléfonos vacíos y customer_name distintos producen VIP Distinct0 total6000 compras3.

Corrección recomendada: Usar customer_id estable cuando exista o ignorar identidad desconocida en métricas individuales; no fusionar todos unknown.

Pruebas: Tres compradores distintos sin teléfono no se clasifican como un VIP único.

Fuente: CONT03_utils.json

## CONT03-DEP01 — Lockfile conserva161 entradas sin origen ni hash integridad

Gravedad: LOW. Estado: CONFIRMED_STRUCTURAL. Evidencia: CONFIRMED_STATIC.

Archivo/función: ['package-lock.json (722 package entries,161 sin resolved/integrity;89 no dev)']; ['Bloque/configuración/render identificado en ubicaciones y evidencia del informe fuente']

Evidencia concreta: Parser recorrió todas entradas y dependencias; ninguna entrada con resolved carece integrity, pero161 entradas carecen ambos, incluyendo producción @floating-ui, @heroicons/react y @radix-ui/colors. No paquetes git/file/host ajeno ni peer/dependency faltantes detectados.

Impacto: Esas instalaciones no quedan fijadas a hash del tarball y dependen resolución registry local. No evidencia de paquete malicioso ni CVE nueva.

Reproducción: None

Corrección recomendada: Regenerar lockfile en entorno limpio con registry esperado; inspeccionar diff y gates existentes; documentar Node mínimo22.20 por lzma en linux-x64.

Pruebas: npm ci limpio plataforma producción + lint/tests/build y auditoría dependencias; no instalar durante auditoría lectura.

Fuente: CONT03_utils.json


## CH-007 — Métricas canales nunca reciben eventos

MEDIUM; CONFIRMED_STATIC. Ver CONT03_INSTRUMENTACION.json para archivo/función, evidencia, impacto, reproducción y pruebas.
