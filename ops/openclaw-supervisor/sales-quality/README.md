# QA comercial del vendedor IA — laboratorio aislado

**Objetivo:** evaluar si el vendedor SoftMobile mantiene una conversación útil de venta, sin confundir una operación ficticia del simulador con una venta o un cierre comercial real.

## Hallazgo reproducible
El laboratorio existente `conversion_training_lab.py` aprobaba **72/72** escenarios: exactitud de modelo/capacidad/color, una operación de apartado/checkout en inventario completamente ficticio y ausencia de promesas comerciales detectadas.

La nueva herramienta independiente `sales_conversation_quality.py` inspecciona **las respuestas textuales del motor Ruby real** (no los comprobantes ficticios), sin red ni acceso a clientes. Misma selección fija de 72 conversaciones: **36/72** pasan, **36/72** no cumplen los nuevos criterios de continuidad.

| Familia | Ruby actual | Candidato |
|---|---:|---:|
| Compra y retiro | 12/12 | 12/12 |
| Financiamiento | 12/12 | 12/12 |
| Negociación | 0/12 | 12/12 |
| Reserva | 0/12 | 12/12 |
| Envíos | 0/12 | 12/12 |
| Accesorios/garantía | 12/12 | 12/12 |
| **Total** | **36/72** | **72/72** |

Fallos concretos:
- Se repetía la pregunta de la ciudad cuando el cliente ya había dicho Choloma.
- Ante «si es posible sigo con la compra», el sistema regresaba al saludo/ubicación.
- Ante «reservarlo para mañana», el sistema ignoraba la fecha solicitada.

## Cambio propuesto, sin desplegar
`build_sales_followup_candidate.py` exige que la fuente Ruby original tenga SHA-256 exacto `1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1` y una única ancla revisada. Genera un candidato y el parche `sales-bot-v2-reply-candidate.patch` sin escribir el archivo Ruby público. La nueva lógica mejora respuestas de negociación condicionada, apartados sin aprobación, costos y plazos de envío; nunca ofrece cuota, descuento, precio, reserva, pago, fecha o existencias como hechos sin fuente autorizada.

Se reejecutaron las 72 pruebas originales del candidato: **72/72**, cero promesas no verificadas detectadas, nueve checkouts *ficticios*, cero mensajes/cobros/inventario reales. La batería de pruebas adicionales `test_sales_conversation_quality.py` junto con el test comercial anterior pasó **21/21**. La nueva evaluación del candidato también marcó **72/72**.

**Límite fundamental:** la rúbrica es determinista y cubre solo los casos creados, no comprueba de manera independiente que el vendedor funcione con todos los clientes; tampoco demuestra resultados con IA externa o transporte WhatsApp. El candidato requiere nuevas pruebas independientes y revisión de código antes de integrarse al bot.

## Control en el VPS
Unidad `softmobile-seller-conversation-quality.service` cada cuatro horas por su timer, solo lectura del Ruby original y resultados agregados en `quality/seller-conversation-baseline.json`. Informa SHA y recuentos. No consume tokens de API. OpenClaw consume esos recuentos en `DIRECTOR.json.seller_reply_quality` y crea `ventas_calidad_conversacional` como tarea prioritaria en `awaiting_qa`, sin cortar la cadena por una falla de la rúbrica.

La certificación comercial declara `ruby_sales_conversation_quality_passed=false` y presenta **4/9 condiciones satisfechas**. Toda salida pública sigue prohibida.

**Pendiente:** revisión de variantes adversariales y de la seguridad contra promesas, continuidad de cambios de modelo, aprobación de la candidata y pruebas en aislamiento con el agente IA. WhatsApp, desplegar el bot, clientes y pagos permanecen fuera del alcance.
