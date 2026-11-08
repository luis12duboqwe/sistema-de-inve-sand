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
