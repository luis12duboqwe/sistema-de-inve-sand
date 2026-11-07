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
- Su timer `softmobile-openclaw-director.timer` se ejecuta a :10 y :40 de cada hora; no envía mensajes ni hace modificaciones externas.
- OpenClaw genera informes especializados: ventas a las 09:30 diario, operaciones a las 09:50 diario, calidad y código martes/jueves/sábado a las 10:15. Todos en `America/Tegucigalpa`, con `--tools read,write`, `--no-deliver`, sesiones aisladas y límite de ejecución.
- Archivos: `SALES_REVIEW.md`, `OPERATIONS_REVIEW.md`, `ENGINEERING_REVIEW.md` en la misma carpeta de reportes.
- Para pruebas: `python3 -m unittest discover -q -p 'test_*.py'`; para ejecución: `systemctl start softmobile-openclaw-director.service`.
- El director integra solo los **agregados anonimizados** de la revisión sintética cuando existe `issue-triage-report.json` y un `offline-issue-replay-report.json` reciente, con 0 llamadas API, 0 mensajes públicos y 0 promociones. Los 250 casos son conversaciones ficticias y las señales no prueban errores comerciales reales.
- Se reactivó `softmobile-issue-triage.timer` (cada 30 minutos) y `softmobile-offline-issue-replay.timer` (cada hora, override `90-softmobile-hourly-safety.conf`): replay en Ruby desechable sin red, 200 MB por contenedor, sin despliegues.
- La conectividad de Meta Ads desde el VPS sigue sin fuente utilizable. La cuenta externa de analytics puede aparecer autenticada pero los conectores requieren suscripción/plan para retornar datos; no declarar campañas optimizadas ni gastos verificados.
- Para detener al director: `systemctl disable --now softmobile-openclaw-director.timer`. Para detener el QA adicional: `systemctl disable --now softmobile-issue-triage.timer softmobile-offline-issue-replay.timer`. Para detener las revisiones de IA, deshabilitar sus trabajos individualmente con OpenClaw cron; no afectan el supervisor.

## Ejecutor interno y embudo comercial ficticio (tercera etapa, PRELANZAMIENTO)
- La cadena está ordenada en UTC: supervisor `:08/:38`, director `:10/:40`, ejecutor `:12/:42`. El override `90-softmobile-schedule-chain.conf` del supervisor garantiza orden predecible. Si las fuentes cambian entre lecturas, el ejecutor se detiene (fail-closed).
- `pilot_executor.py` procesa solo los IDs de tarea autorizados, coteja datos y evidencia sin PII, mantiene `operator.sqlite3` con historial deduplicado e informa en `OPERATOR.json` y `OPERATOR.md`. Acciones reales permitidas: SQL `BEGIN TRANSACTION READ ONLY`, comprobaciones de fotos en SQLite lectura, contenedores mediante Docker inspect y pruebas unitarias acotadas.
- `softmobile-pilot-executor.timer` ejecuta cada 30 minutos; `softmobile-pilot-executor.service` usa `ProtectSystem=strict`, `ReadWritePaths` limitado, `IPAddressDeny=any`, `RestrictAddressFamilies=AF_UNIX`, memoria 192 MB. Por compatibilidad con `runuser -u postgres` y autenticación local peer, el ejecutor usa `NoNewPrivileges=false`; **conserva bloqueo de red, sistema de archivos de solo lectura, allowlist fija y no tiene ninguna acción de escritura comercial**. No instalar extensiones de sistema en este proceso.
- Las 14 tareas del director se transforman en verificaciones internas, alertas de revisión humana y pendientes de QA; las bloqueadas siguen bloqueadas. Ninguna acción produce mensajes, cobros, movimientos de stock ni despliegues.
- `softmobile-sales-conversion.service` comprobó 72 escenarios ficticios (compra, financiamiento, negociación, reserva, envío y accesorios), 72 aprobados y 9 checkouts **simulados**. 0 ventas, 0 pedidos y 0 mensajes reales. El director incluye este resultado en `synthetic_sales`; el ejecutor lo revisa y escala regresiones.
- `softmobile-sales-conversion.timer` se activó con override `zz-softmobile-prelaunch-safe-cadence.conf` (cada 4 horas a `:26` UTC, en lugar del antiguo acelerado cada 30 min). Usa contenedores desechables sin red.
- Pruebas: `python3 -m unittest discover -q -p 'test_*.py'`; ejecución real de cadena: `systemctl start softmobile-openclaw-supervisor.service; systemctl start softmobile-openclaw-director.service; systemctl start softmobile-pilot-executor.service`.
- Desactivar al ejecutor: `systemctl disable --now softmobile-pilot-executor.timer`; desactivar simulación: `systemctl disable --now softmobile-sales-conversion.timer`.

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
