# SoftMobile OpenClaw Supervisor v1

Entorno: VPS srv1656045. Este módulo complementa, NO sustituye ni reconfigura, Chatwoot, el vendedor IA, el laboratorio y el sistema de inventario.

## Funciones implementadas
- Audita todas las conversaciones del buzón 2 de la cuenta 2 (hasta 5,000 para limitar carga). No extrae nombres, teléfonos ni contenido de mensajes.
- Valida cotizaciones de los últimos siete días sin extraer textos de clientes; aplica política de consentimiento explícito, exclusión de contactos, traspaso a humano, cliente que respondió, seguimiento duplicado, plazo de 2 a 24 horas y estado del transporte piloto. Clasifica oportunidades para revisión humana; no envía mensajes.
- Detecta consultas sin responder y propuestas de seguimiento, con consentimiento separado. NO envía mensajes.
- Lee agregados de inventario_db (productos, existencias, órdenes) y la cola de solicitudes de fotografías en modo solo lectura.
- Lee las pruebas locales del laboratorio y distingue resultado local de auditoría independiente.
- Comprueba contenedores Docker principales, estado de WAHA/Redis, memoria y disco.
- Escribe un resumen y un JSON para OpenClaw. El agente crea su propia revisión diaria con propuestas sujetas a aprobación.

## Director operativo multiarea (segunda etapa)
- El director `director.py` lee únicamente el informe saneado del supervisor y agrega datos SQL de solo lectura. Valida que el informe sea reciente, alcance la cobertura completa y que el envío comercial esté bloqueado.
- Produce `DIRECTOR.json` y `DIRECTOR.md`: tareas verificables para ventas, inventario, operaciones, finanzas, calidad, infraestructura, publicidad y desarrollo. Sin datos suficientes, marca la integración como bloqueada (no inventa métricas).
- El servicio director se ejecuta tras cada supervisor exitoso mediante `OnSuccess`; su timer independiente se deshabilitó para no duplicar trabajo.
- OpenClaw genera informes especializados: ventas a las 09:30 diario, operaciones a las 09:50 diario, calidad y código martes/jueves/sábado a las 10:15. Todos en `America/Tegucigalpa`, con `--tools read,write`, `--no-deliver`, sesiones aisladas y límite de ejecución.
- Archivos: `SALES_REVIEW.md`, `OPERATIONS_REVIEW.md`, `ENGINEERING_REVIEW.md` en la misma carpeta de reportes.
- Para pruebas: `python3 -m unittest discover -q -p 'test_*.py'`; para ejecución: `systemctl start softmobile-openclaw-director.service`.
- El director integra solo los **agregados anonimizados** de la revisión sintética cuando existe `issue-triage-report.json` y un `offline-issue-replay-report.json` reciente, con 0 llamadas API, 0 mensajes públicos y 0 promociones. Los 250 casos son conversaciones ficticias y las señales no prueban errores comerciales reales.
- Se reactivó `softmobile-issue-triage.timer` (cada 30 minutos) y `softmobile-offline-issue-replay.timer` (cada hora, override `90-softmobile-hourly-safety.conf`): replay en Ruby desechable sin red, 200 MB por contenedor, sin despliegues.
- La conectividad de Meta Ads desde el VPS sigue sin fuente utilizable. La cuenta externa de analytics puede aparecer autenticada pero los conectores requieren suscripción/plan para retornar datos; no declarar campañas optimizadas ni gastos verificados.
- Para detener la cadena reactiva, quitar los overrides `OnSuccess` de forma controlada y recargar systemd. Para detener el QA adicional: `systemctl disable --now softmobile-issue-triage.timer softmobile-offline-issue-replay.timer`. Para detener las revisiones de IA, deshabilitar sus trabajos individualmente con OpenClaw cron; no afectan el supervisor.

