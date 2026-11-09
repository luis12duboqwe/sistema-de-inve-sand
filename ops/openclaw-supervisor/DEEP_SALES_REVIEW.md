# SoftMobile | Corrección de conversaciones largas en laboratorio

Fecha: 9 de noviembre de 2026. Alcance: ventas de celulares (no reparaciones ni WhatsApp).

## Resultados confirmados

El candidato original de Replica (SHA 367912aab2611f22392cb842c5c0076cc601c7e1c0320300b7f352b9625c5b4b) tenía **21/32** criterios en 10 conversaciones ficticias de 15 mensajes. Se detectaron 11 defectos: repetición de ciudad en pago contra entrega, omisión de cancelación antes del envío, falta de plazo Promerica, retorno a Pro Max no comprendido, siguientes pasos de compra, reserva para mañana, estado de envío de cotización, comprobación de pago recibido, petición de clave temporal, intento de compra que reinicia entrega, y reserva después de pedir cancelación.

Se creó una corrección acotada y comprobable en copia Ruby, sin alterar el código activo. Candidato actual SHA256: `a4ca83e5d83244eb8552c67ad55d291eb601440b9c94c4bd614cd7d28365c06d`.

| Evaluación independiente en laboratorio sin red | Resultado candidato |
|---|---|
| 10 conversaciones de 15 turnos, 32 criterios | 32/32 |
| 13 nuevos casos de reescritura/safety | 13/13 |
| 72 conversaciones comerciales | 72/72 |
| 18 reformulaciones originales | 18/18 |
| 6 retos diarios rotativos | 6/6 |
| 11 casos adversariales | 11/11 |
| 22 preguntas independientes adicionales | 22/22 |
| Checkout ficticio y pruebas unitarias | 72/72 y 68/68 |

No equivale a validación externa de clientes, verificación de pagos, orden real, aprobación de financiamiento, fuente de catálogo ni permiso de lanzamiento.

## Automatización

El servicio `softmobile-replica-cycle.service` ejecuta ahora tres etapas: `replica_cycle.py` verifica fuente/QA y reporte del autofix; `replica_improvement_cycle.py` aplica tres recetas acotadas en una copia; `replica_deep_cycle.py` comprueba que el SHA padre sigue siendo el esperado, construye una propuesta de mejora de conversaciones profundas y la rechaza si alguna de las suites falla. Tiene redes bloqueadas por systemd, solo escritura dentro del laboratorio y no llama a modelos externos. Corre mediante el temporizador existente cada seis horas.

La propuesta Ruby y el diff se guardan en `/opt/openclaw-lab/workspace/lab-runs/replica-skill/candidates/`. Resumen de la última pasada: `/opt/openclaw-lab/workspace/lab-runs/replica-skill/deep-lab-latest.json` y `deep-lab-latest.md`.

El generador solo conoce y permite el SHA de fuente activa `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1` y un candidato padre aprobado para revisión. Si cualquiera cambia, el proceso se bloquea. Los archivos se guardan mediante renombrado atómico para no seguir enlaces simbólicos preexistentes.

## Pendientes reales

El vendedor Ruby activo sigue siendo la versión anterior; sus 72 escenarios de calidad no equivalen a los 72 del candidato. La certificación general de prelanzamiento continúa bloqueada hasta integrar un candidato mediante revisión autorizada, verificar precios y existencias de los aliados, conciliar órdenes, validar fuentes de marketing, comprobar consentimiento de seguimiento y completar WhatsApp en la fase final.

El código de producción, Chatwoot, inventario, cobros y mensajes a clientes no fueron modificados por este trabajo.