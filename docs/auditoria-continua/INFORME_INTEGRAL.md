# Informe integral de código y operación — SoftMobile

## Dictamen

**No listo para certificar producción.** Se completó la revisión estática de los653 archivos de la línea base main `dba6763391d12c6c91c9904cba36725710f9280a`:652 leídos íntegramente (99,85%) y package-lock revisado exhaustivamente por estructura (722 entradas). Cobertura estática100%; pruebas, configuración externa y validación operacional no están100%. No se modificó código ejecutable, no se fusionó ningún PR y no se desplegó ni alteró información real del negocio.

El servicio responde y permite llegar a login. Esto demuestra disponibilidad de esa frontera, no integridad comercial. Con fallos confirmados de stock, IMEI, permisos y reportes, **no recomiendo usarlo como única fuente confiable de inventario, ventas o contabilidad hasta resolver bloqueantes y probarlos**. No se afirma que todas las operaciones actuales estén fallando.

## Alcance y trazabilidad

GitHub main confirmado sin cambios; PR144 dependencias, PR147 draft ejecutable y PR146 documental siguen abiertos. Todos653 blobs locales coinciden con línea base. La documentación de este PR registra archivo, estado, blob y evidencia; no cuenta documentos nuevos para inflar denominador. Se revisaron llamadas y rutas canónicas: las funciones legacy reemplazadas no se confunden con handlers activos. El PR147 toca legacy; no prueba remediación del handler vigente. PR144 queda fuera de la certificación de main y requiere sus propios tests antes de una eventual fusión autorizada.

## Estado por módulo

| Módulo | Estado basado en evidencia |
|---|---|
| Backend/API y servicios | Lectura completa; guards y overrides reconciliados. Atomicidad/auditoría/idempotencia tienen fallos y riesgos pendientes. |
| Inventario/reservas/stock | BUS01 y BUS08 bloqueantes; ajustes/reservas agregadas requieren regresiones concurrentes PostgreSQL. |
| IMEI/seriales | BUS02/03/04/05; Restock conserva serial de otro producto; integridad física y pertenencia no certificadas. |
| Compras/proveedores/costos | Regresiones PG de locks/identidad son sustantivas, pero valoración mezcla monedas; operaciones masivas y costo histórico requieren cierre. |
| Ventas/pagos/financiamiento | Pago mixto frontend incompatible; backend guard rechaza inconsistencia. Reintentos sin idempotencia y formulario borrado en error; ledger/audit parcial. |
| Transferencias/multitienda | Cero recibidos mueve seriales, batching parcial y truncado50; cancelación admin concurrente es riesgo aún no probado PG. Borradores UI reseteados por rerender. |
| Devoluciones/garantías/retomas | Serial de producto cruzado, falta reemplazo, IMEI sobrescrito; activar retoma+traslado2 operaciones no atómicas. |
| Reportes/contabilidad/cierre | Regalías fuera de costo, fecha creación en lugar venta, monedas mezcladas, desglose mixto UI falso, optimización incluye canceladas y costo ficticio. |
| Auth/RBAC/seguridad | JWT/RBAC existen, pero endpoints IA/forecast y serializers filtran indebidamente alcance por sede; cambio contraseña no revoca JWT anterior. |
| Frontend/UI | Todos componentes leídos; catálogo público falla observado en browser, guardado/errores/doble submit/borradores requieren E2E. No prueba botón por botón autenticada. |
| WhatsApp/Messenger/Instagram/n8n/IA | HMAC12 casos aislados aprobados. Persisten dedup/recuperación/fotos/canal/contrato n8n; IA real deshabilitada y credenciales externas no verificadas. |
| Docker/entorno/despliegue/backups | Compose backup efímero y gate métricas incompatible; VPS real systemd diverge, release desconocido, offsite obligatorio sin destino. Restore/DR actual no ejecutado. |
| PostgreSQL/migraciones | CI513 tests PG16 aprobados. Migraciones y locks revisados; nuevos defectos/races sin regresión PG; SQLite migración Decimal falla. |
| Pruebas/dependencias/workflows | Main CI/release gate aprobados, oráculos/gaps identificados. npm audit0 advisories conocidos, no ausencia garantizada de vulnerabilidades. |
| Docs/scripts/mode local | Instrucciones obsoletas/destructivas y demo seed sobrescribe stock. LOCAL01-09 exclusivos local/dev, no asignados a producción API-only. |