## Ejecutor interno y embudo comercial ficticio (tercera etapa, PRELANZAMIENTO)
- La cadena se inicia con el supervisor a las `:08/:38` UTC; tras cada éxito, el director, ejecutor, router y certificado se activan inmediatamente mediante `OnSuccess`. Si las fuentes cambian entre lecturas, el ejecutor se detiene (fail-closed).
- `pilot_executor.py` procesa solo los IDs de tarea autorizados, coteja datos y evidencia sin PII, mantiene `operator.sqlite3` con historial deduplicado e informa en `OPERATOR.json` y `OPERATOR.md`. Acciones reales permitidas: SQL `BEGIN TRANSACTION READ ONLY`, comprobaciones de fotos en SQLite lectura, contenedores mediante Docker inspect y pruebas unitarias acotadas.
- `softmobile-pilot-executor.timer` está deshabilitado (ahora el servicio se activa con `OnSuccess`); `softmobile-pilot-executor.service` usa `ProtectSystem=strict`, `ReadWritePaths` limitado, `IPAddressDeny=any`, `RestrictAddressFamilies=AF_UNIX`, memoria 192 MB. Por compatibilidad con `runuser -u postgres` y autenticación local peer, el ejecutor usa `NoNewPrivileges=false`; **conserva bloqueo de red, sistema de archivos de solo lectura, allowlist fija y no tiene ninguna acción de escritura comercial**. No instalar extensiones de sistema en este proceso.
- Las 14 tareas del director se transforman en verificaciones internas, alertas de revisión humana y pendientes de QA; las bloqueadas siguen bloqueadas. Ninguna acción produce mensajes, cobros, movimientos de stock ni despliegues.
- `softmobile-sales-conversion.service` comprobó 72 escenarios ficticios (compra, financiamiento, negociación, reserva, envío y accesorios), 72 aprobados y 9 checkouts **simulados**. 0 ventas, 0 pedidos y 0 mensajes reales. El director incluye este resultado en `synthetic_sales`; el ejecutor lo revisa y escala regresiones.
- `softmobile-sales-conversion.timer` se activó con override `zz-softmobile-prelaunch-safe-cadence.conf` (cada 4 horas a `:26` UTC, en lugar del antiguo acelerado cada 30 min). Usa contenedores desechables sin red.
- Pruebas: `python3 -m unittest discover -q -p 'test_*.py'`; ejecución real de cadena: `systemctl start softmobile-openclaw-supervisor.service; systemctl start softmobile-openclaw-director.service; systemctl start softmobile-pilot-executor.service`.
- Desactivar al ejecutor: `systemctl disable --now softmobile-pilot-executor.timer`; desactivar simulación: `systemctl disable --now softmobile-sales-conversion.timer`.

