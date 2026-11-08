# SoftMobile — Plan de autonomía OpenClaw (prelanzamiento)
Fecha de revisión: 2026-11-07. Entorno srv1656045. Cada fase requiere pruebas, lectura de resultados y rollback. Nunca habilitar público por el éxito aislado de un laboratorio.

## Fase 1. Encadenamiento por evento del VPS
- Al completarse satisfactoriamente el supervisor, activar el director; al terminar el director, iniciar el ejecutor; después materializar novedades.
- Mantener respaldos periódicos de los timers, sin duplicar clientes ni alterar servicios comerciales.
- Criterios: orden verificable en journald; fail-closed si un paso falla; 0 mensajes enviados; límites de RAM.

## Fase 2. Memoria operativa y tareas
- Registro SQLite local de cambios de tareas a partir de resultados saneados, con detección por ID/digest, historial y responsable sugerido; nunca texto de conversaciones ni datos de pago.
- No marcar tareas como resueltas por desaparecer del reporte; no reintentar envíos al público.
- Criterios: idempotencia; reconexión; repetición de eventos sin duplicaciones; recuentos correctos.

## Fase 3. Vendedor comercial en laboratorio
- Reutilizar agente actual, motor de cotizaciones, fotos, seguimiento, inventario y Chatwoot. Probar recorridos con escenarios ficticios y validadores externos.
- Verificar llegada real WhatsApp -> WAHA -> Chatwoot y salida al número de prueba *antes* de liberar cualquier comunicación pública. WAHA piloto hoy no está operativo y requiere confirmar sus credenciales y aislamiento.
- Criterios: no inventar precio, existencia, cuotas, cuentas, entrega ni aprobaciones; duplicados, mensajes simultáneos y opt-outs cubiertos.

## Fase 4. Automejora
- Triage de problemas y repetición offline. Preparar propuestas de parches en rama, revisión humana, pruebas de regresión y rollback.
- Bloqueo actual: trusted_source_drift del generador de cambios Ruby; el timer permanece deshabilitado.
- Criterios: fallo reproduce antes, pasa después, auditoría independiente, no cambios al activo ni PR merge no aprobado.

## Fase 5. Negocio y crecimiento
- Inventario: conciliación real, reportes sin unidades negativas, comparación de transferencias y compras propuestas; sin ejecutar compras.
- Finanzas: reconciliar pedidos pendientes vs completados, cierres diarios y márgenes con comprobantes reales; nunca inventar ganancias.
- Reparaciones: localizar modelo y órdenes existentes o diseñar integración; empleado/turno y tareas por permisos.
- Meta Ads: recuperar datos comerciales mediante fuente confiable y autorizada; no ajustar campañas automáticamente.
- Criterios: datos verificables y permisos mínimos; historial y límites de costo.

## Fase 6. Certificación y salida
- Validar conectividad, consentimiento, pruebas Chatwoot/WAHA, integridad de la base, cobertura QA independiente y autorización explícita.
- El supervisor tiene el bloqueo public_messaging_ready=false de manera incondicional. No modificar ni eludir sin la revisión y autorización de lanzamiento.

## Convención de estados
- HECHO: acción ejecutada y pruebas registradas.
- PARCIAL: componentes operativos, falta validación integral.
- BLOQUEADA: falta acceso, evidencia o autorización.
- La ejecución autónoma se limita a comprobaciones/reproducciones ficticias, tareas internas y preparación reversible, no mensajes o transacciones reales.

## Estado al iniciar la fase nueva
Supervisor, director y ejecutor activos; 14 tareas/8 áreas, 86 pruebas locales, 72/72 conversaciones ficticias, 250 replays ficticios, 0 mensajes públicos. 4 bloqueos de lanzamiento.

## Ejecución y evidencia de esta etapa (7 nov, 2026; horario del VPS UTC)
- **Fase 1 — HECHO para snapshots internos:** sistema `OnSuccess` encadena supervisor→director→ejecutor→router→certificado. Servicio systemd de cada etapa verificado con `Result=success` y misma marca temporal. Supervisor mantiene timer cada 30 minutos; director y ejecutor ya no tienen timer propio activo. NO es aún un webhook de mensajes reales.
- **Fase 2 — HECHO para tareas internas saneadas:** `event_router.py` genera `EVENTS.json`/`EVENTS.md`, guarda un historial SQLite local de eventos, detecta tareas nuevas, cambiadas y desaparecidas sin declararlas completadas. Router puede disparar un agente de ventas/operaciones/ingeniería verificado y restringido (`--tools read,write`, sin entrega externa); 3 revisiones reactivas diarias como máximo. Se probó en sistema aislado el encolado efectivo del agente de ventas.
- **Fase 3 — PARCIAL:** 72/72 conversaciones ficticias de seis familias, nueve cierres simulados, sin operaciones reales. WAHA piloto sigue detenido; falta canal verdadero de prueba y confirmar consentimiento de cada contacto.
- **Fase 4 — PARCIAL/BLOQUEADA:** 250 incidencias sintéticas reproducidas en aislamiento (202 señales persisten). Falta convergencia independiente. El generador inerte de cambios Ruby está bloqueado por `trusted_source_drift`; no habilitar su timer ni promover parches automáticamente.
- **Fase 5 — PARCIAL/BLOQUEADA:** inventario agrega stock y revisa órdenes por lectura; reparaciones no integradas; rentabilidad sin conciliación; publicidad sin fuente de datos utilizable; ningún pago ni campaña editada.
- **Fase 6 — AUDITORÍA AUTOMÁTICA HECHA, CERTIFICACIÓN NO APROBADA:** `release_gate.py` produce `CERTIFICATION.json`/`CERTIFICATION.md`: 5/15 controles aprobados, 6 bloqueos de lanzamiento comercial, 10 de autonomía completa. El informe NO puede habilitar envíos públicos.