## Gravedad y certeza

Registro vigente: **110 entradas provisionales**, {'HIGH': 34, 'MEDIUM': 63, 'LOW': 12, 'INFORMATIONAL': 1}. Cero CRITICAL asignados; no conclusión de inexistencia. El total incluye observaciones documentales/pruebas/local y no debe venderse como número de vulnerabilidades distintas. Detalle con ubicaciones/evidencia/impacto/repro/recomendación/pruebas en HALLAZGOS.json/md y bloques.

Confirmados mediante reproducción aislada: consumo de reserva ajena por venta; recepción cero mueve seriales; garantía producto cruzado/sin reemplazo; retoma sobrescribe serial; CSV comillas; margen de regalías; sincronización IDs y pérdida de diario; métricas y contexto logs; backup falso éxito; migración SQLite. Mocks y SQLite no certifican PostgreSQL. Confirmados estáticamente: contratos/UI y controles descritos en registros; browser observó catálogo fallido. Riesgos pendientes: SA01 carrera cancelación/confirmación; SA02 purga condicional (deshabilitada en producción); ejecución JS de PDF no demostrada y CSP self mitiga inline. No se hizo tráfico de explotación, purga, carga ni cambio de datos reales.

Rectificaciones: FE01 ya no afirma persistencia corrupta de pagos; ORM before_flush rechaza/rollback. CH002/003/004 históricos no se contabilizan como defecto actual del handler reemplazado. Inyección HTML PDF confirmada no se presenta como XSS ejecutado en producción.

## Funcionalidades incompletas o desconectadas

Catálogo público no obtiene productos en prueba real y contacto WhatsApp hardcodeado de ejemplo; sólo primera página100 frente189 públicos. n8n tiene contrato training inválido y flujo no acredita envío real Meta. Métricas de eventos de canales tienen definiciones sin incrementos/callers según bloque security. Configuración técnica de canales usa estado comercial anterior. IA/email reales deshabilitados/no configurados según snapshot. Persistencia local y diario no tienen atomicidad completa; producción estándar fuerza API y no usa esas ramas. Botones de reparación local en producción generan éxito sin corrección backend. Reportes y forecasts no acreditan calidad financiera ni precisión predictiva por compilar.

## Pruebas: aprobadas, fallidas, omitidas y no ejecutadas

| Evidencia | Resultado | Límite |
|---|---|---|
| CI main PG16 | 513passed,71% backend cobertura | Resultado automatizado observado en logs; oráculos y casos faltantes permanecen. |
| CI y ejecución frontend local |49passed/21 archivos,19,89% líneas; lint/build exit0 | Mocks y compilación; no certifica flujos de usuario. |
| E2E SQLite y health local |9passed | Fixtures temporales; no concurrencia PG. |
| E2E PG CI |1passed | Acepta algunas respuestas500/503 del competidor; no demuestra rollback íntegro. |
| Shell deploy mock |5 suites exit0 | Sin deploy real. |
| HMAC continuación03 |12assertions aprobadas:200 válida,401 ausente/incorrecta/alterada | Tres canales; cuerpos vacíos, NoDB; no entrega Meta. |
| npm audit continuación03 |exit0;0 advisories conocidos | Cobertura registry/advisories, no audit código ni supply-chain certificado. |
| Probes de fallos anteriores |Defectos reproducidos, no aprobación de negocio | SQLite/mocks y helpers en memoria. |
| Browser público |Catálogo falló fetch; / llega a login | No sesión autenticada ni modificaciones. |
| PG local continuación03 |No ejecutado | pgserver instaló binario16.2; useradd/setgroups bloqueados, ningún servidor iniciado. |
| Browser local Playwright |No ejecutado | Chromium ausente/descarga fallida. Browser cloud permitió lectura pública parcial. |
| Informe VPS histórico |474SKIPPED | Omitidas no son aprobadas. |

Pruebas autenticadas botón por botón, todas las carreras PG nuevas, entrega efectiva proveedores y restauración offsite actual: **pendientes**, no aprobadas por inferencia. Ninguna suite disponible falló en ejecuciones aprobadas indicadas; los probes sí detectan fallos del producto. Notebooks/prints manuales sin asserts no cuentan como tests aprobados.

## Preparación operacional real