## Coordinación reactiva y certificación de prelanzamiento (fase siguiente)
- Cadena **OnSuccess** systemd verificada: `softmobile-openclaw-supervisor.service` → `softmobile-openclaw-director.service` → `softmobile-pilot-executor.service` → `softmobile-event-router.service` → `softmobile-release-gate.service`. Ante error en cualquiera de las etapas, la cadena se detiene sin activar público.
- `softmobile-openclaw-supervisor.timer` sigue cada 30 minutos (único disparador periódico de esta cadena); se deshabilitaron los timers independientes del director y ejecutor para evitar ejecuciones redundantes. Esto es reacción a **nuevos snapshots internos**, NO webhook instantáneo de WhatsApp.
- `event_router.py` conserva `events.sqlite3` sin PII, genera `EVENTS.json` y `EVENTS.md`, detecta eventos `detected`, `changed`, `not_observed` y `reappeared` sin duplicar resultados ni marcar desaparición como cierre. Cada tarea recibe responsable especializado (ventas, operaciones o ingeniería).
- Ante eventos prioritarios que requieren revisión, el router puede despertar el job OpenClaw especializado mediante **IDs fijos**, validando sesión aislada, `toolsAllow=['read','write']`, `delivery.mode='none'`, que esté habilitado y que no use shells. Máximo tres revisiones reactivas por día (entre todas las especialidades); revisiones diarias independientes continúan. Si no se verifica un job, no se ejecuta.
- `softmobile-event-router.service`: sandbox de solo lectura del sistema, sin red externa, máximo 128 MB. Se probó que puede iniciar una revisión restringida del especialista de ventas desde el mismo sandbox.
- `release_gate.py` y `softmobile-release-gate.service` generan `CERTIFICATION.json` y `CERTIFICATION.md`; verifican consistencia de snapshots, cobertura de Chatwoot, pruebas de vendedor, seguridad, transporte y demás fuentes. El permiso de lanzamiento siempre es `False`, aun con todas las pruebas técnicas satisfechas.
- Estado de aceptación 7 nov: 117 pruebas locales aprobadas; los cinco servicios terminan con estado success. La certificación señala **5/15 controles positivos, 6 bloqueos comerciales y 10 bloqueos de autonomía completa**. Cero mensajes públicos.
- Para desactivar la nueva ruta reactiva: quitar los overrides `90-softmobile-on-success-*.conf`, `90-on-success-release-gate.conf` y ejecutar `systemctl daemon-reload`. No borrar informes ni historiales; programaciones del supervisor y otros laboratorios pueden mantenerse.
- Plan de fases y criterios de aceptación: `ROADMAP.md`. Fases comerciales reales, reparaciones y Meta Ads **NO** están terminadas y requieren datos, pruebas/consentimiento y autorizaciones que todavía no constan en el VPS.

## Corrección aislada del vendedor piloto: reclamo por pedido dañado
- Un caso realista en un ensayo ficticio mostró que **«Mi pedido llegó roto, ¿lo dejan en la puerta?»** se clasificaba erróneamente como `tracking`, porque el detector temprano de reclamos no reconocía `mi pedido` + `llegó` + `roto`. El flujo correcto es `complaint` con traspaso a humano, sin prometer cambios/devoluciones.
- `stage_damage_priority.py` creó un parche mínimo (solo tres condiciones tras el detector de credenciales), exigió que coincidiera el ancla exacta y mantuvo `PILOT_CONVERSATION_ID=3`, `INBOX_ID=2` y `AUTO_REPLY_LIMIT=1`.
- Antes de instalarlo se verificó Ruby syntax, 72/72 recorridos comerciales (sin promesas inventadas), 3/3 prioridades críticas, 117/117 regresiones Ruby y 250 incidencias ficticias sin indicadores nuevos respecto al baseline.
- Se incorporó SOLO al archivo Ruby del piloto `/opt/softmobile-waha-test/sales-bot-v2.rb` tras revisar SHA, consentimiento y guardas de publicación. SHA instalado `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1`. Backup de reversión: `/opt/softmobile-waha-test/quality-backups/sales-bot-v2.rb.before-damage-priority-20261108T011016Z.bak`.
- Regresión después de instalar: 118/118 pruebas del supervisor, 62 pruebas del laboratorio sin fallos (1 skip porque una propuesta anterior está vinculada a otro hash), 72/72 simulaciones con SHA del código actual. No se modificó la activación de mensajes públicos.
- El generador de *nuevas propuestas automáticas* sigue detenido por `trusted_source_drift` de su otra ancla; esta corrección específica no supone aprobar ese generador ni cerrar QA independiente. El PR documenta el diff exacto. El bot no está listo para clientes reales hasta completar los demás bloqueos.

## Preparación de propuestas de código
- `patch_proposer_capped.py` limita el generador existente de parches IA a **4 llamadas Groq por día** incluso si la configuración global de desarrollo es ilimitada.
- La unidad tiene override `95-softmobile-proposal-budget.conf`: mismo candado de concurrencia, máximo de 384 MB y 150 segundos.
- Pruebas: 4 del presupuesto + 17 originales del generador y su validador aprobadas.
- La ejecución manual del 7 nov devolvió `trusted_source_drift`: la estructura Ruby actual ya no coincide con el ancla exacta esperada. No se aplicaron cambios, no se generó un nuevo parche y **no se habilitó su timer** hasta revisar ese desfase.
- El generador solo puede preparar parches en archivos privados para revisión humana; nunca desplegar ni modificar conversaciones de clientes.