### Controles de costos y seguridad
- 117 pruebas unitarias de la cadena. Datos de clientes no copiados a la memoria de eventos. Máximo tres despertares de especialista/día por alertas. Trabajos de laboratorio aislados, sin contacto externo.
- Módulos systemd bajo aislamiento del sistema de archivos, rutas de salida restringidas, límites RAM y bloqueo de red. No reiniciar WAHA, cambiar entorno público, aplicar parches ni tocar datos de clientes mientras los certificados sigan bloqueados.
- Código y unidades desplegadas están respaldados en el PR #156 **en borrador**: revisar antes de integrar a rama principal.

### Criterio de cierre restante
Una tarea bloqueada se considera completada solo con evidencia independiente de integración en el entorno autorizado. El usuario aún tiene que aprobar la puesta en producción después de comprobar transporte real, WhatsApp, QA y políticas comerciales; por tanto no podemos afirmar que todas las seis fases están terminadas.

### Auditoría adicional del vendedor (8 nov UTC)
- Pruebas unitarias de los módulos `sales_ai_agent`, `lead_handoff`, `sales_pipeline_conversion`, `chatwoot_ai_bridge` y `sales_ai_photo_adapter`: **60/60 aprobadas**, usando mocks y sin mensajes reales.
- `test_followup_policy_priority.py` añade una prueba que **no puede completarse**: el generador de una propuesta antigua rechaza el hash SHA del código Ruby actual, deliberadamente. La prueba agregada queda **60/61, con 1 error de source drift**. No cambiar a ciegas BASE_SHA ni deshabilitar este control.
- Las tres prioridades `security`, `complaint`, `cancel_interest` **sí coincidieron** con las intenciones esperadas al ejecutar el motor Ruby vigente en un contenedor desechable sin red, de forma separada al generador antiguo.
- Estos datos no acreditan éxito real de Chatwoot/WAHA ni invalidan el bloqueo de lanzamiento. Para la fase 4 es necesario revisar/rebasar la propuesta antigua y demostrar convergencia independiente.

### Corrección y regresión ampliada (8 nov UTC)
- El nuevo caso con acentos reales detectó un fallo del Ruby activo: «Mi pedido llegó roto» podía clasificarse como `tracking` en lugar de `complaint`. Las pruebas antiguas tenían caracteres sustituidos por `?` y no lo reproducían.
- Se preparó un candidato exacto de una sola regla para detectar daño físico en pedidos entregados antes de las consultas genéricas de rastreo. Se hicieron pruebas en contenedor desechable sin red: **72/72 ventas ficticias**, **117/117 Ruby**, 3/3 prioridades seguridad/reclamo/cancelación y **250 replays sin nuevas señales** comparados con el código anterior.
- El piloto recibió la corrección con SHA validado, backup y alcance restringido. Regresión posterior: **118/118 pruebas del supervisor**, **62 pruebas del agente sin fallos y 1 skip explícito de propuesta vieja**, **72/72 simulaciones del Ruby actualizado**. No se enviaron mensajes públicos ni se activaron pagos/ventas.
- `director.py` valida ahora que `scored_source_sha256` de los ensayos corresponda al archivo Ruby activo, evitando indicar un 72/72 antiguo tras una modificación.
- El parche antiguo en seguimiento aún necesita rebase validado: su test se **omite** ante SHA incorrecto, mientras que el comportamiento de seguridad del código activo se prueba siempre de forma independiente.
- La certificación sigue bloqueando el lanzamiento por la falta de transporte WhatsApp real probado, convergencia independiente, consentimiento verificable, autorización comercial y aprobación del propietario.


## Última actualización: prioridad NO WhatsApp (noviembre 7 HN)
**Foco:** WhatsApp se desplaza a fase final; no modificar WAHA, campañas, pagos ni contactos reales.