Health/ready200 con PG conectado, Uvicorn4workers systemd. Snapshot de código VPS dba-equivalente en144 backend/app, pero checkout antiguo/sucio y2 src diferentes, sin APP_BUILD_SHA/X-Release-SHA conocido. No garantiza bundle servido ni memoria proceso corresponda al main. IA false/email ausente/MetaSecret ausente; require_offsite true con destino vacío. No se reemplazó configuración ni se restauró negocio. DR reportado anteriormente no equivale a un drill fresco del estado actual ni confirma offsite.

## Plan de corrección ordenado por dependencia y gravedad (NO iniciado)

1. **P0 recuperación y aislamiento antes de cambios:** definir backup offsite real, restaurar copia en entorno descartable y probar invariantes; fijar SHA/build/provenance y evitar modificación fuera GitHub. Acordar evidencia de recuperación antes de migraciones.
2. **P1 inventario transaccional y autoridad:** resolver reserva por dueño, estados de orden/traslado, locks coherentes y rollback único; IMEI pertenencia/uniqueness/retoma/garantía; oráculos PG exactos. Añadir regresiones fallidas antes de corregir, incluyendo concurrencia y stock sobrante.
3. **P1 permisos y side effects:** cerrar leaks de sede en serializers/IA/forecast, exigir orders:create en IA, revocar tokens según política aprobada; idempotencia en creación negocio/consumidores y commit audit coherente. Depende del modelo de transacción estable.
4. **P1 contratos frontend/backend:** pagos mixtos/financiación y cierres; conservar formulario ante error; bloquear doble submit; batching transaccional; seriales atados a producto; estado perfil correcto; drafts estables. Tests componentes +PG API+E2E descartable.
5. **P1 canales y sync:** dedup por cuenta/canal/cliente, durable outbox/retry/manual recovery, canal fotos, contratos n8n; mapear IDs/remapear FKs y bloquear dependencias fallidas; diario que preserve pendientes. Configurar credenciales externas sin exponerlas; probar mensajes sintéticos en cuentas de prueba.
6. **P2 finanzas y reportes:** moneda base/conversión, costo real/histórico incluidos regalos, fecha efectiva venta y devoluciones, desglose pagos mixtos. Conciliar API/UI/exports con fixtures conocidos.
7. **P2 operación y seguridad complementaria:** backup exitcodes/volúmenes/restore atómico/gates rutas/env/bootstrap; limitar cardinalidad métricas, contexto por tarea y Sentry único; escapar HTML/CSV, corregir catálogo/contacto/paginación.
8. **P3 ramas local/demo/UI/documentación/dependencias:** aislar demo/reseed, atomizar local si se mantiene soporte, mejorar oráculos/accesibilidad/errores/documentos/Copilot, fijar integridad lock. PR144 se prueba aparte; no usar upgrade para esconder bugs de negocio.
9. **Gate de salida:** suites/regresiones nuevas PG16, navegador aislado con todos roles/sedes/flujos y negativos; validar prod-gate y restore/offsite reales, reauditar diffs, desplegar sólo tras autorización posterior.

## Condiciones exactas para declarar100%

- Cobertura de todos archivos/blobs del SHA final y cualquier cambio posterior reauditable; revisión estática ahora satisfecha únicamente para la línea base indicada.
- Cada hallazgo con corrección probada o aceptación explícita justificada; ningún HIGH/bloqueante de inventario, pagos, permisos o recuperación abierto.
- Invariantes concurrentes PG16: cantidades conservadas, reservas por dueño, IMEI único/perteneciente, estados válidos, ni efectos parciales ni duplicados ante retry/rollback.
- Conciliación de dinero/moneda/costos/retomas/regalías/pagos/financiación/cierres/devoluciones con fixtures y consultas DB exactas.
- E2E de todos flujos críticos y botones aplicables en entorno aislado, roles/sedes y negativos; errores sin perder borradores ni anunciar éxito falso.
- Meta/n8n/IA/email configurados con pruebas reales controladas, HMAC, aislamiento cuentas, recuperación de mensajes, sin side effects duplicados.
- SHA desplegado verificable limpio/GitHub; CI final y prod-gate con configuración real aprobados; backup offsite verificado y restauración DR fresca comprobada.
- Diferenciar código implementado, probado, integrado, desplegado/configurado y funcionamiento real. Las seis etapas deben tener evidencia; compilar/health200 no sustituye ninguna.

**La revisión estática terminó; la auditoría operacional permanece abierta en los puntos de prueba explícitos. La fase de corrección espera autorización del usuario.**