## Ejecución en VPS
- Código activo: /opt/openclaw-lab/supervisor/supervisor.py
- Pruebas: /opt/openclaw-lab/supervisor/test_supervisor.py y test_followup_policy.py
- Motor comercial sin envío: /opt/openclaw-lab/supervisor/followup_policy.py
- Servicio: softmobile-openclaw-supervisor.service
- Timer: softmobile-openclaw-supervisor.timer (cada 30 minutos)
- Salidas internas: /opt/openclaw-lab/workspace/softmobile-supervisor/STATUS.md y latest.json
- Análisis del agente: /opt/openclaw-lab/workspace/softmobile-supervisor/AGENT_REVIEW.md
- OpenClaw cron: 7dd7767a-e001-4646-a635-85b960a52053; diario 09:15 America/Tegucigalpa; sin envío externo.

## Pruebas y límites
Pruebas unitarias (sin red): python3 -m unittest discover -v -p 'test_*.py'
Prueba de integración: systemctl start softmobile-openclaw-supervisor.service
Revisión: systemctl status softmobile-openclaw-supervisor.service
Desactivar supervisión si es necesario: systemctl disable --now softmobile-openclaw-supervisor.timer

Estado observado 2026-11-07: 9/9 conversaciones evaluadas, 1 pendiente, ninguna nueva en 24h.
Inventario DB: 106 unidades disponibles, 135 productos activos sin stock, 458 registros de órdenes con estado pendiente (no verificar como ventas reales).
Fotos (cola de pruebas): 4 completadas, 1 cancelada, 1 pendiente de revisión.
Laboratorio: 492 pruebas locales aprobadas, sin confirmación de convergencia independiente.
WAHA y Redis del stack de PRUEBAS WhatsApp estaban detenidos. NO se reiniciaron. El 2026-11-06 ~23:11 UTC hubo una parada coordinada de varios servicios y temporizadores; no se ha demostrado un OOM aislado. El buzón 2 es Channel::Api (WhatsApp - SoftMobile (prueba WAHA)). No declarar caído un canal productivo por este dato.
La ejecución de seguimiento comercial está bloqueada por compuertas de salida. Ninguna prueba técnica, por sí sola, autoriza mensajes al público.

## Seguridad
- Solo lectura a Chatwoot mediante Rails runner con cuenta y buzón fijos.
- No modifica inventario, presupuestos, precios, campañas o código en producción.
- No publica WhatsApp ni Chatwoot; ninguna respuesta sale automáticamente.
- Cuando supera 5,000 conversaciones, falla con alerta en vez de omitir datos y declarar cobertura total.
- Informes internos incluyen IDs de conversaciones; no deben publicarse.
- Mantener la aprobación humana para propuestas y cambios de infraestructura.

## Pendientes no implementados
Recuperación real de ventas, seguimiento comercial consentido masivo, sincronización transaccional de inventario con Chatwoot, anuncios Meta, finanzas reales, reparaciones y remediación automática de errores requieren integración y pruebas adicionales. No confundir esta primera versión con un sistema autónomo comercial completo.


## Estado de trabajo SIN WhatsApp — actualización 7 nov 2026 HN / 8 nov UTC
El usuario decidió dejar WhatsApp para la última fase. **No tocar WAHA, ni la salida pública, ni pagos, anuncios o compras.** Las automatizaciones internas siguen en marcha.

### Cadena systemd actual
`softmobile-openclaw-supervisor.service` → `softmobile-openclaw-director.service` → `softmobile-pilot-executor.service` → **`softmobile-finance-audit.service`** → **`softmobile-repair-workflow-lab.service`** → `softmobile-event-router.service` → `softmobile-release-gate.service`. La cadena se ejecuta por `OnSuccess` de cada etapa y comienza desde el timer del supervisor cada media hora. Si falla una etapa, no se dispara la siguiente. El router añade `finanzas_auditoria` a la cola de tareas y solo expone datos agregados.