**Hecho y probado en el VPS:**
- Auditoría de inventario/finanzas `finance_audit.py` por SQL de solo lectura con discrepancias agregadas y clasificación por método de pago. Se incorpora a la cadena `OnSuccess` después del ejecutor.
- Motor de reparaciones `repair_workflow.py` con transiciones de estado auditables e idempotentes y presupuesto/QA con aprobación humana, 60/60 escenarios totalmente ficticios. `repair_lab_runner.py` detecta que las tablas y API reales aún faltan. Cero casos reales creados.
- Evidencia de Meta Ads vía Metricool, importada manualmente sin secretos y con advertencia de datos no suficientes para ROI; ninguna campaña editada.
- Control `patch_source_compat.py` revisa dos veces al día el SHA del Ruby piloto sin llamadas API ni despliegues.
- Agentes de OpenClaw reorientados para consultar reportes saneados de finanzas, reparaciones, publicidad y código, concentrándose en las áreas no WhatsApp.
- Estado de QA local después de estas mejoras: **180 pruebas unitarias aprobadas**; cero mensajes públicos. El certificado diferencia *non_whatsapp_readiness = 5/10* del lanzamiento comercial *5/15*.

**No terminado, requiere fuente y/o validación:**
- Conciliación bancaria/caja real: 458 órdenes pendientes y 0 cierres; 173 diferencias por pago (96 tarjeta, 57 financiamiento, 14 transferencia, 6 efectivo) son alertas de conciliación, no errores ni pérdidas confirmadas.
- Reparaciones reales: desarrollar módulos de backend, permisos por técnico y sucursal, orden y trazabilidad de piezas, interfaz y pruebas de aceptación; actualmente solo existe flujo aislado.
- Ads: comprobar datos reales y fuente de campañas con métricas de atribución; el conector no devolvió filas de campaña y no tiene sincronización automática al VPS.
- QA independiente: 250 replays hipotéticos no prueban convergencia; conservar el bloqueo.
- Programador autónomo: source guard de SHA listo, pero el generador antiguo de propuestas sigue sin ejecutarse debido al source drift; se necesita adaptación y pruebas independientes antes de activarlo.
- WhatsApp, consentimiento y salida pública: **al final**, únicamente tras completar áreas anteriores y solicitar autorización explícita.

La autorización pública es independiente de cualquier resultado de laboratorio; nunca se concederá automáticamente.


### Subfase de reparaciones — API funcional en borrador, integración real pendiente
- En PR #156 se añadieron modelo, esquemas, motor de transiciones, API administrativa, bandera `SOFTMOBILE_REPAIRS_ENABLED` desactivada por defecto y **16/16 tests HTTP** con SQLite de memoria. No se modificó el FastAPI activo ni sus tablas.
- Migración `backend/migrations/repairs_schema_prelaunch.sql` sometida a prueba de DDL en Postgres 16 efímero sin red (tablas, índices, restricciones, una orden y un evento de prueba). **No se aplicó en el servidor de inventario**.
- Pendientes de cierre: permisos de técnico por sucursal y supervisión de acceso, integración real de repuestos y costes, UI operativa, validación documental de aprobación del cliente, migración y respaldo, pruebas E2E con Postgres en entorno aislado, decisión de habilitación.
- Cierre de los trabajos internos actuales: 180 pruebas de OpenClaw aprobadas + 16 tests HTTP del borrador. Auditoría financiera distingue 20 discrepancias no tarjeta/financiamiento a revisar y 153 que podrían deberse a cargos/financiamiento; confirmar origen contable antes de cambios.

### Reparaciones: UI + API + DDL endurecidos en PR #156 (7 nov HN)
- La pantalla de taller está preparada tras bandera UI independiente `VITE_SOFTMOBILE_REPAIRS_ENABLED=true` y acceso superadministrador. Compilación TypeScript y paquete Vite terminados en copia aislada; ningún archivo frontend servido en producción ha cambiado.
- El backend preparado está detrás de `SOFTMOBILE_REPAIRS_ENABLED=true` y además verifica la existencia previa de tablas y columnas antes de cargar modelos; no ejecuta DDL automáticamente por el flag.
- El registro de orden requiere `intake_key` único para impedir duplicados por reintentos. La asignación exige técnico activo autorizado para la sucursal del caso.
- **20 tests HTTP aprobados** sobre SQLite de memoria; **PostgreSQL 16 aislado sin red** con migración y ciclo HTTP end-to-end (8 eventos) también aprobado.
- **Solo código en PR, no en producción.** El indicador de 5/10 no WhatsApp **no cambia**, porque faltan integración de taller real, finanzas conciliadas, datos de ads verificados y QA convergente.
- Siguientes pasos: revisión de permisos/perfil por empleado, consentimiento verificable, repuestos/consumos y costos, diseño del módulo para operación de taller, auditoría del PR y aprobación explícita para migración en ambiente aislado/producción.