### Auditoría financiera
`finance_audit.py` usa PostgreSQL `BEGIN TRANSACTION READ ONLY`, sin nombres, teléfonos, comprobantes ni referencias bancarias. Informe `FINANCE_AUDIT.json`/MD. **458 órdenes pendientes, cero completadas, cero cierres diarios**; no se puede afirmar ingresos o utilidad. Se detectaron **173 diferencias entre total y suma de líneas:** 96 tarjeta, 57 financiamiento, 14 transferencia y 6 efectivo. Estas cifras NO son pérdidas probadas: tarjeta/financiamiento pueden incluir recargos. También hay **3 productos activos con precio bajo costo**, pendientes de revisar promociones y datos. Nunca cerrar órdenes ni modificar pagos automáticamente.

### Reparaciones
`repair_workflow.py` implementa **únicamente el dominio ficticio** de recepción, diagnóstico, presupuesto, aprobación humana, repuestos, reparación, QA y entrega; bloquea transiciones inseguras, repetidos y costos inválidos. Se completaron **60/60 casos sintéticos**. `repair_lab_runner.py` verificó que en el backend/DB examinados no hay router, modelo ni tablas de reparaciones: **cero reparaciones reales conectadas**. Reporte `REPAIRS_LAB.json`/MD. Falta desarrollar integración protegida con permisos, técnicos, trabajos, historial y UI. Nunca avisar a clientes sin integración y autorización.

### Publicidad
Conector de Metricool para marca SoftMobile accesible desde ChatGPT: el período 08 oct–07 nov reportó **31 filas diarias con métricas en cero y 0 filas de campañas**. Importación manual a `METRICOOL_SOURCE.json`, y revisión por `marketing_analytics.py` → `MARKETING_AUDIT.json`/MD. Esto **no demuestra** ausencia de campañas ni gasto. Moneda y conversiones reales no verificadas; sin refresco automático en el VPS. No atribuir ingresos o recomendar cambiar presupuestos.

### Código y calidad
`patch_source_compat.py` verifica la versión Ruby de piloto por SHA de fuente revisado: `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1`. Detecta la nueva ancla segura de contexto, **sin Groq, sin ejecutar parches, sin despliegues**; timer dos veces al día. Un generador antiguo todavía tiene `trusted_source_drift` y su timer de propuestas está apagado. Los 250 issues del laboratorio son ficticios, no defectos reales certificados. Faltan validación independiente y revisión de candidato para despliegues.

### Certificado y pruebas
La certificación ya tiene apartado **non_whatsapp_readiness: 5 de 10**, separado de las condiciones de salida comercial (todavía **5 de 15**). Los 5 pendientes no WhatsApp son: convergencia QA independiente, conciliación real de ingresos, reparaciones integradas, fuente de campañas fiable, pipeline autónomo de código completo. **180 pruebas unitarias del supervisor aprobadas**. No se hicieron envíos públicos, pagos, pedidos, campañas ni reinicios WhatsApp. Código respaldado en PR #156 en borrador.

**Para detener módulos**: `systemctl disable --now softmobile-patch-source-compat.timer`; para detener toda la cadena detener `softmobile-openclaw-supervisor.timer` y revisar cuidadosamente los overrides `OnSuccess` (no modificar el entorno público). Cada archivo de salida permanece restringido a `/opt/openclaw-lab/workspace/softmobile-supervisor`.


### API de reparaciones en rama de desarrollo (sin instalar)
- **GitHub PR #156, aún en borrador:** módulos `backend/app/models/repairs.py`, `schemas/repairs.py`, `services/repairs_policy.py`, `routers/repairs.py`; `backend/app/main.py` registra las rutas únicamente si `SOFTMOBILE_REPAIRS_ENABLED=true`. Al arrancar normalmente (bandera ausente o false) NO registra rutas de reparaciones ni importa el modelo, y el VPS productivo permanece sin cambios.
- Los endpoints de recepción, consulta, asignación a técnicos, eventos y transiciones requieren superadministrador. La asignación verifica rol Técnico activo. Los modelos prohíben PII/IMEI/cuentas y requieren una referencia opaca, presupuesto aprobado, repuestos y QA para entregar. Las referencias de aprobación todavía **no constituyen prueba independiente de consentimiento del cliente**.
- **16/16 pruebas HTTP con FastAPI y SQLite de memoria** usando la virtualenv existente del backend, sin importar app.main productivo ni tocar datos reales.
- Migración SQL para PostgreSQL **solo preparada** en `backend/migrations/repairs_schema_prelaunch.sql`. La ejecuté en PostgreSQL 16 *desechable y sin red*, creando las dos tablas y validando cuatro restricciones; el contenedor se elimina al salir. **Nunca se ejecutó sobre `inventory_db`**.
- Faltan revisión de la migración con DB real y backup, permisos por sucursal/empleado, consentimiento documental, UI del taller, integración a inventario/repuestos y pruebas E2E. No activar el flag sin todo ello.
- El análisis financiero diferencia 173 órdenes con total distinto del subtotal: **153 tarjeta/financiamiento potencialmente con ajustes o cargos**, 20 efectivo/transferencia que requieren cotejo. No son pérdidas reales verificadas. `FINANCE_AUDIT.json` mantiene solo dos alertas agregadas (20 y tres productos bajo costo).
- El número actual de regresiones del sistema supervisor es **180/180**, separado de las 16 de la API aislada. Meta Ads y WhatsApp siguen sin automatizaciones comerciales.

### Continuación 7 nov 2026 HN — interfaz y anti-duplicados, exclusivamente en PR
- La interfaz administrativa de reparaciones está en la rama PR #156: `src/components/RepairIntakeDialog.tsx`, `src/lib/repairs.ts`, métodos autenticados en `src/lib/apiClient.ts`, botón oculto en `src/App.tsx` salvo `VITE_SOFTMOBILE_REPAIRS_ENABLED=true` y usuario superadministrador.
- **TypeScript compila sin errores** y **Vite genera el paquete** en `/tmp/sm-repairs-frontend-check/dist`, fuera del árbol de producción. No se desplegó esa interfaz.
- `backend/app/services/repair_schema_guard.py` bloquea la importación de modelos y rutas si las tablas de reparaciones no están previamente instaladas. Evita que `init_db().create_all()` cree accidentalmente tablas nuevas al activar solo la bandera. A falta de esquema, todo el inventario sigue funcionando sin las rutas de reparaciones.
- `intake_key` único en modelo, SQL, API y UI: repetir una solicitud con misma clave/datos devuelve la misma orden; usar clave con datos diferentes devuelve 409. La UI conserva la clave durante reintentos fallidos y la reinicia si cambia el borrador del equipo.
- La asignación verifica rol Técnico activo **y acceso de edición a la misma sucursal**. Los cambios de estado siguen exigiendo supervisión y QA; los técnicos aún no tienen acceso propio a endpoints (piloto admin-only).
- **20/20 pruebas HTTP aisladas en SQLite de memoria**, incluyendo seguridad del esquema, alcance de técnico, idempotencia e historial.
- **Prueba de PostgreSQL 16 desechable sin red completada:** migración DDL revisada, caso ficticio, asignación autorizada, siete transiciones, ocho eventos, repetición idempotente y conflicto detectado. Cero casos reales, cero pagos y cero escrituras al PostgreSQL de inventario. Script: `backend/tests/postgres_repair_smoke.py`.
- **Pendiente antes de poner reparaciones en operación:** CI en rama completa, revisión de esquema y respaldo real, roles por técnico/sucursal, interfaz probada en navegador, evidencia real de autorización del cliente, repuestos/costos y aceptación del dueño. Mantener ambos flags apagados; WhatsApp al final.
